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
