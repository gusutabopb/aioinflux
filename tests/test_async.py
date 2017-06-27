import pytest

import aioinflux.test_utils as utils


@pytest.mark.asyncio
async def test_ping(async_client):
    assert len(await async_client.ping()) == 4


@pytest.mark.asyncio
async def test_create_database(async_client):
    resp = await async_client.create_database(db='mytestdb')
    assert resp


@pytest.mark.asyncio
async def test_simple_write(async_client):
    print(async_client.db)
    assert await async_client.write(utils.random_points(100))


@pytest.mark.asyncio
async def test_simple_query(async_client):
    resp = await async_client.select_all(measurement='test_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 100


@pytest.mark.asyncio
async def test_chunked_query(async_client):
    resp = await async_client.select_all(measurement='test_measurement', chunked=True, chunk_size=10)
    points = [i async for i in resp]
    assert len(points) == 100


@pytest.mark.asyncio
async def test_drop_measurement(async_client):
    await async_client.drop_measurement(measurement='test_measurement')


@pytest.mark.asyncio
async def test_drop_database(async_client):
    await async_client.drop_database(db='mytestdb')
