import pytest
from testing_utils import logger


@pytest.mark.asyncio
async def test_cache(cache_client):
    assert await cache_client.write('foo bar=1')
    q = 'SELECT bar from foo'

    r1 = await cache_client.query(q, use_cache=True)  # Create cache
    logger.debug(r1)
    assert await cache_client._redis.exists(f'aioinflux:{q}')

    r2 = await cache_client.query(q, use_cache=True)  # Get cache
    logger.debug(r2)
    r3 = await cache_client.query(q, use_cache=False)  # Ignore cache

    r1 = r1['results'][0]['series'][0]
    r2 = r2['results'][0]['series'][0]
    r3 = r3['results'][0]['series'][0]
    assert r1 == r2 == r3
