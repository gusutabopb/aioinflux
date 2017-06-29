import pytest

import aioinflux.test_utils as utils


def test_ping(sync_client):
    assert len(sync_client.ping()) == 4


def test_create_database(sync_client):
    resp = sync_client.create_database(db='mytestdb')
    assert resp


def test_simple_write(sync_client):
    print(sync_client.db)
    assert sync_client.write(utils.random_points(10))


def test_simple_query(sync_client):
    resp = sync_client.select_all(measurement='test_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 10


def test_drop_measurement(sync_client):
    sync_client.drop_measurement(measurement='test_measurement')


def test_write_with_custom_measurement(sync_client):
    points = [p for p in utils.random_points(5)]
    for p in points:
        _ = p.pop('measurement')
    print(points)
    with pytest.raises(ValueError):
        assert sync_client.write(points)
    assert sync_client.write(points, measurement='another_measurement')
    resp = sync_client.select_all(measurement='another_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 5


def test_write_without_tags(sync_client):
    points = [p for p in utils.random_points(7)]
    for p in points:
        _ = p.pop('tags')
    print(points)
    assert sync_client.write(points, mytag='foo')
    resp = sync_client.select_all(measurement='test_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 7


def test_write_without_timestamp(sync_client):
    points = [p for p in utils.random_points(9)]
    for p in points:
        _ = p.pop('time')
        _ = p.pop('measurement')
    print(points)
    assert sync_client.write(points, measurement='yet_another_measurement')
    resp = sync_client.select_all(measurement='yet_another_measurement')
    # Points with the same tag/timestamp set are overwritten
    assert len(resp['results'][0]['series'][0]['values']) == 1


def test_write_non_string_identifier_and_tags(sync_client):
    point = dict(tags={1: 2},
                 fields={3: 4})
    with pytest.warns(UserWarning):
        assert sync_client.write(point, measurement='my_measurement')
    resp = sync_client.select_all(measurement='my_measurement')
    print(resp)
    assert len(resp['results'][0]['series'][0]['values']) == 1


def test_drop_database(sync_client):
    sync_client.drop_database(db='mytestdb')
