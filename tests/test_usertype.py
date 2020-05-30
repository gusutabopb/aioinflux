# flake8: noqa
import uuid
import enum
from datetime import datetime
from typing import NamedTuple, Optional
from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal

import pytest

import aioinflux
from aioinflux import lineprotocol, SchemaError
from testing_utils import logger


class CpuLoad(enum.Enum):
    LOW = 10
    HIGH = 100


@pytest.mark.asyncio
async def test_decorator(client):
    @lineprotocol
    class MyPoint(NamedTuple):
        measurement: aioinflux.MEASUREMENT
        time: aioinflux.TIMEINT
        host: aioinflux.TAG
        running: aioinflux.BOOL
        users: aioinflux.INT
        cpu_load: aioinflux.FLOAT
        cpu_load_level: aioinflux.ENUM
        cpu_load_level_tag: aioinflux.TAGENUM
        running_cost: aioinflux.DECIMAL
        uuid: aioinflux.STR

    p = MyPoint(
        measurement="dp",
        time=1500,
        host="us1",
        running=True,
        users=1000,
        cpu_load=99.5,
        cpu_load_level=CpuLoad.HIGH,
        cpu_load_level_tag=CpuLoad.LOW,
        running_cost=Decimal('3.54'),
        uuid=str(uuid.uuid4()),
    )
    assert p
    assert hasattr(p, 'to_lineprotocol')
    assert await client.write(p)
    logger.info(await client.query('SELECT * FROM dp'))
    logger.info(await client.query("SHOW FIELD KEYS FROM dp"))


def test_functional():
    schema = dict(
        measurement=aioinflux.MEASUREMENT,
        time=aioinflux.TIMEINT,
        host=aioinflux.TAG,
        running=aioinflux.BOOL,
        users=aioinflux.INT,
    )
    MyPoint = lineprotocol(namedtuple('MyPoint', schema.keys()), schema=schema)
    p = MyPoint("a", 2, "b", False, 5)
    logger.debug(p.to_lineprotocol())
    assert isinstance(p.to_lineprotocol(), bytes)


def test_datestr():
    schema = dict(
        measurement=aioinflux.MEASUREMENT,
        time=aioinflux.TIMESTR,
        host=aioinflux.TAG,
        running=aioinflux.BOOL,
        users=aioinflux.INT,
    )
    MyPoint = lineprotocol(namedtuple('MyPoint', schema.keys()), schema=schema)
    p = MyPoint("a", "2018-08-08 15:22:33", "b", False, 5)
    logger.debug(p.to_lineprotocol())
    assert isinstance(p.to_lineprotocol(), bytes)


def test_datetime():
    schema = dict(
        measurement=aioinflux.MEASUREMENT,
        time=aioinflux.TIMEDT,
        host=aioinflux.TAG,
        running=aioinflux.BOOL,
        users=aioinflux.INT,
    )
    MyPoint = lineprotocol(namedtuple('MyPoint', schema.keys()), schema=schema)
    p = MyPoint("a", datetime.utcnow(), "b", False, 5)
    logger.debug(p.to_lineprotocol())
    assert isinstance(p.to_lineprotocol(), bytes)


def test_placeholder():
    @lineprotocol(placeholder=True)
    @dataclass
    class MyPoint:
        timestamp: aioinflux.TIMEINT

    lp = MyPoint(0).to_lineprotocol()
    logger.debug(lp)


def test_extra_tags():
    @lineprotocol(extra_tags={'host': 'ap1'})
    class MyPoint(NamedTuple):
        measurement: aioinflux.MEASUREMENT
        time: aioinflux.TIMEINT
        running: aioinflux.BOOL
        users: aioinflux.INT

    p = MyPoint("a", 2, False, 5)
    assert b'ap1' in p.to_lineprotocol()


def test_rm_none():
    @lineprotocol(rm_none=True)
    class MyPoint(NamedTuple):
        measurement: aioinflux.MEASUREMENT
        time: aioinflux.TIMEINT
        host: aioinflux.TAG
        running: Optional[aioinflux.BOOL]
        users: Optional[aioinflux.INT]

    p1 = MyPoint("a", 2, "b", True, None)
    p2 = MyPoint("a", 2, "b", None, 1)
    logger.debug(p1.to_lineprotocol())
    logger.debug(p2.to_lineprotocol())
    assert b'users' not in p1.to_lineprotocol()
    assert b'running' not in p2.to_lineprotocol()


# noinspection PyUnusedLocal
def test_schema_error():
    with pytest.raises(SchemaError):
        @lineprotocol
        class MyPoint:
            pass

    with pytest.raises(SchemaError):
        @lineprotocol  # noqa: F811
        class MyPoint(NamedTuple):
            measurement: aioinflux.MEASUREMENT
            time: aioinflux.TIMEINT
            host: aioinflux.TAG
            running: bool
            users: aioinflux.INT

    with pytest.raises(SchemaError):
        @lineprotocol  # noqa: F811
        class MyPoint(NamedTuple):
            measurement: aioinflux.MEASUREMENT
            measurement2: aioinflux.MEASUREMENT
            time: aioinflux.TIMEINT
            host: aioinflux.TAG
            running: aioinflux.BOOL
            users: aioinflux.INT

    with pytest.raises(SchemaError):
        @lineprotocol  # noqa: F811
        class MyPoint(NamedTuple):
            measurement: aioinflux.MEASUREMENT
            time: aioinflux.TIMEINT
            time2: aioinflux.TIMEDT
            host: aioinflux.TAG
            running: aioinflux.BOOL
            users: aioinflux.INT

    with pytest.raises(SchemaError):
        @lineprotocol  # noqa: F811
        class MyPoint(NamedTuple):
            measurement: aioinflux.MEASUREMENT
            time: aioinflux.TIMEINT
            host: aioinflux.TAG
