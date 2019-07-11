import enum
import ciso8601
import time
import decimal
from collections import Counter
from typing import TypeVar, Optional, Mapping, Union
from datetime import datetime

# noinspection PyUnresolvedReferences
from .common import *  # noqa
from ..compat import pd

__all__ = [
    'lineprotocol', 'SchemaError',
    'MEASUREMENT', 'TIMEINT', 'TIMESTR', 'TIMEDT',
    'TAG', 'TAGENUM',
    'BOOL', 'INT', 'DECIMAL', 'FLOAT', 'STR', 'ENUM',
]

MEASUREMENT = TypeVar('MEASUREMENT', bound=str)
TIMEINT = TypeVar('TIMEINT', bound=int)
TIMESTR = TypeVar('TIMESTR', bound=str)
TIMEDT = TypeVar('TIMEDT', bound=datetime)
TAG = TypeVar('TAG', bound=str)
TAGENUM = TypeVar('TAGENUM', bound=enum.Enum)
BOOL = TypeVar('BOOL', bound=bool)
INT = TypeVar('INT', bound=int)
DECIMAL = TypeVar('DECIMAL', bound=decimal.Decimal)
FLOAT = TypeVar('FLOAT', bound=float)
STR = TypeVar('STR', bound=str)
ENUM = TypeVar('ENUM', bound=enum.Enum)

time_types = [TIMEINT, TIMEDT, TIMESTR]
tag_types = [TAG, TAGENUM]
field_types = [BOOL, INT, DECIMAL, FLOAT, STR, ENUM]
optional_field_types = [Optional[f] for f in field_types]


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
    if sum(c[e] for e in field_types + optional_field_types) < 1 and not placeholder:
        raise SchemaError(f"Must have one or more non-empty "
                          f"field-type attributes {field_types}")


def is_optional(t, base_type):
    """Checks if type hint is Optional[base_type]"""
    # NOTE: The 'typing' module is still "provisional" and documentation sub-optimal,
    #  which requires these kinds instrospection into undocumented implementation details
    # NOTE: May break in Python 3.8
    # TODO: Check if works on Python 3.6
    try:
        cond1 = getattr(t, '__origin__') is Union
        cond2 = {type(None), base_type} == set(getattr(t, '__args__', []))
        if cond1 and cond2:
            return True
    except AttributeError:
        return False
    return False


def _make_serializer(meas, schema, extra_tags, placeholder):  # noqa: C901
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
        elif t is TAG or is_optional(t, TAG):
            tags.append(f"{k}={{str(i.{k}).translate(tag_escape)}}")
        elif t is TAGENUM or is_optional(t, TAGENUM):
            tags.append(f"{k}={{getattr(i.{k}, 'name', i.{k} or None)}}")
        elif t is FLOAT or is_optional(t, FLOAT):
            fields.append(f"{k}={{i.{k}}}")
        elif t is DECIMAL or is_optional(t, DECIMAL):
            fields.append(f"{k}={{i.{k}}}")
        elif t is BOOL or is_optional(t, BOOL):
            fields.append(f"{k}={{i.{k}}}")
        elif t is INT or is_optional(t, INT):
            fields.append(f"{k}={{i.{k}}}i")
        elif t is STR or is_optional(t, STR):
            fields.append(f"{k}=\\\"{{str(i.{k}).translate(str_escape)}}\\\"")
        elif t is ENUM or is_optional(t, ENUM):
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
    f = eval(f'lambda i: f"{fmt}".encode()')
    f.__doc__ = "Returns InfluxDB line protocol representation of user-defined class"
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
    opts = dict(
        schema=schema,
        rm_none=rm_none,
        extra_tags=extra_tags or {},
        placeholder=placeholder,
    )

    def _lineprotocol(cls):
        _schema = schema or getattr(cls, '__annotations__', {})
        # TODO: Raise warning or exception if schema has optionals but rm_none is False
        # for t in _schema.values():
        #     for bt in field_types + tag_types:
        #         if is_optional(t, bt):
        #             warnings.warn("")
        f = _make_serializer(cls.__name__, _schema, extra_tags, placeholder)
        cls.to_lineprotocol = f
        cls.to_lineprotocol.opts = opts
        return cls

    def _rm_none_lineprotocol(cls):

        def _parser_selector(i):
            if not hasattr(i, '_asdict'):
                raise ValueError("'rm_none' can only be used with namedtuples")
            key = tuple([k for k, v in i._asdict().items() if v != '' and v is not None])
            if key not in parsers:
                _schema = schema or getattr(cls, '__annotations__', {})
                _schema = {k: v for k, v in _schema.items() if k in key}
                parsers[key] = _make_serializer(cls.__name__, _schema, extra_tags, placeholder)
            return parsers[key](i)

        parsers = {}
        cls.to_lineprotocol = _parser_selector
        cls.to_lineprotocol.opts = opts
        return cls

    if cls:
        if rm_none:
            # Using rm_none has substantial runtime impact.
            # Best avoided if performance is critical.
            return _rm_none_lineprotocol(cls)
        # No options
        return _lineprotocol(cls)
    else:
        if rm_none:
            return _rm_none_lineprotocol
        return _lineprotocol
