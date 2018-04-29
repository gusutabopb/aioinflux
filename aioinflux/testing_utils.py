import datetime
import random
import string
import uuid
from itertools import combinations, cycle, islice

from . import pd, np, no_pandas_warning

import pytest

requires_pandas = pytest.mark.skipif(pd is None, reason=no_pandas_warning)


def random_point():
    now = datetime.datetime.now()
    point = {'measurement': 'test_measurement',
             'tags': {'tag key with sp🚀ces': 'tag,value,with"commas"'},
             'time': random.choice([now, str(now)]),
             'fields': {
                 'fi\neld_k\ey': random.randint(0, 200),
                 'quote': '"',
                 'value': random.random(),
                }
             }
    return point


def random_points(n=10):
    for i in range(n):
        yield random_point()


def random_dataframe():
    """Generates a DataFrame with five random walk columns and a tag column"""
    arr = np.cumsum(np.random.randn(50, 5), axis=1)
    letters = combinations(string.ascii_uppercase, 3)
    columns = [''.join(triplet) for triplet in random.choices(list(letters), k=5)]
    tags = [chr(i + 65) for i in np.random.randint(0, 5, 50)]
    ix = pd.date_range(end=pd.Timestamp.utcnow(), periods=50, freq='90min')

    df = pd.DataFrame(arr, columns=columns)
    df['tag'] = tags
    df['noise'] = list(islice(cycle(["a", '\n', r"\n"]), 50))
    df.index = ix
    return df


def trading_df(N=100):
    sym = [''.join(i) for i in combinations('ABCDE', 3)]

    df = pd.DataFrame({
        'str_id': [str(uuid.uuid4()) for _ in range(N)],
        'px': 1000 + np.cumsum(np.random.randint(-10, 11, N)) / 2,
        'sym': np.random.choice(sym, N),
        'side': np.random.choice(['BUY', 'SELL'], N),
        'size': np.random.randint(1, 10, size=N) * 100,
        'valid': np.random.randint(2, size=N).astype('bool')
    })
    df.index = pd.date_range(end=pd.Timestamp.utcnow(), periods=N, freq='1s')
    df['side'] = df['side'].astype('category')
    return df


def random_string():
    return ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))


def cpu_load_generator(n):
    p = 'cpu_load,direction={d},host=server{s:02d},region=us-{r} value={f:.5f} {t}'
    t = 1520535379386016000
    d = ['in', 'out']
    r = ['north', 'south', 'west', 'east']
    for _ in range(n):
        t += random.randint(1, 10 ** 10)
        yield p.format(t=t,
                       d=random.choice(d),
                       r=random.choice(r),
                       s=random.randint(1, 99),
                       f=random.random() * 10)
