import asyncio
import json
import logging
import re
import warnings
from collections import defaultdict
from functools import wraps, partialmethod as pm
from itertools import chain
from typing import (Union, AnyStr, Mapping, Iterable,
                    Optional, Callable, AsyncGenerator)
from urllib.parse import urlencode

import aiohttp

from . import pd, no_pandas_warning
from .iterutils import InfluxDBResult, InfluxDBChunkedResult
from .serialization import parse_data, make_df

PointType = Union[AnyStr, Mapping] if pd is None else Union[AnyStr, Mapping, pd.DataFrame]
ResultType = Union[AsyncGenerator, dict, InfluxDBResult, InfluxDBChunkedResult]

# Aioinflux uses logging mainly for debugging purposes.
# Please attach your own handlers if you need logging.
logger = logging.getLogger('aioinflux')


def runner(coro):
    """Function execution decorator."""

    @wraps(coro)
    def inner(self, *args, **kwargs):
        if self.mode == 'async':
            return coro(self, *args, **kwargs)
        return self._loop.run_until_complete(coro(self, *args, **kwargs))

    return inner


class InfluxDBError(Exception):
    pass


class InfluxDBClient:
    def __init__(self,
                 host: str = 'localhost',
                 port: int = 8086,
                 mode: str = 'async',
                 output: str = 'raw',
                 db: str = 'testdb',
                 *,
                 ssl: bool = False,
                 unix_socket: Optional[str] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 database: Optional[str] = None,
                 loop: Optional[asyncio.BaseEventLoop] = None,
                 ):
        """
        The InfluxDBClient object holds information necessary to interact with InfluxDB.
        It is async by default, but can also be used as a sync/blocking client.
        When querying, responses are returned as raw JSON by default, but can also be wrapped in easily iterable
        wrapper object or be parsed to Pandas DataFrames.
        The three main public methods are the three endpoints of the InfluxDB API, namely:
        1) InfluxDBClient.ping
        2) InfluxDBClient.write
        3) InfluxDBClient.query
        See each of the above methods documentation for further usage details.
        See also: https://docs.influxdata.com/influxdb/latest/tools/api/

        :param host: Hostname to connect to InfluxDB.
        :param port: Port to connect to InfluxDB.
        :param mode: Mode in which client should run.
            Available options are: 'async', 'blocking' and 'dataframe'.
            - 'async': Default mode. Each query/request to the backend will
            - 'blocking': Behaves in sync/blocking fashion, similar to the official InfluxDB-Python client.
        :param output: Output format of the response received from InfluxDB.
            - 'raw': Default format. Returns JSON as received from InfluxDB.
            - 'iterable': Wraps the raw response in a `InfluxDBResult` or `InfluxDBChunkedResult`,
                          which can be used for easier iteration over retrieved data points.
            - 'dataframe': Parses results into Pandas DataFrames. Not compatible with chunked responses.
        :param db: Default database to be used by the client.
        :param ssl: If https should be used.
        :param unix_socket: Path to the InfluxDB Unix domain socket.
        :param username: Username to use to connect to InfluxDB.
        :param password: User password.
        :param database: Default database to be used by the client.
            This field is for argument consistency with the official InfluxDB Python client.
        :param loop: Asyncio event loop.
        """
        self._loop = asyncio.get_event_loop() if loop is None else loop
        self._connector = aiohttp.UnixConnector(path=unix_socket, loop=self._loop) if unix_socket else None
        self._auth = aiohttp.BasicAuth(username, password) if username and password else None
        self._session = aiohttp.ClientSession(loop=self._loop, auth=self._auth, connector=self._connector)
        self._url = f'{"https" if ssl else "http"}://{host}:{port}/{{endpoint}}'
        self.host = host
        self.port = port
        self._mode = None
        self._output = None
        self._db = None
        self.tag_cache = defaultdict(lambda: defaultdict(dict))
        self.mode = mode
        self.output = output
        self.db = database or db

    @property
    def mode(self):
        return self._mode

    @property
    def output(self):
        return self._output

    @property
    def db(self):
        return self._db

    @mode.setter
    def mode(self, mode):
        if mode not in ('async', 'blocking'):
            raise ValueError('Invalid running mode')
        self._mode = mode

    @output.setter
    def output(self, output):
        if pd is None and output == 'dataframe':
            raise ValueError(no_pandas_warning)
        if output not in ('raw', 'iterable', 'dataframe'):
            raise ValueError('Invalid output format')
        self._output = output

    @db.setter
    def db(self, db):
        self._db = db
        if db is None:
            return
        elif self.output == 'dataframe' and db not in self.tag_cache:
            if self.mode == 'async':
                asyncio.ensure_future(self.get_tag_info(), loop=self._loop)
            else:
                self.get_tag_info()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __del__(self):
        if not self._loop.is_closed() and self._session:
            asyncio.ensure_future(self._session.close(), loop=self._loop)

    def __repr__(self):
        items = [f'{k}={v}' for k, v in vars(self).items() if not k.startswith('_')
                 and k != 'tag_cache']
        items.append(f'mode={self.mode}')
        return f'{type(self).__name__}({", ".join(items)})'

    @runner
    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    @runner
    async def ping(self) -> dict:
        """Pings InfluxDB.
         Returns a dictionary containing the headers of the response from `influxd`.
         """
        async with self._session.get(self._url.format(endpoint='ping')) as resp:
            logger.debug(f'{resp.status}: {resp.reason}')
            return dict(resp.headers.items())

    @runner
    async def write(self, data: Union[PointType, Iterable[PointType]],
                    measurement: Optional[str] = None,
                    tag_columns: Optional[Iterable] = None, **extra_tags) -> bool:
        """Writes data to InfluxDB.
        Input can be:
        1) a string properly formatted in InfluxDB's line protocol
        2) a dictionary-like object containing four keys: 'measurement', 'time', 'tags', 'fields'
        3) a Pandas DataFrame with a DatetimeIndex
        4) an iterable of one of above
        Input data in formats 2-4 are parsed to the line protocol before being written to InfluxDB.
        See also: https://docs.influxdata.com/influxdb/latest/write_protocols/line_protocol_reference/

        :param data: Input data (see description above).
        :param tag_columns: Columns that should be treated as tags (used when writing DataFrames only)
        :param measurement: Measurement name. Mandatory when when writing DataFrames only.
            When writing dictionary-like data, this field is treated as the default value
            for points that do not contain a `measurement` field.
        :param extra_tags: Additional tags to be added to all points passed.
        :return: Returns `True` if insert is successful. Raises `ValueError` exception otherwise.
        """
        data = parse_data(data, measurement, tag_columns, **extra_tags)
        logger.debug(data)
        url = self._url.format(endpoint='write') + '?' + urlencode(dict(db=self.db))
        async with self._session.post(url, data=data) as resp:
            if resp.status == 204:
                return True
            else:
                msg = (f'Error writing data ({resp.status}): '
                       f'{resp.headers.get("X-Influxdb-Error", resp.reason)}')
                raise InfluxDBError(msg)

    @runner
    async def query(self, q: AnyStr,
                    *args,
                    epoch: str = 'ns',
                    chunked: bool = False,
                    chunk_size: Optional[int] = None,
                    db: Optional[str] = None,
                    parser: Optional[Callable] = None,
                    **kwargs) -> ResultType:
        """Sends a query to InfluxDB.
        Please refer to the InfluxDB documentation for all the possible queries:
        https://docs.influxdata.com/influxdb/latest/query_language/

        :param q: Raw query string
        :param args: Positional arguments for query patterns
        :param db: Database parameter. Defaults to `self.db`
        :param epoch: Precision level of response timestamps.
            Valid values: ``{'ns', 'u', 'µ', 'ms', 's', 'm', 'h'}``.
        :param chunked: If ``True``, makes InfluxDB return results in streamed batches
            rather than as a single response. Returns an AsyncGenerator which yields responses
            in the same format as non-chunked queries.
        :param chunk_size: Max number of points for each chunk. By default, InfluxDB chunks
            responses by series or by every 10,000 points, whichever occurs first.
        :param kwargs: Keyword arguments for query patterns
        :param parser: Optional parser function for 'iterable' mode
        :return: Returns an async generator if chunked is ``True``, otherwise returns
            a dictionary containing the parsed JSON response.
        """

        async def _chunked_generator(url, data):
            async with self._session.post(url, data=data) as resp:
                # Hack to avoid aiohttp raising ValueError('Line is too long')
                # The number 16 is arbitrary (may be too large/small).
                resp.content._high_water *= 16
                async for chunk in resp.content:
                    chunk = json.loads(chunk)
                    self._check_error(chunk)
                    yield chunk

        try:
            if args:
                fields = [i for i in re.findall('{(\w+)}', q) if i not in kwargs]
                kwargs.update(dict(zip(fields, args)))
            db = self.db if db is None else db
            query = q.format(db=db, **kwargs)
        except KeyError as e:
            raise ValueError(f'Missing argument "{e.args[0]}" in {repr(q)}')

        data = dict(q=query, db=db, chunked=str(chunked).lower(), epoch=epoch)
        if chunked and chunk_size:
            data['chunk_size'] = chunk_size

        url = self._url.format(endpoint='query')
        if chunked:
            if self.mode != 'async':
                raise ValueError("Can't use 'chunked' with non-async mode")
            g = _chunked_generator(url, data)
            if self.output == 'raw':
                return g
            elif self.output == 'iterable':
                return InfluxDBChunkedResult(g, parser=parser, query=query)
            elif self.output == 'dataframe':
                raise ValueError("Chunked queries are not support with 'dataframe' output")

        async with self._session.post(url, data=data) as resp:
            logger.debug(resp)
            output = await resp.json()
            logger.debug(output)
            self._check_error(output)
            if self.output == 'raw':
                return output
            elif self.output == 'iterable':
                return InfluxDBResult(output, parser=parser, query=query)
            elif self.output == 'dataframe':
                return make_df(output, self.tag_cache[self.db])

    @staticmethod
    def _check_error(response):
        """Checks for JSON error messages and raises Python exception"""
        if 'error' in response:
            raise InfluxDBError(response['error'])
        elif 'results' in response:
            for statement in response['results']:
                if 'error' in statement:
                    msg = '{d[error]} (statement {d[statement_id]})'
                    raise InfluxDBError(msg.format(d=statement))

    # noinspection PyCallingNonCallable
    @runner
    async def get_tag_info(self) -> Optional[dict]:
        """Gathers tag key/value information for measurements in current database

        This method sends a series of ``SHOW TAG KEYS`` and ``SHOW TAG VALUES`` queries
        to InfluxDB and gathers key/value information for all measurements of the active
        database in a dictionary.
        This is used internally automatically when using ``dataframe`` mode in order to
        correctly parse dataframes.
        """

        # noinspection PyCallingNonCallable
        async def get_measurement_tags(m, cache):
            keys = (await self.show_tag_keys_from(m))['results'][0]
            if 'series' not in keys:
                return
            for series in keys['series']:
                cache[series['name']] = defaultdict(list)
                for tag in chain(*series['values']):
                    tag_values = await self.show_tag_values_from(series['name'], tag)
                    for _, v in tag_values['results'][0]['series'][0]['values']:
                        cache[series['name']][tag].append(v)

        logger.info(f"Caching tags from all measurements from '{self.db}'")
        cache = {}
        state = self.mode, self.output
        self.mode = 'async'
        self.output = 'raw'
        ms = (await self.show_measurements())['results'][0]
        if 'series' not in ms:
            self.mode, self.output = state
            return
        await asyncio.gather(*[get_measurement_tags(m[0], cache) for m in ms['series'][0]['values']])
        for m in cache:
            cache[m] = {k: v for k, v in cache[m].items()}
        if cache:
            self.tag_cache[self._db] = cache
        self.mode, self.output = state
        return cache

    # Built-in query patterns
    _user_query_patterns = set()
    create_database = pm(query, "CREATE DATABASE {db}")
    drop_database = pm(query, "DROP DATABASE {db}")
    drop_measurement = pm(query, "DROP MEASUREMENT {measurement}")
    show_databases = pm(query, "SHOW DATABASES")
    show_measurements = pm(query, "SHOW MEASUREMENTS")
    show_retention_policies = pm(query, "SHOW RETENTION POLICIES")
    show_users = pm(query, "SHOW USERS")
    select_all = pm(query, "SELECT * FROM {measurement}")
    show_tag_keys = pm(query, "SHOW TAG KEYS")
    show_tag_values = pm(query, 'SHOW TAG VALUES WITH key = "{key}"')
    show_tag_keys_from = pm(query, "SHOW TAG KEYS FROM {measurement}")
    show_tag_values_from = pm(query, 'SHOW TAG VALUES FROM {measurement} WITH key = "{key}"')

    @classmethod
    def set_query_pattern(cls, queries: Optional[Mapping] = None, **kwargs) -> None:
        """Defines custom methods to provide quick access to commonly used query patterns.

        Query patterns are passed as mappings, where the key is name name of
        the desired new method representing the query pattern and the value is the actual query pattern.
        Query patterns are plain strings, with optional the named placed holders. Named placed holders
        are processed as keyword arguments in ``str.format``. Positional arguments are also supported.

        Sample query pattern dictionary:
        {"host_load": "SELECT mean(load) FROM cpu_stats WHERE host = '{host}' AND time > now() - {days}d",
         "peak_load": "SELECT max(load) FROM cpu_stats WHERE host = '{host}' GROUP BY time(1d),host"}

        :param queries: Mapping (e.g. dictionary) containing query patterns.
            Can be used in conjunction with kwargs.
        :param kwargs: Alternative way to pass query patterns.
        """
        if queries is None:
            queries = {}
        if not isinstance(queries, Mapping):
            raise ValueError('Query patterns must be passed in a dictionary '
                             'or by using keyword arguments')
        restricted_kwargs = ('q', 'epoch', 'chunked' 'chunk_size', 'parser')
        for name, query in {**queries, **kwargs}.items():
            if any(kw in restricted_kwargs for kw in re.findall('{(\w+)}', query)):
                warnings.warn(f'Ignoring invalid query pattern: {query}')
                continue
            if name in dir(cls) and name not in cls._user_query_patterns:
                warnings.warn(f'Ignoring invalid query pattern name: {name}')
                continue
            cls._user_query_patterns.add(name)
            setattr(cls, name, pm(cls.query, query))
