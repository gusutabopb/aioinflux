import enum
import ciso8601
import time
# noinspection PyUnresolvedReferences
import re  # noqa
from collections import Counter
from typing import TypeVar, Optional, Mapping
from datetime import datetime

# noinspection PyUnresolvedReferences
from .common import *  # noqa
from ..compat import pd

__all__ = [
    'lineprotocol', 'SchemaError',
    'MEASUREMENT', 'TIMEINT', 'TIMESTR', 'TIMEDT',
    'TAG', 'TAGENUM',
    'BOOL', 'INT', 'FLOAT', 'STR', 'ENUM',
]

MEASUREMENT = TypeVar('MEASUREMENT', bound=str)
TIMEINT = TypeVar('TIMEINT', bound=int)
TIMESTR = TypeVar('TIMESTR', bound=str)
TIMEDT = TypeVar('TIMEDT', bound=datetime)
TAG = TypeVar('TAG', bound=str)
TAGENUM = TypeVar('TAGENUM', enum.Enum, str)
BOOL = TypeVar('BOOL', bound=bool)
INT = TypeVar('INT', bound=int)
FLOAT = TypeVar('FLOAT', bound=float)
STR = TypeVar('STR', bound=str)
ENUM = TypeVar('ENUM', enum.Enum, str)

time_types = [TIMEINT, TIMEDT, TIMESTR]
field_types = [BOOL, INT, FLOAT, STR, ENUM]


class SchemaError(TypeError):
    """Raised when invalid schema is passed to :func:`lineprotocol`"""


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


def _validate_schema(schema, placeholder):
    c = Counter(schema.values())
    if not c:
        raise SchemaError("Schema/type annotations missing")
    if c[MEASUREMENT] > 1:
        raise SchemaError("Class can't have more than one 'MEASUREMENT' attribute")
    if sum(c[e] for e in time_types) > 1:
        raise SchemaError(f"Can't have more than one timestamp-type attribute {time_types}")
    if sum(c[e] for e in field_types) < 1 and not placeholder:
        raise SchemaError(f"Must have one or more field-type attributes {field_types}")


def _make_serializer(meas, schema, rm_none, extra_tags, placeholder):  # noqa: C901
    """Factory of line protocol parsers"""
    _validate_schema(schema, placeholder)
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
        elif t is STR:
            fields.append(f"{k}=\\\"{{str(i.{k}).translate(str_escape)}}\\\"")
        elif t is ENUM:
            fields.append(f"{k}=\\\"{{getattr(i.{k}, 'name', i.{k} or None)}}\\\"")
        else:
            raise SchemaError(f"Invalid attribute type {k!r}: {t!r}")
    extra_tags = extra_tags or {}
    for k, v in extra_tags.items():
        tags.append(f"{k}={v}")
    if placeholder:
        fields.insert(0, f"_=true")

    sep = ',' if tags else ''
    ts = f' {ts}' if ts else ''
    fmt = f"{meas}{sep}{','.join(tags)} {','.join(fields)}{ts}"
    if rm_none:
        # Has substantial runtime impact. Best avoided if performance is critical.
        # First field can't be removed.
        pat = r',\w+="?None"?i?'
        f = eval('lambda i: re.sub(r\'{}\', "", f"{}").encode()'.format(pat, fmt))
    else:
        f = eval('lambda i: f"{}".encode()'.format(fmt))
    f.__doc__ = "Returns InfluxDB line protocol representation of user-defined class"
    f._args = dict(meas=meas, schema=schema, rm_none=rm_none,
                   extra_tags=extra_tags, placeholder=placeholder)
    return f


def lineprotocol(
        cls=None,
        *,
        schema: Optional[Mapping[str, type]] = None,
        rm_none: bool = False,
        extra_tags: Optional[Mapping[str, str]] = None,
        placeholder: bool = False
):
    """Adds ``to_lineprotocol`` method to arbitrary user-defined classes

    :param cls: Class to monkey-patch
    :param schema: Schema dictionary (attr/type pairs).
    :param rm_none: Whether apply a regex to remove ``None`` values.
        If ``False``, passing ``None`` values to boolean, integer or float or time fields
        will result in write errors. Setting to ``True`` is "safer" but impacts performance.
    :param extra_tags: Hard coded tags to be added to every point generated.
    :param placeholder: If no field attributes are present, add a placeholder attribute (``_``)
        which is always equal to ``True``. This is a workaround for creating field-less points
        (which is not supported natively by InfluxDB)
    """

    def _lineprotocol(cls):
        _schema = schema or getattr(cls, '__annotations__', {})
        f = _make_serializer(cls.__name__, _schema, rm_none, extra_tags, placeholder)
        cls.to_lineprotocol = f
        return cls

    return _lineprotocol(cls) if cls else _lineprotocol
