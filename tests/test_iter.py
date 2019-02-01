import pytest
from aioinflux import logger, iterpoints


@pytest.mark.asyncio
async def test_iterpoints_with_parser(iter_client):
    r = await iter_client.query("SELECT * FROM cpu_load LIMIT 3")
    parser = lambda x, meta: dict(zip(meta['columns'], x))  # noqa
    for i in iterpoints(r, parser):
        logger.info(i)
        assert 'time' in i
        assert 'value' in i
        assert 'host' in i


@pytest.mark.asyncio
async def test_aiter_point(iter_client):
    resp = await iter_client.select_all(measurement='cpu_load',
                                        chunked=True, chunk_size=10)
    points = []
    async for chunk in resp:
        for point in iterpoints(chunk):
            points.append(point)
    assert len(points) == 100
