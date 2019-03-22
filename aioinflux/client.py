import asyncio
import json
import logging
import warnings
from functools import wraps
from typing import TypeVar, Union, AnyStr, Mapping, Iterable, Optional, AsyncGenerator

import aiohttp

from . import serialization
from .compat import *

if pd:
    PointType = TypeVar('PointType', Mapping, dict, bytes, pd.DataFrame)
    ResultType = TypeVar('ResultType', dict, bytes, pd.DataFrame)
else:
    PointType = TypeVar('PointType', Mapping, dict, bytes)
    ResultType = TypeVar('ResultType', dict, bytes)

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
    """Raised when an server-side error occurs"""
    pass


class InfluxDBWriteError(InfluxDBError):
    """Raised when a server-side writing error occurs"""
    def __init__(self, resp):
        self.status = resp.status
        self.headers = resp.headers
        self.reason = resp.reason
        super().__init__(f'Error writing data ({self.status} - {self.reason}): '
                         f'{self.headers.get("X-Influxdb-Error", "")}')


class InfluxDBClient:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 8086,
        mode: str = 'async',
        output: str = 'json',
        db: Optional[str] = None,
        database: Optional[str] = None,
        ssl: bool = False,
        *,
        unix_socket: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[Union[aiohttp.ClientTimeout, float]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        redis_opts: Optional[dict] = None,
        cache_expiry: int = 86400,
        **kwargs
    ):
        """
        :class:`~aioinflux.client.InfluxDBClient`  holds information necessary
        to interact with InfluxDB.
        It is async by default, but can also be used as a sync/blocking client.
        When querying, responses are returned as parsed JSON by default,
        but can also be wrapped in easily iterable
        wrapper object or be parsed to Pandas DataFrames.
        The three main public methods are the three endpoints of the InfluxDB API, namely:

        1. :meth:`~.InfluxDBClient.ping`
        2. :meth:`~.InfluxDBClient.write`
        3. :meth:`~.InfluxDBClient.query`

        See each of the above methods documentation for further usage details.

        See also: https://docs.influxdata.com/influxdb/latest/tools/api/

        :param host: Hostname to connect to InfluxDB.
        :param port: Port to connect to InfluxDB.
        :param mode: Mode in which client should run. Available options:

           - ``async``: Default mode. Each query/request to the backend will
           - ``blocking``: Behaves in sync/blocking fashion,
             similar to the official InfluxDB-Python client.

        :param output: Output format of the response received from InfluxDB.

           - ``json``: Default format.
             Returns parsed JSON as received from InfluxDB.
           - ``dataframe``: Parses results into :py:class`pandas.DataFrame`.
             Not compatible with chunked responses.

        :param db: Default database to be used by the client.
        :param ssl: If https should be used.
        :param unix_socket: Path to the InfluxDB Unix domain socket.
        :param username: Username to use to connect to InfluxDB.
        :param password: User password.
        :param timeout: Timeout in seconds or :class:`aiohttp.ClientTimeout` object
        :param database: Default database to be used by the client.
            This field is for argument consistency with the official InfluxDB Python client.
        :param loop: Asyncio event loop.
        :param redis_opts: Dict fo keyword arguments for :func:`aioredis.create_redis`
        :param cache_expiry: Expiry time (in seconds) for cached data
        :param kwargs: Additional kwargs for :class:`aiohttp.ClientSession`
        """
        self._loop = loop or asyncio.get_event_loop()
        self._session: aiohttp.ClientSession = None
        self._redis: aioredis.Redis = None
        self._mode = None
        self._output = None
        self._db = None
        self.ssl = ssl
        self.host = host
        self.port = port
        self.mode = mode
        self.output = output
        self.db = database or db

        # ClientSession configuration
        if username:
            kwargs.update(auth=aiohttp.BasicAuth(username, password))
        if unix_socket:
            kwargs.update(connector=aiohttp.UnixConnector(unix_socket, loop=self._loop))
        if timeout:
            if isinstance(timeout, aiohttp.ClientTimeout):
                kwargs.update(timeout=timeout)
            else:
                kwargs.update(timeout=aiohttp.ClientTimeout(total=timeout))
        self.opts = kwargs

        # Cache configuration
        self.redis_opts = redis_opts
        self.cache_expiry = cache_expiry

    async def create_session(self, **kwargs):
        """Creates an :class:`aiohttp.ClientSession`

        Override this or call it with ``kwargs`` to use other :mod:`aiohttp`
        functionality not covered by :class:`~.InfluxDBClient.__init__`
        """
        self.opts.update(kwargs)
        self._session = aiohttp.ClientSession(**self.opts, loop=self._loop)
        if self.redis_opts:
            if aioredis:
                self._redis = await aioredis.create_redis(**self.redis_opts,
                                                          loop=self._loop)
            else:
                warnings.warn(no_redis_warning)

    @property
    def url(self):
        return f'{"https" if self.ssl else "http"}://{self.host}:{self.port}/{{endpoint}}'

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
        if output not in ('json', 'dataframe'):
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
        if self._redis:
            self._redis.close()

    @runner
    async def ping(self) -> dict:
        """Pings InfluxDB

         Returns a dictionary containing the headers of the response from ``influxd``.
         """
        if not self._session:
            await self.create_session()
        async with self._session.get(self.url.format(endpoint='ping')) as resp:
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
        3. A user defined class decorated w/
            :func:`~aioinflux.serialization.usertype.lineprotocol`
        4. A string (``str`` or ``bytes``) properly formatted in InfluxDB's line protocol
        5. An iterable of one of the above

        Input data in formats 1-3 are parsed to the line protocol before being
        written to InfluxDB.
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
        :param rp: Sets the target retention policy for the write.
            If unspecified, data is written to the default retention policy.
        :param tag_columns: Columns to be treated as tags
            (used when writing DataFrames only)
        :param extra_tags: Additional tags to be added to all points passed.
        :return: Returns ``True`` if insert is successful.
            Raises :py:class:`ValueError` otherwise.
        """
        if not self._session:
            await self.create_session()
        if precision is not None:
            # FIXME: Implement. Related issue: aioinflux/pull/13
            raise NotImplementedError("'precision' parameter is not supported yet")
        data = serialization.serialize(data, measurement, tag_columns, **extra_tags)
        params = {'db': db or self.db}
        if rp:
            params['rp'] = rp
        url = self.url.format(endpoint='write')
        async with self._session.post(url, params=params, data=data) as resp:
            if resp.status == 204:
                return True
            raise InfluxDBWriteError(resp)

    @runner
    async def query(
        self,
        q: AnyStr,
        *,
        epoch: str = 'ns',
        chunked: bool = False,
        chunk_size: Optional[int] = None,
        db: Optional[str] = None,
        use_cache: bool = False,
    ) -> Union[AsyncGenerator[ResultType, None], ResultType]:
        """Sends a query to InfluxDB.
        Please refer to the InfluxDB documentation for all the possible queries:
        https://docs.influxdata.com/influxdb/latest/query_language/

        :param q: Raw query string
        :param db: Database to be queried. Defaults to `self.db`.
        :param epoch: Precision level of response timestamps.
            Valid values: ``{'ns', 'u', 'µ', 'ms', 's', 'm', 'h'}``.
        :param chunked: If ``True``, makes InfluxDB return results in streamed batches
            rather than as a single response.
            Returns an AsyncGenerator which yields responses
            in the same format as non-chunked queries.
        :param chunk_size: Max number of points for each chunk. By default, InfluxDB chunks
            responses by series or by every 10,000 points, whichever occurs first.
        :param use_cache:
        :return: Response in the format specified by the combination of
           :attr:`.InfluxDBClient.output` and ``chunked``
        """

        async def _chunked_generator(url, data):
            async with self._session.post(url, data=data) as resp:
                logger.debug(f'{resp.status} (CHUNKED): {q}')
                # Hack to avoid aiohttp raising ValueError('Line is too long')
                # The number 16 is arbitrary (may be too large/small).
                resp.content._high_water *= 16
                async for chunk in resp.content:
                    chunk = json.loads(chunk)
                    self._check_error(chunk)
                    yield chunk

        if not self._session:
            await self.create_session()

        # InfluxDB documentation is wrong regarding `/query` parameters
        # See https://github.com/influxdata/docs.influxdata.com/issues/1807
        if not isinstance(chunked, bool):
            raise ValueError("'chunked' must be a boolean")
        data = dict(q=q, db=db or self.db, chunked=str(chunked).lower(), epoch=epoch)
        if chunked and chunk_size:
            data['chunk_size'] = chunk_size

        url = self.url.format(endpoint='query')
        if chunked:
            if self.mode != 'async':
                raise ValueError("Can't use 'chunked' with non-async mode")
            g = _chunked_generator(url, data)
            if self.output == 'json':
                return g
            elif self.output == 'dataframe':
                raise ValueError("Chunked queries are not support with 'dataframe' output")

        key = f'aioinflux:{q}'
        if use_cache and self._redis and await self._redis.exists(key):
            logger.debug(f'Cache HIT: {q}')
            data = lz4.decompress(await self._redis.get(key))
        else:
            async with self._session.post(url, data=data) as resp:
                data = await resp.read()
                if use_cache and self._redis:
                    logger.debug(f'Cache MISS ({resp.status}): {q}')
                    await self._redis.set(key, lz4.compress(data))
                    await self._redis.expire(key, self.cache_expiry)
                else:
                    logger.debug(f'{resp.status}: {q}')

        data = json.loads(data)
        self._check_error(data)
        if self.output == 'json':
            return data
        elif self.output == 'dataframe':
            return serialization.dataframe.parse(data)
        else:
            raise ValueError('Invalid output format')

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

    # InfluxQL - Data management
    # --------------------------

    def create_database(self, db=None):
        db = db or self.db
        return self.query(f'CREATE DATABASE "{db}"')

    def drop_database(self, db=None):
        db = db or self.db
        return self.query(f'DROP DATABASE "{db}"')

    def drop_measurement(self, measurement):
        return self.query(f'DROP MEASUREMENT "{measurement}"')

    # InfluxQL - Schema exploration
    # -----------------------------

    def show_databases(self):
        return self.query("SHOW DATABASES")

    def show_measurements(self):
        return self.query("SHOW MEASUREMENTS")

    def show_users(self):
        return self.query("SHOW USERS")

    def show_series(self, measurement=None):
        if measurement:
            return self.query(f"SHOW SERIES FROM {measurement}")
        return self.query("SHOW SERIES")

    def show_tag_keys(self, measurement=None):
        if measurement:
            return self.query(f"SHOW TAG KEYS FROM {measurement}")
        return self.query("SHOW TAG KEYS")

    def show_field_keys(self, measurement=None):
        if measurement:
            return self.query(f"SHOW FIELD KEYS FROM {measurement}")
        return self.query("SHOW FIELD KEYS")

    def show_tag_values(self, key, measurement=None):
        if measurement:
            return self.query(f'SHOW TAG VALUES FROM "{measurement}" WITH key = "{key}"')
        return self.query(f'SHOW TAG VALUES WITH key = "{key}"')

    def show_retention_policies(self):
        return self.query("SHOW RETENTION POLICIES")

    # InfluxQL - Other
    # ----------------

    def show_continuous_queries(self):
        return self.query("SHOW CONTINUOUS QUERIES")
