import pytest
from aioinflux import InfluxDBError, iterpoints
import testing_utils as utils
from testing_utils import logger


@pytest.mark.asyncio
async def test_ping(async_client):
    r = await async_client.ping()
    assert 'X-Influxdb-Version' in r


@pytest.mark.asyncio
async def test_create_database(async_client):
    resp = await async_client.create_database(db='mytestdb')
    assert resp


@pytest.mark.asyncio
async def test_drop_database(async_client):
    resp = await async_client.drop_database(db='mytestdb')
    assert resp


@pytest.mark.asyncio
async def test_simple_write(async_client):
    assert await async_client.write(utils.random_points(100))


@pytest.mark.asyncio
async def test_simple_query(async_client):
    resp = await async_client.query('SELECT * FROM test_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 100


@pytest.mark.asyncio
async def test_chunked_query(async_client):
    resp = await async_client.query('SELECT * FROM test_measurement',
                                    chunked=True, chunk_size=10)
    points = []
    async for chunk in resp:
        for point in iterpoints(chunk):
            points.append(point)
    assert len(points) == 100


@pytest.mark.asyncio
async def test_chunked_query_error(async_client):
    with pytest.raises(InfluxDBError) as e:
        resp = await async_client.query('INVALID QUERY', chunked=True, chunk_size=10)
        _ = [i async for i in resp]
    logger.error(e)


@pytest.mark.asyncio
async def test_empty_chunked_query(async_client):
    resp = await async_client.query('SELECT * FROM fake', chunked=True, chunk_size=10)
    points = []
    async for chunk in resp:
        for point in iterpoints(chunk):
            points.append(point)
    assert len(points) == 0


@pytest.mark.asyncio
async def test_drop_measurement(async_client):
    await async_client.drop_measurement(measurement='test_measurement')
