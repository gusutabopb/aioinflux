import itertools
import string
import random
import datetime

import numpy as np
import pandas as pd


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


def random_dataframe():
    """Generates a DataFrame with five random walk columns and a tag column"""
    arr = np.cumsum(np.random.randn(50, 5), axis=1)
    letters = itertools.combinations(string.ascii_uppercase, 3)
    columns = [''.join(triplet) for triplet in random.choices(list(letters), k=5)]
    tags = [chr(i + 65) for i in np.random.randint(0, 5, 50)]
    ix = pd.date_range(end=pd.Timestamp.utcnow(), periods=50, freq='90min')

    df = pd.DataFrame(arr, columns=columns)
    df['tag'] = tags
    df.index = ix
    return df


def random_string():
    return ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))
