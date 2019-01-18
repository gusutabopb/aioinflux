import time
from typing import Mapping

import ciso8601

from .common import *


def serialize(point: Mapping, measurement=None, **extra_tags) -> bytes:
    """Converts dictionary-like data into a single line protocol line (point)"""
    tags = _serialize_tags(point, extra_tags)
    return (
        f'{_serialize_measurement(point, measurement)}'
        f'{"," if tags else ""}{tags} '
        f'{_serialize_fields(point)} '
        f'{_serialize_timestamp(point)}'
    ).encode()


def _serialize_measurement(point, measurement):
    try:
        return escape(point['measurement'], measurement_escape)
    except KeyError:
        if measurement is None:
            raise ValueError("'measurement' missing")
        return escape(measurement, measurement_escape)


def _serialize_tags(point, extra_tags):
    output = []
    for k, v in {**point.get('tags', {}), **extra_tags}.items():
        k = escape(k, key_escape)
        v = escape(v, tag_escape)
        if not v:
            continue  # ignore blank/null string tags
        output.append(f'{k}={v}')
    return ','.join(output)


def _serialize_timestamp(point):
    dt = point.get('time')
    if not dt:
        return ''
    elif isinstance(dt, int):
        return dt
    elif isinstance(dt, (str, bytes)):
        dt = ciso8601.parse_datetime(dt)
        if not dt:
            raise ValueError(f'Invalid datetime string: {dt!r}')

    if not dt.tzinfo:
        # Assume tz-naive input to be in UTC, not local time
        return int(dt.timestamp() - time.timezone) * 10 ** 9 + dt.microsecond * 1000
    return int(dt.timestamp()) * 10 ** 9 + dt.microsecond * 1000


def _serialize_fields(point):
    """Field values can be floats, integers, strings, or Booleans."""
    output = []
    for k, v in point['fields'].items():
        k = escape(k, key_escape)
        if isinstance(v, bool):
            output.append(f'{k}={v}')
        elif isinstance(v, int):
            output.append(f'{k}={v}i')
        elif isinstance(v, str):
            output.append(f'{k}="{v.translate(str_escape)}"')
        elif v is None:
            # Empty values
            continue
        else:
            # Floats
            output.append(f'{k}={v}')
    return ','.join(output)
