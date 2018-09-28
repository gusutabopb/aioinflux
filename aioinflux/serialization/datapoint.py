import enum
import ciso8601
import time
# noinspection PyUnresolvedReferences
import re  # noqa
from collections import Counter

# noinspection PyUnresolvedReferences
from .common import *  # noqa
from ..compat import pd


class DataPoint:
    """Base class for dynamically generated datapoint class"""
    __slots__ = ()

    def items(self):
        """Returns an iterator over pair of keys and values"""

    def to_dict(self) -> dict:
        """Converts datapoint to a regular dictionary"""

    def to_lineprotocol(self) -> bytes:
        """Returns InfluxDB line protocol representation of datapoint"""


class InfluxType(enum.Enum):
    MEASUREMENT = 0
    TIMEINT = 10
    TIMESTR = 11
    TIMEDT = 12
    TAG = 20
    TAGENUM = 21
    # Fields (>=25)
    PLACEHOLDER = 25
    BOOL = 30
    INT = 40
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


def _make_serializer(schema, meas, rm_none=False, extra_tags=None):
    """Factory of datapoint -> line protocol parsers"""
    tags = []
    fields = []
    ts = None
    meas = meas
    for k, t in schema.items():
        if t is InfluxType.MEASUREMENT:
            meas = f"{{i.{k}}}"
        elif t is InfluxType.TIMEINT:
            ts = f"{{i.{k}}}"
        elif t is InfluxType.TIMESTR:
            if pd:
                ts = f"{{pd.Timestamp(i.{k} or 0).value}}"
            else:
                ts = f"{{dt_to_int(str_to_dt(i.{k}))}}"
        elif t is InfluxType.TIMEDT:
            if pd:
                ts = f"{{pd.Timestamp(i.{k} or 0).value}}"
            else:
                ts = f"{{dt_to_int(i.{k})}}"
        elif t is InfluxType.TAG:
            tags.append(f"{k}={{str(i.{k}).translate(tag_escape)}}")
        elif t is InfluxType.TAGENUM:
            tags.append(f"{k}={{getattr(i.{k}, 'name', i.{k} or None)}}")
        elif t in (InfluxType.FLOAT, InfluxType.BOOL):
            fields.append(f"{k}={{i.{k}}}")
        elif t is InfluxType.INT:
            fields.append(f"{k}={{i.{k}}}i")
        elif t is InfluxType.PLACEHOLDER:
            fields.append(f"{k}=true")
        elif t is InfluxType.STR:
            fields.append(f"{k}=\\\"{{str(i.{k}).translate(str_escape)}}\\\"")
        elif t is InfluxType.ENUM:
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
    f.__doc__ = DataPoint.to_lineprotocol.__doc__
    return f


def datapoint(schema=None, name="DataPoint", *, rm_none=False, fill_none=False, extra_tags=None):
    """Dynamic datapoint class factory

    Can be used as a decorator (similar to Python 3.7 :py:mod:`dataclasses`)
    or as a function (similar to :py:func:`~collections.namedtuple`, but mutable).

    Main characteristics:

      - Supports accessing field values by attribute or subscription
      - Support dict-like iteration via ``items`` method
      - Built-in serialization to InfluxDB line protocol through the ``to_lineprotocol`` method.
      - About 2-3x faster serialization than the ``serialization.mapping`` module.

          - Difference gets smaller (1x-1.5x) when ``rm_none=True`` or when the number of
            fields/tags is very large (20+).

    :param schema: Dictionary-based (functional namedtuple style)
        or @dataclass decorator-based (dataclass style) measurement schema
    :param name: Class name (used when passing schema dictionaries only)
    :param rm_none: Whether apply a regex to remove ``None`` values from.
        If ``False``, passing ``None`` values to boolean, integer or float or time fields
        will result in write errors. Setting to ``True`` is "safer" but impacts performance.
    :param fill_none: Whether or not to set missing fields to ``None``.
        Likely best used together with ``rm_none=True``.
    :param extra_tags: Hard coded tags to be added to every point generated.
    """
    def _datapoint(schema):
        cls_name = getattr(schema, "__name__", name)
        docstring = getattr(schema, '__doc__', DataPoint.__doc__)
        schema = getattr(schema, "__annotations__", schema)
        schema = {k: schema[k] for k in sorted(schema, key=lambda x: schema[x].value)}

        # Sanity check
        c = Counter(schema.values())
        assert c[InfluxType.MEASUREMENT] <= 1
        assert sum([c[e] for e in InfluxType if 0 < e.value < 20]) <= 1  # 0 or 1 timestamp
        assert sum([c[e] for e in InfluxType if e.value >= 25]) > 0      # 1 or more fields

        # Generate __init__
        if fill_none:
            args = ', '.join([f"{k}=None" for k in schema])
        else:
            args = ', '.join(schema)
        exec(
            f"def __init__(self, {args}):\n"
            + "\n".join([f'    self.{k} = {k}' for k in schema])
        )

        def __repr__(self):
            items = [f'{k}={repr(v)}' for k, v in self.items()]
            return f'{cls_name}({", ".join(items)})'

        def items(self):
            for k in self._schema:
                yield k, getattr(self, k)
            yield from self._extra_tags.items()

        cls_attrs = {
            '_schema': schema,
            '_opts': (rm_none, fill_none),
            '_extra_tags': extra_tags or {},
            '__slots__': tuple(schema),
            '__init__': locals()['__init__'],
            '__repr__': locals()['__repr__'],
            '__getitem__': lambda self, item: getattr(self, item),
            '__len__': lambda self: len(self._schema),
            '__iter__': lambda self: iter(self._schema),
            '__eq__': lambda self, other: all(self[k] == other[k] for k in self),
            '__doc__': docstring,
            'items': locals()['items'],
            'to_dict': lambda self: dict(self.items()),
            'to_lineprotocol': _make_serializer(schema, cls_name, rm_none, extra_tags)
        }
        return type(cls_name, (DataPoint,), cls_attrs)

    return _datapoint(schema) if schema else _datapoint
