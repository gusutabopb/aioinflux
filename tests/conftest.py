import asyncio

import pytest

from aioinflux import InfluxDBClient
import testing_utils as utils



@pytest.yield_fixture(scope='module')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='module')
async def async_client():
    async with InfluxDBClient(db='async_client_test', mode='async') as client:
        await client.create_database()
        yield client
        await client.drop_database()


@pytest.fixture(scope='module')
def sync_client():
    with InfluxDBClient(db='sync_client_test', mode='blocking') as client:
        client.create_database()
        yield client
        client.drop_database()


@pytest.fixture(scope='module')
def df_client():
    if utils.pd is None:
        return
    with InfluxDBClient(db='df_client_test', mode='blocking', output='dataframe') as client:
        client.create_database()
        yield client
        client.drop_database()


@pytest.fixture(scope='module')
async def iter_client():
    async with InfluxDBClient(db='iter_client_test', mode='async') as client:
        await client.create_database()
        await client.write([p for p in utils.cpu_load_generator(100)])
        yield client
        await client.drop_database()
