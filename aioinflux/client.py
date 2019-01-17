import asyncio
import json
import logging
import re
import warnings
from functools import wraps, partialmethod as pm
from typing import (Union, AnyStr, Mapping, Iterable,
                    Optional, Callable, AsyncGenerator)

import aiohttp

from . import serialization
from .compat import pd, no_pandas_warning
from .iterutils import InfluxDBResult, InfluxDBChunkedResult

PointType = Union[AnyStr, Mapping] if pd is None else Union[AnyStr, Mapping, pd.DataFrame]
ResultType = Union[AsyncGenerator, dict, bytes, InfluxDBResult, InfluxDBChunkedResult]

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


class InfluxDBWriteError(InfluxDBError):
    def __init__(self, resp):
        self.status = resp.status
        self.headers = resp.headers
        self.reason = resp.reason
        super().__init__(f'Error writing data ({self.status} - {self.reason}): '
                         f'{self.headers.get("X-Influxdb-Error", "")}')


# noinspection PyAttributeOutsideInit
class InfluxDBClient:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 8086,
        mode: str = 'async',
        output: str = 'json',
        db: Optional[str] = None,
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
        When querying, responses are returned as parsed JSON by default,
        but can also be wrapped in easily iterable
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
            Available options are: 'async' and 'blocking'.
            - 'async': Default mode. Each query/request to the backend will
            - 'blocking': Behaves in sync/blocking fashion,
                          similar to the official InfluxDB-Python client.
        :param output: Output format of the response received from InfluxDB.
            - 'json': Default format. Returns parsed JSON as received from InfluxDB.
            - 'bytes': Returns raw, non-parsed JSON binary blob as received from InfluxDB.
                       No error checking is performed. Useful for response caching.
            - 'iterable': Wraps the JSON response in a `InfluxDBResult` or `InfluxDBChunkedResult`,
                          which can be used for easier iteration over retrieved data points.
            - 'dataframe': Parses results into Pandas DataFrames.
                           Not compatible with chunked responses.
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
        self._session = aiohttp.ClientSession(
            loop=self._loop,
            auth=aiohttp.BasicAuth(username, password) if username and password else None,
            connector=aiohttp.UnixConnector(path=unix_socket,
                                            loop=self._loop) if unix_socket else None,
        )
        self._url = f'{"https" if ssl else "http"}://{host}:{port}/{{endpoint}}'
        self.host = host
        self.port = port
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
        if output not in ('json', 'bytes', 'iterable', 'dataframe'):
            raise ValueError('Invalid output format')
        self._output = output

    @db.setter
    def db(self, db):
        self._db = db
        if not db:
            warnings.warn(f'No default databases is set. '
                          f'Database must be specified when querying/writing.')

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
        items = [f'{k}={v}' for k, v in vars(self).items() if not k.startswith('_')]
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
    async def write(
        self,
        data: Union[PointType, Iterable[PointType]],
        measurement: Optional[str] = None,
        db: Optional[str] = None,
        precision: Optional[str] = None,
        rp: Optional[str] = None,
        tag_columns: Optional[Iterable] = None,
        **extra_tags,
    ) -> bool:
        """Writes data to InfluxDB.
        Input can be:

        1. A mapping (e.g. ``dict``) containing the keys:
            ``measurement``, ``time``, ``tags``, ``fields``
        2. A Pandas :class:`~pandas.DataFrame` with a :class:`~pandas.DatetimeIndex`
        3. A user defined class decorated w/ :func:`~aioinflux.serialization.usertype.lineprotocol`
        4. A string (``str`` or ``bytes``) properly formatted in InfluxDB's line protocol
        5. An iterable of one of the above

        Input data in formats 1-3 are parsed to the line protocol before being written to InfluxDB.
        See the `InfluxDB docs <https://docs.influxdata.com/influxdb/latest/
        write_protocols/line_protocol_reference/>`_ for more details.

        :param data: Input data (see description above).
        :param measurement: Measurement name. Mandatory when when writing DataFrames only.
            When writing dictionary-like data, this field is treated as the default value
            for points that do not contain a `measurement` field.
        :param db: Database to be written to. Defaults to `self.db`.
        :param precision: Sets the precision for the supplied Unix time values.
            Ignored if input timestamp data is of non-integer type.
            Valid values: ``{'ns', 'u', 'µ', 'ms', 's', 'm', 'h'}``
        :param rp: Sets the target retention policy for the write. If unspecified,
            data is written to the default retention policy.
        :param tag_columns: Columns to be treated as tags (used when writing DataFrames only)
        :param extra_tags: Additional tags to be added to all points passed.
        :return: Returns `True` if insert is successful. Raises `ValueError` exception otherwise.
        """
        if precision is not None:
            # FIXME: Implement. Related issue: aioinflux/pull/13
            raise NotImplementedError("'precision' parameter is not supported yet")
        data = serialization.serialize(data, measurement, tag_columns, **extra_tags)
        logger.debug(data)
        params = {'db': db or self.db}
        if rp:
            params['rp'] = rp
        url = self._url.format(endpoint='write')
        async with self._session.post(url, params=params, data=data) as resp:
            if resp.status == 204:
                return True
            raise InfluxDBWriteError(resp)

    @runner
    async def query(
        self,
        q: AnyStr,
        *args,
        epoch: str = 'ns',
        chunked: bool = False,
        chunk_size: Optional[int] = None,
        db: Optional[str] = None,
        parser: Optional[Callable] = None,
        **kwargs,
    ) -> ResultType:
        """Sends a query to InfluxDB.
        Please refer to the InfluxDB documentation for all the possible queries:
        https://docs.influxdata.com/influxdb/latest/query_language/

        :param q: Raw query string
        :param args: Positional arguments for query patterns
        :param db: Database to be queried. Defaults to `self.db`.
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

        # noinspection PyShadowingNames
        async def _chunked_generator(url, data):
            async with self._session.post(url, data=data) as resp:
                # Hack to avoid aiohttp raising ValueError('Line is too long')
                # The number 16 is arbitrary (may be too large/small).
                resp.content._high_water *= 16
                async for chunk in resp.content:
                    if self.output == 'bytes':
                        yield chunk
                        continue
                    chunk = json.loads(chunk)
                    self._check_error(chunk)
                    yield chunk

        try:
            if args:
                fields = [i for i in re.findall(r'{(\w+)}', q) if i not in kwargs]
                kwargs.update(dict(zip(fields, args)))
            db = self.db if db is None else db
            query = q.format(db=db, **kwargs)
        except KeyError as e:
            raise ValueError(f'Missing argument "{e.args[0]}" in {repr(q)}')

        # InfluxDB documentation is wrong regarding `/query` parameters
        # See https://github.com/influxdata/docs.influxdata.com/issues/1807
        if not isinstance(chunked, bool):
            raise ValueError("'chunked' must be a boolean")
        data = dict(q=query, db=db, chunked=str(chunked).lower(), epoch=epoch)
        if chunked and chunk_size:
            data['chunk_size'] = chunk_size

        url = self._url.format(endpoint='query')
        if chunked:
            if self.mode != 'async':
                raise ValueError("Can't use 'chunked' with non-async mode")
            g = _chunked_generator(url, data)
            if self.output in ('bytes', 'json'):
                return g
            elif self.output == 'iterable':
                return InfluxDBChunkedResult(g, parser=parser, query=query)
            elif self.output == 'dataframe':
                raise ValueError("Chunked queries are not support with 'dataframe' output")

        async with self._session.post(url, data=data) as resp:
            logger.debug(resp)
            output = await resp.read()
            logger.debug(output)

            if self.output == 'bytes':
                return output

            output = json.loads(output.decode())
            self._check_error(output)
            if self.output == 'json':
                return output
            elif self.output == 'iterable':
                return InfluxDBResult(output, parser=parser, query=query)
            elif self.output == 'dataframe':
                return serialization.dataframe.serialize(output)

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

    # Built-in query patterns
    _user_qp = set()
    create_database = pm(query, 'CREATE DATABASE "{db}"')
    drop_database = pm(query, 'DROP DATABASE "{db}"')
    drop_measurement = pm(query, 'DROP MEASUREMENT "{measurement}"')
    select_all = pm(query, 'SELECT * FROM "{measurement}"')
    show_databases = pm(query, "SHOW DATABASES")
    show_continuous_queries = pm(query, "SHOW CONTINUOUS QUERIES")
    show_measurements = pm(query, "SHOW MEASUREMENTS")
    show_retention_policies = pm(query, "SHOW RETENTION POLICIES")
    show_users = pm(query, "SHOW USERS")
    show_series = pm(query, 'SHOW SERIES')
    show_series_from = pm(query, 'SHOW SERIES FROM "{measurement}"')
    show_tag_keys = pm(query, "SHOW TAG KEYS")
    show_tag_values = pm(query, 'SHOW TAG VALUES WITH key = "{key}"')
    show_tag_keys_from = pm(query, 'SHOW TAG KEYS FROM "{measurement}"')
    show_tag_values_from = pm(query, 'SHOW TAG VALUES FROM "{measurement}" WITH key = "{key}"')

    @classmethod
    def set_query_pattern(cls, name: str, qp: str) -> None:
        """Defines custom methods to provide quick access to commonly used query patterns.
        Query patterns are plain strings, with optional the named placed holders.
        Named placed holders are processed as keyword arguments in ``str.format``.
        Positional arguments are also supported.

        Sample query pattern:
        ``"SELECT mean(load) FROM cpu_stats WHERE host = '{host}' AND time > now() - {days}d"``

        :param name: Name of the query pattern class method. Must be a valid Python identifier.
        :param qp: Query pattern string
        """
        restricted_kwargs = ('q', 'epoch', 'chunked' 'chunk_size', 'parser')
        if any(kw in restricted_kwargs for kw in re.findall(r'{(\w+)}', qp)):
            warnings.warn(f'Ignoring invalid query pattern: {qp}')
        elif not name.isidentifier() or (name in dir(cls) and name not in cls._user_qp):
            warnings.warn(f'Ignoring invalid query pattern name: {name}')
        else:
            cls._user_qp.add(name)
            setattr(cls, name, pm(cls.query, qp))
