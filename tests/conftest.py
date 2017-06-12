import pytest
from aioinflux import AsyncInfluxDBClient


@pytest.fixture(scope='module')
def client():
    with AsyncInfluxDBClient(database='mytestdb', sync=True) as client:
        yield client
