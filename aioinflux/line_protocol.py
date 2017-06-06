from typing import Iterable, Mapping, AnyStr

import pandas as pd


def parse_data(data):
    if isinstance(data, bytes):
        return data
    elif isinstance(data, str):
        return data.encode('utf-8')
    elif isinstance(data, Mapping):
        return make_line(data)
    elif isinstance(data, Iterable):
        return b'\n'.join([parse_data(i) for i in data])
    else:
        raise ValueError('Invalid input', data)


def make_line(point):
    l = '{measurement},{tags} {fields} {timestamp}'
    l = l.format(measurement=_parse_measurement(point),
                 tags=_parse_tags(point),
                 fields=_parse_fields(point),
                 timestamp=_parse_timestamp(point))
    return l.encode('utf-8')


def _parse_measurement(point):
    return point['measurement']


def _parse_tags(point):
    return ','.join(['{k}={v}'.format(k=k, v=v) for k, v in point['tags'].items()])


def _parse_timestamp(point):
    if 'time' not in point:
        return str()
    else:
        return int(pd.Timestamp(point['time']).asm8)


def _parse_fields(point):
    output = []
    for k, v in point['fields'].items():
        if isinstance(v, int):
            output.append('{k}={v}i'.format(k=k, v=v))
        else:
            output.append('{k}={v}'.format(k=v, v=v))
    return ','.join(output)
