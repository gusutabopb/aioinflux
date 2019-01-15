import uuid
import enum
from datetime import datetime
from typing import NamedTuple
from collections import namedtuple
from dataclasses import dataclass

import pytest

import aioinflux
from aioinflux import lineprotocol


class CpuLoad(enum.Enum):
    LOW = 10
    HIGH = 100


def test_decorator(sync_client):
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
        uuid=str(uuid.uuid4()),
    )
    assert p
    assert hasattr(p, 'to_lineprotocol')
    assert sync_client.write(p)
    print(sync_client.select_all('dp'))
    print(sync_client.query("SHOW FIELD KEYS FROM dp"))


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
    print(p.to_lineprotocol())
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
    print(p.to_lineprotocol())
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
    print(p.to_lineprotocol())
    assert isinstance(p.to_lineprotocol(), bytes)


def test_placeholder():
    @lineprotocol
    @dataclass
    class MyPoint:
        timestamp: aioinflux.TIMEINT
        _: aioinflux.PLACEHOLDER = True

    lp = MyPoint(0).to_lineprotocol()
    print(lp)


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
        running: aioinflux.BOOL
        users: aioinflux.INT

    p = MyPoint("a", 2, "b", True, None)
    print(p.to_lineprotocol())
    assert b'users' not in p.to_lineprotocol()


def test_invalid_type():
    with pytest.raises(KeyError):
        @lineprotocol
        class MyPoint(NamedTuple):
            measurement: aioinflux.MEASUREMENT
            time: aioinflux.TIMEINT
            host: aioinflux.TAG
            running: bool
            users: aioinflux.INT

        assert MyPoint("a", 2, "b", None, 5)

    # noinspection PyArgumentList
    MyEnum = enum.Enum('MyEnum', names=list('ABC'))
    with pytest.raises(TypeError):
        @lineprotocol
        class MyPoint(NamedTuple):
            measurement: aioinflux.MEASUREMENT
            time: aioinflux.TIMEINT
            host: aioinflux.TAG
            running: MyEnum.A
            users: aioinflux.INT

        assert MyPoint("a", 2, "b", None, 5)
