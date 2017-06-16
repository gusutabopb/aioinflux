import pytest
from aioinflux import AsyncInfluxDBClient


@pytest.fixture(scope='module')
def client():
    with AsyncInfluxDBClient(database='mytestdb', async=False, log_level=5) as client:
        yield client
