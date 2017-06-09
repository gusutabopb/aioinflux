from typing import Iterable, Mapping

import pandas as pd

# Special characters documentation:
# https://docs.influxdata.com/influxdb/v1.2/write_protocols/line_protocol_reference/#special-characters
# Although not in the official docs, new line characters are removed in order to avoid issues.
escape_key = str.maketrans({',': r'\,', ' ': r'\ ', '=': r'\=', '\n': ''})
escape_tag = str.maketrans({',': r'\,', ' ': r'\ ', '=': r'\=', '\n': ''})
escape_str = str.maketrans({'"': r'\"', '\n': ''})
escape_measurement = str.maketrans({',': r'\,', ' ': r'\ ', '\n': ''})

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
    p = dict(measurement=_parse_measurement(point),
             tags=_parse_tags(point),
             fields=_parse_fields(point),
             timestamp=_parse_timestamp(point))
    if point['tags']:
        line = '{measurement},{tags} {fields} {timestamp}'.format(**p)
    else:
        p.pop('tags')
        line = '{measurement} {fields} {timestamp}'.format(**p)
    return line.encode('utf-8')


def _parse_measurement(point):
    return point['measurement'].translate(escape_measurement)


def _parse_tags(point):
    output = []
    for k, v in point['tags'].items():
        k = k.translate(escape_key)
        v = v.translate(escape_tag)
        if not v:
            continue  # ignore blank/null string tags
        output.append('{k}={v}'.format(k=k, v=v))
    if output:
        return ','.join(output)
    else:
        return ''


def _parse_timestamp(point):
    if 'time' not in point:
        return str()
    else:
        return int(pd.Timestamp(point['time']).asm8)


def _parse_fields(point):
    output = []
    for k, v in point['fields'].items():
        k = k.translate(escape_key)
        if isinstance(v, int):
            output.append('{k}={v}i'.format(k=k, v=v))
        elif isinstance(v, bool):
            output.append('{k}={v}'.format(k=k, v=str(v).upper()))
        elif isinstance(v, str):
            output.append('{k}="{v}"'.format(k=k, v=v.translate(escape_str)))
        else:
            output.append('{k}={v}'.format(k=k, v=v))
    return ','.join(output)
