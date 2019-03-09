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
async def client():
    async with InfluxDBClient(db='client_test', mode='async') as client:
        await client.create_database()
        yield client
        await client.drop_database()


@pytest.fixture(scope='module')
async def cache_client():
    opts = dict(
        db='cache_client_test',
        redis_opts=dict(
            address='redis://localhost:6379/8',
            timeout=5,
        ),
        cache_expiry=600
    )
    async with InfluxDBClient(**opts, mode='async') as client:
        assert await client.create_database()
        yield client
        await client.drop_database()
        await client._redis.flushdb()


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
