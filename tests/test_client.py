import random
import datetime


def random_point():
    point = {'measurement': 'test_measurement',  # '"measurement with quo⚡️es and emoji"',
             'tags': {'tag key with sp🚀ces': 'tag,value,with"commas"'},
             'time': datetime.datetime.now(),
             'fields': {
                 'fi\neld_k\ey': random.randint(0, 200),
                 'quote': '"'
                }
             }
    return point


def random_points(n=10):
    for i in range(n):
        yield random_point()


def test_ping(client):
    assert len(client.ping()) == 4


def test_create_database(client):
    resp = client.create_database(db='mytestdb')
    assert resp['resp'].status == 200


def test_simple_write(client):
    print(client.db)
    assert client.write(random_points(10))


def test_simple_query(client):
    resp = client.select_all(measurement='test_measurement')
    assert len(resp['json']['results'][0]['series'][0]['values']) == 10


def test_drop_measurement(client):
    client.drop_measurement(measurement='test_measurement')


def test_drop_database(client):
    client.drop_database(db='mytestdb')
