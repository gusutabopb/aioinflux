import pytest
from aioinflux import iterpoints
from testing_utils import logger


@pytest.mark.asyncio
async def test_iterpoints_with_parser(iter_client):
    r = await iter_client.query("SELECT * FROM cpu_load LIMIT 3")
    parser = lambda *x, meta: dict(zip(meta['columns'], x))  # noqa
    for i in iterpoints(r, parser):
        logger.info(i)
        assert 'time' in i
        assert 'value' in i
        assert 'host' in i


@pytest.mark.asyncio
async def test_aiter_point(iter_client):
    resp = await iter_client.query('SELECT * from cpu_load', chunked=True, chunk_size=10)
    points = []
    async for chunk in resp:
        for point in iterpoints(chunk):
            points.append(point)
    assert len(points) == 100


@pytest.mark.asyncio
async def test_iter_point_namedtuple(iter_client):
    from collections import namedtuple
    nt = namedtuple('cpu_load', ['time', 'direction', 'host', 'region', 'value'])

    resp = await iter_client.query('SELECT * from cpu_load')
    points = []
    for point in iterpoints(resp, parser=nt):
        points.append(point)
        assert len(point) == 5
    assert len(points) == 100


def test_iter_multi_series():
    # See https://github.com/gusutabopb/aioinflux/issues/29
    d = {'results': [{'series': [
        {'columns': ['time', 'free', 'total', 'used', 'percent', 'path'],
         'name': 'win_disk',
         'tags': {'instance': 'C:'},
         'values': [[1577419571000000000, 94, 238, 144, 60.49140930175781, 'C:']]},
        {'columns': ['time', 'free', 'total', 'used', 'percent', 'path'],
         'name': 'win_disk',
         'tags': {'instance': 'D:'},
         'values': [[1577419571000000000, 1727, 1863, 136, 7.3103790283203125, 'D:']]},
        {'columns': ['time', 'free', 'total', 'used', 'percent', 'path'],
         'name': 'win_disk',
         'tags': {'instance': 'HarddiskVolume1'},
         'values': [[1577419330000000000, 0, 0, 0, 29.292930603027344, 'HarddiskVolume1']]},
        {'columns': ['time', 'free', 'total', 'used', 'percent', 'path'],
         'name': 'win_disk', 'tags': {'instance': '_Total'},
         'values': [[1577419571000000000, 1821, 2101, 280, 13.345237731933594, '_Total']]}],
        'statement_id': 0}]}
    assert len(list(iterpoints(d))) == 4
