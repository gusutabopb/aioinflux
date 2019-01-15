import enum
import ciso8601
import time
# noinspection PyUnresolvedReferences
import re  # noqa
from collections import Counter
from typing import TypeVar

# noinspection PyUnresolvedReferences
from .common import *  # noqa
from ..compat import pd


MEASUREMENT = TypeVar('MEASUREMENT')
TIMEINT = TypeVar('TIMEINT')
TIMESTR = TypeVar('TIMESTR')
TIMEDT = TypeVar('TIMEDT')
TAG = TypeVar('TAG')
TAGENUM = TypeVar('TAGENUM', enum.Enum, str)
PLACEHOLDER = TypeVar('PLACEHOLDER')
BOOL = TypeVar('BOOL')
INT = TypeVar('INT')
FLOAT = TypeVar('FLOAT')
STR = TypeVar('STR')
ENUM = TypeVar('ENUM', enum.Enum, str)

influx_types = {
    MEASUREMENT: 0,
    TIMEINT: 10,
    TIMESTR: 11,
    TIMEDT: 12,
    TAG: 20,
    TAGENUM: 21,
    # Fields (>25)
    PLACEHOLDER: 25,
    BOOL: 30,
    INT: 40,
    FLOAT: 50,
    STR: 60,
    ENUM: 61,
}


def str_to_dt(s):
    dt = ciso8601.parse_datetime(s)
    if dt:
        return dt
    raise ValueError(f'Invalid datetime string: {dt!r}')


def dt_to_int(dt):
    if not dt.tzinfo:
        # Assume tz-naive input to be in UTC, not local time
        return int(dt.timestamp() - time.timezone) * 10 ** 9 + dt.microsecond * 1000
    return int(dt.timestamp()) * 10 ** 9 + dt.microsecond * 1000


def _make_serializer(schema, meas, rm_none=False, extra_tags=None):
    """Factory of line protocol parsers"""
    tags = []
    fields = []
    ts = None
    meas = meas
    for k, t in schema.items():
        if t is MEASUREMENT:
            meas = f"{{i.{k}}}"
        elif t is TIMEINT:
            ts = f"{{i.{k}}}"
        elif t is TIMESTR:
            if pd:
                ts = f"{{pd.Timestamp(i.{k} or 0).value}}"
            else:
                ts = f"{{dt_to_int(str_to_dt(i.{k}))}}"
        elif t is TIMEDT:
            if pd:
                ts = f"{{pd.Timestamp(i.{k} or 0).value}}"
            else:
                ts = f"{{dt_to_int(i.{k})}}"
        elif t is TAG:
            tags.append(f"{k}={{str(i.{k}).translate(tag_escape)}}")
        elif t is TAGENUM:
            tags.append(f"{k}={{getattr(i.{k}, 'name', i.{k} or None)}}")
        elif t in (FLOAT, BOOL):
            fields.append(f"{k}={{i.{k}}}")
        elif t is INT:
            fields.append(f"{k}={{i.{k}}}i")
        elif t is PLACEHOLDER:
            fields.append(f"{k}=true")
        elif t is STR:
            fields.append(f"{k}=\\\"{{str(i.{k}).translate(str_escape)}}\\\"")
        elif t is ENUM:
            fields.append(f"{k}=\\\"{{getattr(i.{k}, 'name', i.{k} or None)}}\\\"")
        else:
            raise TypeError(f"Unknown type: {t!r}")
    extra_tags = extra_tags or {}
    for k, v in extra_tags.items():
        tags.append(f"{k}={v}")

    sep = ',' if tags else ''
    ts = f' {ts}' if ts else ''
    fmt = f"{meas}{sep}{','.join(tags)} {','.join(fields)}{ts}"
    if rm_none:
        # Has substantial runtime impact. Best avoided if performance is critical.
        # First field can't be removed.
        pat = ',\w+="?None"?i?'
        f = eval('lambda i: re.sub(r\'{}\', "", f"{}").encode()'.format(pat, fmt))
    else:
        f = eval('lambda i: f"{}".encode()'.format(fmt))
    f.__doc__ = "Returns InfluxDB line protocol representation of user-defined class"
    return f


def lineprotocol(cls=None, *, schema=None, rm_none=False, extra_tags=None):
    """Adds to_lineprotocol method to arbitrary user-defined classes

    Can be used as a decorator or as a regular function
    (for namedtuples generated functionally).

    Main characteristics:

      - Built-in serialization to InfluxDB line protocol through the ``to_lineprotocol`` method.
      - About 2-3x faster serialization than the ``serialization.mapping`` module.

          - Difference gets smaller (1x-1.5x) when ``rm_none=True`` or when the number of
            fields/tags is very large (20+).

    :param schema: Dictionary-based (functional namedtuple style)
        or @dataclass decorator-based (dataclass style) measurement schema
    :param rm_none: Whether apply a regex to remove ``None`` values from.
        If ``False``, passing ``None`` values to boolean, integer or float or time fields
        will result in write errors. Setting to ``True`` is "safer" but impacts performance.
    :param extra_tags: Hard coded tags to be added to every point generated.
    """

    def _lineprotocol(cls):
        cls_name = getattr(cls, "__name__")
        _schema = schema or getattr(cls, "__annotations__")
        _schema = {k: _schema[k] for k in sorted(_schema, key=lambda x: influx_types[_schema[x]])}

        # Sanity check
        c = Counter(_schema.values())
        assert c[MEASUREMENT] <= 1
        assert sum([c[e] for e, v in influx_types.items() if 0 < v < 20]) <= 1  # 0 or 1 timestamp
        assert sum([c[e] for e, v in influx_types.items() if v >= 25]) > 0  # 1 or more fields

        cls._schema = _schema
        cls._opts = (rm_none,),
        cls._extra_tags = extra_tags or {},
        cls.to_lineprotocol = _make_serializer(_schema, cls_name, rm_none, extra_tags)

        return cls

    return _lineprotocol(cls) if cls else _lineprotocol


__all__ = [t.__name__ for t in influx_types] + ['lineprotocol']
