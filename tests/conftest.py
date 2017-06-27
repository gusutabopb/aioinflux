import pytest
import asyncio

from aioinflux import AsyncInfluxDBClient


@pytest.fixture(scope='module')
def sync_client():
    with AsyncInfluxDBClient(database='mytestdb', async=False, log_level=5) as client:
        yield client


@pytest.fixture(scope='module')
def async_client():
    with AsyncInfluxDBClient(database='mytestdb', async=True, log_level=5) as client:
        yield client


@pytest.fixture
def event_loop():
    return asyncio.get_event_loop()
