import pytest
from aioinflux import AsyncInfluxDBClient


@pytest.fixture(scope='module')
def client():
    with AsyncInfluxDBClient as client:
        yield client
