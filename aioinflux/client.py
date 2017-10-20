import asyncio
import json
import logging
import re
from collections import namedtuple, AsyncGenerator
from functools import partialmethod
from functools import wraps
from typing import Union, AnyStr, Mapping, Iterable, Optional
from urllib.parse import urlencode

import aiohttp
import pandas as pd

from .serialization import parse_data, make_df

PointType = Union[AnyStr, Mapping, pd.DataFrame]


def runner(coro):
    """Function execution decorator."""

    @wraps(coro)
    def inner(self, *args, **kwargs):
        if self.mode == 'async':
            return coro(self, *args, **kwargs)
        resp = self._loop.run_until_complete(coro(self, *args, **kwargs))
        if self.mode == 'dataframe' and coro.__name__ == 'query':
            try:
                return make_df(resp)
            except KeyError:
                return resp
        else:
            return resp

    return inner


class InfluxDBError(Exception):
    pass


class AsyncInfluxDBClient:
    def __init__(self, host: str = 'localhost', port: int = 8086,
                 username: Optional[str] = None, password: Optional[str] = None,
                 db: str = 'testdb', database: Optional[str] = None,
                 loop: asyncio.BaseEventLoop = None,
                 log_level: int = 30, mode: str = 'async'):
        """
        The AsyncInfluxDBClient object holds information necessary to interact with InfluxDB.
        It is async by default, but can also be used as a sync/blocking client and even generate
        Pandas DataFrames from queries.
        The three main public methods are the three endpoints of the InfluxDB API, namely:
        1) AsyncInfluxDBClient.ping
        2) AsyncInfluxDBClient.write
        3) AsyncInfluxDBClient.query
        See each of the above methods documentation for further usage details.
        See also: https://docs.influxdata.com/influxdb/v1.2/tools/api/

        :param host: Hostname to connect to InfluxDB.
        :param port: Port to connect to InfluxDB.
        :param username: Username to use to connect to InfluxDB.
        :param password: User password.
        :param db: Default database to be used by the client.
        :param database: Default database to be used by the client.
            This field is for argument consistency with the official InfluxDB Python client.
        :param loop: Event loop used for processing HTTP requests.
        :param log_level: Logging level. The lower the more verbose. Defaults to INFO (30).
        :param mode: Mode in which client should run.
            Available options are: 'async', 'blocking' and 'dataframe'.
            - 'async': Default mode. Each query/request to the backend will
            - 'blocking': Behaves in sync/blocking fashion, similar to the official InfluxDB-Python client.
            - 'dataframe': Behaves in a sync/blocking fashion, but parsing results into Pandas DataFrames.
                           Similar to InfluxDB-Python's `DataFrameClient`.
        """
        self._logger = self._make_logger(log_level)
        self._loop = asyncio.get_event_loop() if loop is None else loop
        self._auth = aiohttp.BasicAuth(username, password) if username and password else None
        self._session = aiohttp.ClientSession(loop=self._loop, auth=self._auth)
        self._url = f'http://{host}:{port}/{{endpoint}}'
        self.host = host
        self.port = port
        self.db = database or db
        self.mode = mode
        if mode not in {'async', 'blocking', 'dataframe'}:
            raise ValueError('Invalid mode')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close()

    def __del__(self):
        self._session.close()

    def __repr__(self):
        items = {f'{k}={v}' for k, v in vars(self).items() if not k.startswith('_')}
        return f'{type(self).__name__}({", ".join(items)})'

    @runner
    async def ping(self) -> dict:
        """Pings InfluxDB.
         Returns a dictionary containing the headers of the response from `influxd`.
         """
        async with self._session.get(self._url.format(endpoint='ping')) as resp:
            self._logger.info(f'{resp.status}: {resp.reason}')
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
        See also: https://docs.influxdata.com/influxdb/v1.2/write_protocols/line_protocol_reference/

        :param data: Input data (see description above).
        :param tag_columns: Columns that should be treated as tags (used when writing DataFrames only)
        :param measurement: Measurement name. Mandatory when when writing DataFrames only.
            When writing dictionary-like data, this field is treated as the default value
            for points that do not contain a `measurement` field.
        :param extra_tags: Additional tags to be added to all points passed.
        :return: Returns `True` if insert is successful. Raises `ValueError` exception otherwise.
        """
        data = parse_data(data, measurement, tag_columns, **extra_tags)
        self._logger.debug(data)
        url = self._url.format(endpoint='write') + '?' + urlencode(dict(db=self.db))
        async with self._session.post(url, data=data) as resp:
            if resp.status == 204:
                return True
            else:
                msg = f'Error writing data. Response: {resp.status} | {resp.reason}'
                raise InfluxDBError(msg)

    @runner
    async def query(self, q: AnyStr, db=None, epoch='ns',
                    chunked=False, chunk_size=None, **kwargs) -> Union[AsyncGenerator, dict]:
        """Sends a query to InfluxDB.
        Please refer to the InfluxDB documentation for all the possible queries:
        https://docs.influxdata.com/influxdb/v1.2/query_language/spec/#queries

        :param q: Raw query string
        :param db: Database parameter. Defaults to `self.db`
        :param epoch: Precision level of response timestamps.
            Valid values: ``{'ns', 'u', 'µ', 'ms', 's', 'm', 'h'}``.
        :param chunked: Retrieves the points in streamed batches instead of in a single
            response and returns an AsyncGenerator which will yield point by point as
            a Point namedtuple.  Non-alphanumeric field names are not supported.
            WARNING: If there are more than one series in your query result
            points may not be yielded in the correct ascending/descending order
            If client side codes depends on such behavior, make sure queries will only
            return a single series.
        :param chunk_size: Max number of points for each chunk. InfluxDB chunks responses
            by series or by every 10,000 points, whichever occurs first.
        :param kwargs: String interpolation arguments for partial methods
        :return: Returns an async generator if chunked is True, otherwise returns
            a dictionary containing the parsed JSON response.
        """

        async def _chunked_generator(func, url, data):
            async with func(url, **data) as resp:
                async for chunk in resp.content:
                    chunk = json.loads(chunk)
                    if 'error' in chunk:
                        raise InfluxDBError(chunk)
                    for statement in chunk['results']:
                        if 'series' not in statement:
                            continue
                        for series in statement['series']:
                            # Non-alphanumeric field names are not supported for namedtuples
                            # If that is a problem, a regular tuple can be yielded instead:
                            # e.g., tuple(zip(series['columns'], point))
                            field_names = [re.sub('[^0-9a-zA-Z]+', '_', col)
                                           for col in series['columns']]
                            Point = namedtuple('Point', field_names)
                            for point in series['values']:
                                yield Point(*point)

        try:
            db = self.db if db is None else db
            query = q.format(db=db, **kwargs)
        except KeyError as e:
            raise ValueError(f'Missing argument "{e.args[0]}" in {repr(q)}')

        data = dict(q=query, db=db, chunked=str(chunked).lower(), epoch=epoch)
        if chunked and chunk_size:
            data['chunk_size'] = chunk_size
        if q.startswith('SELECT') or q.startswith('SHOW'):
            method = 'get'  # Will fail with SELECT INTO
        else:
            method = 'post'

        url = self._url.format(endpoint='query')
        func = getattr(self._session, method)
        data = dict(params=data) if method == 'get' else dict(data=data)
        self._logger.debug(data)

        if chunked:
            return _chunked_generator(func, url, data)

        async with func(url, **data) as resp:
            self._logger.info(f'{resp.status}: {resp.reason}')
            output = await resp.json()
            self._logger.debug(resp)
            self._logger.debug(output)
            self._check_error(output)
            return output

    # Below are methods that wrap ``AsyncInfluxDBClient.query`` in order to provide
    # convenient access to commonly used query patterns. Named arguments corresponding
    # to the named placed holders in the pre-formatted query string of each of partial methods
    # must be passed (e.g.: `db`, `measurement`, etc).
    # For more complex queries, pass a raw query to ``AsyncInfluxDBClient.query``.
    # Please refer to the InfluxDB documentation for all the possible queries:
    # https://docs.influxdata.com/influxdb/v1.2/query_language/spec/#queries
    create_database = partialmethod(query, q='CREATE DATABASE {db}')
    drop_database = partialmethod(query, q='DROP DATABASE {db}')
    drop_measurement = partialmethod(query, q='DROP MEASUREMENT {measurement}')
    show_databases = partialmethod(query, q='SHOW DATABASES')
    show_measurements = partialmethod(query, q='SHOW MEASUREMENTS')
    show_retention_policies = partialmethod(query, q='SHOW RETENTION POLICIES')
    show_users = partialmethod(query, q='SHOW USERS')
    select_all = partialmethod(query, q='SELECT * FROM {measurement}')

    @staticmethod
    def _make_logger(log_level):
        """Initializes logger"""
        logger = logging.getLogger('aioinflux')
        logger.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s: %(message)s')
        if log_level and not logger.handlers:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
        return logger

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
