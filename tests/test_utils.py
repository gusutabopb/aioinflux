import inspect

from aioinflux import iterpoints, logger


def test_set_query_patterns(sync_client):
    sync_client.set_query_pattern(my_query='SELECT * FROM my_measurement WHERE time > now() - {day}d')
    assert inspect.ismethod(sync_client.my_query.func)
    assert sync_client.my_query(1)


def test_iterpoints_with_parser(sync_client):
    point = 'm1,host=server02,region=us-west load=0.55 1422568543702900257'
    assert sync_client.write(point)
    r = sync_client.query("SELECT * FROM m1 LIMIT 10")
    for i in iterpoints(r, parser=lambda x, meta: dict(zip(meta['columns'], x))):
        logger.info(i)
        assert 'time' in i
        assert 'load' in i
        assert 'host' in i
