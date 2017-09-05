import pytest
import asyncio

from aioinflux import AsyncInfluxDBClient


@pytest.fixture(scope='module')
def sync_client():
    with AsyncInfluxDBClient(db='mytestdb', mode='blocking', log_level=5) as client:
        client.create_database(db='mytestdb')
        yield client
        client.drop_database(db='mytestdb')


@pytest.fixture(scope='module')
def async_client():
    with AsyncInfluxDBClient(db='mytestdb', mode='async', log_level=5) as client:
        yield client


@pytest.fixture(scope='module')
def df_client():
    with AsyncInfluxDBClient(db='mytestdb', mode='dataframe', log_level=5) as client:
        client.create_database(db='mytestdb')
        yield client
        client.drop_database(db='mytestdb')


@pytest.fixture
def event_loop():
    return asyncio.get_event_loop()
