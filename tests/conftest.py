import asyncio
import logging.config
from pathlib import Path

import pytest
import yaml

from aioinflux import InfluxDBClient

with open(Path(__file__).parent / 'logging.yml') as f:
    logging.config.dictConfig(yaml.load(f))


@pytest.yield_fixture(scope='module')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='module')
def sync_client():
    with InfluxDBClient(db='mytestdb', mode='blocking') as client:
        client.create_database()
        yield client
        client.drop_database()


@pytest.mark.asyncio
@pytest.fixture(scope='module')
async def async_client():
    async with InfluxDBClient(db='mytestdb', mode='async') as client:
        await client.create_database()
        yield client
        await client.drop_database()


@pytest.fixture(scope='module')
def df_client():
    with InfluxDBClient(db='mytestdb', mode='dataframe') as client:
        client.create_database()
        yield client
        client.drop_database()
