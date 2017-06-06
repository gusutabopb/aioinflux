import asyncio
import logging
from typing import Union, AnyStr, Mapping, Iterable
from urllib.parse import urlencode

import aiohttp

from .line_protocol import parse_data

PointType = Union[AnyStr, Mapping]


class AsyncInfluxDBClient:

    def __init__(self, host='localhost', port=8086, db='testdb',
                 username=None, password=None, loop=None, log_level=None):
        self.logger = self._make_logger(log_level)
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.db = db
        self.base_url = f'http://{host}:{port}/'
        self.query_url = self.base_url + 'query'
        self.write_url = self.base_url + 'write'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    async def create_database(self, dbname):
        data = dict(q=f'CREATE DATABASE {dbname}')
        return await self._post(self.query_url, data=data)

    async def write(self, data: Union[PointType, Iterable[PointType]]):
        """Write query to InfluxDB."""
        data = parse_data(data)
        self.logger.debug(data)
        url = self.write_url + '?' + urlencode(dict(db=self.db))
        return await self._post(url, data=data)

    async def query(self, q: AnyStr, epoch=None):
        """Send a query to InfluxDB."""
        data = dict(q=q, db=self.db)
        if epoch:
            data['epoch'] = epoch
        return await self._post(self.query_url, data=data)

    def run(self, coro, *args, **kwargs):
        """Testing function"""
        return self.loop.run_until_complete(coro(*args, **kwargs))

    async def _post(self, *args, **kwargs):
        async with self.session.post(*args, **kwargs) as resp:
            self.logger.debug(f'{resp.status}: {resp.reason}')
            return await resp.json()

    @staticmethod
    def _make_logger(log_level):
        logger = logging.getLogger('aioinflux')
        formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s: %(message)s')
        if log_level and not logger.handlers:
            logger.setLevel(log_level)
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
        return logger
