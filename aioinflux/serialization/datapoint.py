import enum
import ciso8601
import time
# noinspection PyUnresolvedReferences
import re  # noqa
from collections import Counter

# noinspection PyUnresolvedReferences
from .common import *  # noqa
from .. import pd


class DataPoint:
    pass


class InfluxType(enum.Enum):
    MEASUREMENT = 0
    TIMEINT = 10
    TIMESTR = 11
    TIMEDT = 12
    TAG = 20
    # Fields (>=30)
    BOOL = 30
    INT = 40
    DATETIME = 41
    TIMEDELTA = 42
    FLOAT = 50
    STR = 60
    ENUM = 61


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


def td_to_int(td):
    return int(td.total_seconds()) * 10 ** 9 + td.microseconds * 1000


def _gen_parser(schema, cls_name, rm_none=False, extra_tags=None):
    """Factory of datapoint -> line protocol parsers"""
    tags = []
    fields = []
    ts = None
    meas = cls_name
    for k, t in schema.items():
        if t is InfluxType.MEASUREMENT:
            meas = f"{{i['{k}']}}"
        elif t is InfluxType.TIMEINT:
            ts = f"{{i['{k}']}}"
        elif t is InfluxType.TIMESTR:
            if pd:
                ts = f"{{pd.Timestamp(i['{k}']).value}}"
            else:
                ts = f"{{dt_to_int(str_to_dt(i['{k}']))}}"
        elif t is InfluxType.TIMEDT:
            if pd:
                ts = f"{{pd.Timestamp(i['{k}']).value}}"
            else:
                ts = f"{{dt_to_int(i['{k}'])}}"
        elif t is InfluxType.TAG:
            tags.append(f"{k}={{str(i['{k}']).translate(tag_escape)}}")
        elif t in (InfluxType.FLOAT, InfluxType.BOOL):
            fields.append(f"{k}={{i['{k}']}}")
        elif t is InfluxType.INT:
            fields.append(f"{k}={{i['{k}']}}i")
        elif t is InfluxType.DATETIME:
            if pd:
                fields.append(f"{k}={{pd.Timestamp(i['{k}']).value}}i")
            else:
                fields.append(f"{k}={{dt_to_int(i['{k}'])}}i")
        elif t is InfluxType.TIMEDELTA:
            if pd:
                fields.append(f"{k}={{pd.Timedelta(i['{k}']).value}}i")
            else:
                fields.append(f"{k}={{td_to_int(i['{k}'])}}i")
        elif t is InfluxType.STR:
            fields.append(f"{k}=\\\"{{(str(i['{k}']) or '').translate(str_escape)}}\\\"")
        else:
            raise NotImplementedError(f"Unknown type: {t!r}")
    extra_tags = extra_tags or {}
    for k in extra_tags:
        tags.append(f"{k}={{extra_tags['{k}']}}")

    sep = ',' if tags else ''
    fmt = f"{meas}{sep}{','.join(tags)} {','.join(fields)} {ts}"
    print(fmt)
    if rm_none:
        # Have 1-2us runtime impact. First field CAN'T be removed.
        pat = ',\w+="?None"?i?'
        f = eval('lambda i: re.sub(\'{}\', "", f"{}").encode()'.format(pat, fmt))
    else:
        f = eval('lambda i: f"{}".encode()'.format(fmt))
    return f


def datapoint(schema=None, name="DataPoint", *, rm_none=False, extra_tags=None):
    def _datapoint(schema):
        """Dynamic datapoint class factory
        Can be used as a decorator (similar to Python 3.7 Dataclasses)
        or as a function (similar to namedtuple).

        Datapoints have the following characteristics:
        - Similar to a dataclass/attrs, but more specialized
        - Highly efficient thanks to the usage of __slots__
            (similar or faster object generation than namedtuple, ctypes, protobuf, etc)
        - Supports accessing field values by attribute or subscription
        - Support dict-like iteration via ``items`` method
        - Built-in serialization to InfluxDB line protocol through the ``to_lineprotocol`` method.
        """
        cls_name = getattr(schema, "__name__", name)
        schema = getattr(schema, "__annotations__", schema)
        schema = {k: schema[k] for k in sorted(schema, key=lambda x: schema[x].value)}

        # Sanity check
        c = Counter(schema.values())
        if not issubclass(type(schema), type):
            # Require measurement field if schema is passed as a dictionary
            assert c[InfluxType.MEASUREMENT] == 1

        assert sum([c[e] for e in InfluxType if 0 < e.value < 20]) == 1  # ONE timestamp
        assert sum([c[e] for e in InfluxType if e.value >= 30]) > 0      # ONE+ fields

        # Generate __init__
        exec(
            f"def __init__(self, {', '.join(schema)}):\n"
            + "\n".join([f'    self.{k} = {k}' for k in schema])
        )

        def __repr__(self):
            items = [f'{k}={repr(v)}' for k, v in self.items()]
            return f'{cls_name}({", ".join(items)})'

        def items(self):
            for k in self._schema:
                yield k, getattr(self, k)

        cls_attrs = {
            '_schema': schema,
            '__slots__': tuple(schema),
            '__init__': locals()['__init__'],
            '__repr__': locals()['__repr__'],
            '__getitem__': lambda self, item: getattr(self, item),
            '__len__': lambda self: len(self._schema),
            '__iter__': lambda self: iter(self._schema),
            '__eq__': lambda self, other: all(self[k] == other[k] for k in self),
            '__doc__': getattr(schema, '__doc__', ''),
            'items': locals()['items'],
            'to_dict': lambda self: dict(self.items()),
            'to_lineprotocol': _gen_parser(schema, cls_name, rm_none, extra_tags)
        }
        return type(cls_name, (DataPoint,), cls_attrs)

    return _datapoint(schema) if schema else _datapoint
