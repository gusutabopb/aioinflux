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


def test_drop_database(sync_client):
    sync_client.drop_database(db='mytestdb')
