import asyncio
import json
import logging
from functools import partialmethod
from functools import wraps
from typing import Union, AnyStr, Mapping, Iterable, Optional
from urllib.parse import urlencode

import aiohttp
import pandas as pd

from .line_protocol import parse_data

PointType = Union[AnyStr, Mapping]


def runner(coro):
    """Function execution decorator."""

    @wraps(coro)
    def inner(self, *args, **kwargs):
        if not self.sync:
            return coro(self, *args, **kwargs)
        resp = self.loop.run_until_complete(coro(self, *args, **kwargs))
        if self.dataframe and coro.__name__ == 'query':
            return self.make_df(resp)
        else:
            return resp

    return inner


class AsyncInfluxDBClient:
    def __init__(self, host: str = 'localhost', port: int = 8086,
                 username: Optional[str] = None, password: Optional[str] = None,
                 database: str = 'testdb', loop: asyncio.BaseEventLoop = None,
                 log_level: int = 30, dataframe: bool = False, sync: bool = False):
        """
        The AsyncInfluxDBClient object holds information necessary to interect with InfluxDB.
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
        :param database: Default database to be used by the client.
        :param loop: Event loop used for processing HTTP requests.
        :param log_level: Logging level. The lower the more verbose. Defaults to INFO (30).
        :param dataframe: Setting to `True` make query results be parsed into a Pandas DataFrame.
                          When set to `False` (default), query results will be returned as dictionaries.
        :param sync: Setting to `True` will make the client behave in a sychronous way.
                     Setting `self.dataframe` to True automatically sets `sync` to True as well.
        """
        self.logger = self._make_logger(log_level)
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.auth = aiohttp.BasicAuth(username, password) if username and password else None
        self.session = aiohttp.ClientSession(loop=self.loop, auth=self.auth)
        self.db = database
        self.url = f'http://{host}:{port}/{{endpoint}}'
        self.dataframe = dataframe
        self.sync = sync or dataframe

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def __del__(self):
        self.session.close()

    @runner
    async def ping(self) -> dict:
        """Ping InfluxDB. Returns a dictionary containing the headers of the response from `influxd`."""
        async with self.session.get(self.url.format(endpoint='ping')) as resp:
            self.logger.info(f'{resp.status}: {resp.reason}')
            return dict(resp.headers.items())

    @runner
    async def write(self, data: Union[PointType, Iterable[PointType]]) -> bool:
        """
        Write query to InfluxDB.
        Input can be:
        1) a string properly formatted in InfluxDB's line protocol
        2) a dictionary containing four items ('measurement', 'time', 'tags', 'fields')
        3) a Pandas DataFrame with a DatetimeIndex
        4) an iterable of one of above
        Input data in the 2-4 formats are parsed to the line protocol before being written to InfluxDB.
        See also: https://docs.influxdata.com/influxdb/v1.2/write_protocols/line_protocol_reference/

        :param data: Input data (see description above).
        :return: Returns `True` if insert is sucessfull. Raises `ValueError` exception otherwise.
        """
        data = parse_data(data)
        self.logger.debug(data)
        url = self.url.format(endpoint='write') + '?' + urlencode(dict(db=self.db))
        async with self.session.post(url, data=data) as resp:
            if resp.status == 204:
                return True
            else:
                msg = f'Error writing data. Response: {resp.status} | {resp.reason}'
                raise ValueError(msg)

    @runner
    async def query(self, q: AnyStr, db=None, epoch='ns', chunked=False, chunk_size=None, **kwargs):
        """
        Send a query to InfluxDB.
        https://docs.influxdata.com/influxdb/v1.2/tools/api/#query-string-parameters

        :param q: Raw query string
        :param db: Database parameter. Defaults to `self.db`
        :param epoch:
        :param chunked:
        :param chunk_size:
        :param kwargs: String interpolation arguments for partialmethods
        """
        kwargs['db'] = self.db if db is None else db
        data = dict(q=q.format(**kwargs), chunked=str(chunked).lower(), epoch=epoch)
        if chunked and chunk_size:
            data['chunk_size'] = chunk_size
        if q.startswith('SELECT') or q.startswith('SHOW'):
            method = 'post'  # Won't work with SELECT INTO
            if db is None:
                data['db'] = self.db
        else:
            method = 'post'

        url = self.url.format(endpoint='query')
        func = getattr(self.session, method)
        data = dict(params=data) if method == 'get' else dict(data=data)
        async with func(url, **data) as resp:
            self.logger.info(f'{resp.status}: {resp.reason}')
            if chunked:
                output = dict(resp=resp, json=[json.loads(chunk) async for chunk in resp.content])
            else:
                output = dict(resp=resp, json=await resp.json())
            self.logger.debug(output['json'])
            return output

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
        logger = logging.getLogger('aioinflux')
        logger.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s: %(message)s')
        if log_level and not logger.handlers:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
        return logger

    @staticmethod
    def make_df(resp):
        def _make_df(series):
            df = pd.DataFrame(series['values'], columns=series['columns'])
            df = df.set_index(pd.to_datetime(df['time'])).drop('time', axis=1)
            df.index = df.index.tz_localize('UTC')
            df.index.name = None
            if 'name' in series:
                df.name = series['name']
            return df

        return [(series['name'], _make_df(series))
                for statement in resp['json']['results']
                for series in statement['series']]
