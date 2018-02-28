import asyncio

import pytest

from aioinflux import AsyncInfluxDBClient, logger

logger.setLevel('DEBUG')


@pytest.yield_fixture(scope='module')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='module')
def sync_client():
    with AsyncInfluxDBClient(db='mytestdb', mode='blocking') as client:
        client.create_database(db='mytestdb')
        yield client
        client.drop_database(db='mytestdb')


@pytest.mark.asyncio
@pytest.fixture(scope='module')
async def async_client():
    async with AsyncInfluxDBClient(db='mytestdb', mode='async') as client:
        logger.debug(client)  # test __repr__
        yield client


@pytest.fixture(scope='module')
def df_client():
    with AsyncInfluxDBClient(db='mytestdb', mode='dataframe') as client:
        client.create_database(db='mytestdb')
        yield client
        client.drop_database(db='mytestdb')
