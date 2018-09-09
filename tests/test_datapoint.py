import uuid
import enum

import pytest

from aioinflux.serialization.datapoint import datapoint, InfluxType, DataPoint


def test_decorator(sync_client):
    @datapoint
    class MyPoint:
        measurement: InfluxType.MEASUREMENT
        time: InfluxType.TIMEINT
        host: InfluxType.TAG
        running: InfluxType.BOOL
        users: InfluxType.INT
        cpu_load: InfluxType.FLOAT
        cpu_load_level: InfluxType.ENUM
        cpu_load_level_tag: InfluxType.TAGENUM
        uuid: InfluxType.STR

    p = MyPoint(
        measurement="dp",
        time=1500,
        host="us1",
        running=True,
        users=1000,
        cpu_load=99.5,
        cpu_load_level=InfluxType.TAG,
        cpu_load_level_tag=InfluxType.TAG,
        uuid=uuid.uuid4(),
    )
    assert p
    assert isinstance(p, DataPoint)
    assert sync_client.write(p)
    print(sync_client.select_all('dp'))
    print(sync_client.query("SHOW FIELD KEYS FROM dp"))


def test_functional():
    MyPoint = datapoint(dict(
        measurement=InfluxType.MEASUREMENT,
        time=InfluxType.TIMEINT,
        host=InfluxType.TAG,
        running=InfluxType.BOOL,
        users=InfluxType.INT,
    ), name='MyPoint')
    assert MyPoint("a", 2, "b", False, 5)


def test_datestr():
    MyPoint = datapoint(dict(
        measurement=InfluxType.MEASUREMENT,
        time=InfluxType.TIMESTR,
        host=InfluxType.TAG,
        running=InfluxType.BOOL,
        users=InfluxType.INT,
    ), name='MyPoint')
    p = MyPoint("a", "2018-08-08 15:22:33", "b", False, 5)
    print(p.to_lineprotocol())


def test_placeholder():
    @datapoint(fill_none=True)
    class MyPoint:
        measurement: InfluxType.MEASUREMENT
        _: InfluxType.PLACEHOLDER
    lp = MyPoint().to_lineprotocol()
    print(lp)


def test_repr():
    MyPoint = datapoint(dict(
        measurement=InfluxType.MEASUREMENT,
        time=InfluxType.TIMEINT,
        host=InfluxType.TAG,
        running=InfluxType.BOOL,
        users=InfluxType.INT,
    ), name='MyPoint')
    print(MyPoint("a", 2, "b", False, 5))


def test_items():
    MyPoint = datapoint(dict(
        measurement=InfluxType.MEASUREMENT,
        time=InfluxType.TIMEINT,
        host=InfluxType.TAG,
        running=InfluxType.BOOL,
        users=InfluxType.INT,
    ), name='MyPoint')
    p = MyPoint("a", 2, "b", False, 5)
    for k, v in p.items():
        print(f"KEY: {k}, VALUE: {v}")


def test_extra_tags():
    MyPoint = datapoint(dict(
        measurement=InfluxType.MEASUREMENT,
        time=InfluxType.TIMEINT,
        running=InfluxType.BOOL,
        users=InfluxType.INT,
    ), name='MyPoint', extra_tags={'host': 'ap1'})
    p = MyPoint("a", 2, False, 5)
    assert b'ap1' in p.to_lineprotocol()


def test_rm_none():
    MyPoint = datapoint(dict(
        measurement=InfluxType.MEASUREMENT,
        time=InfluxType.TIMEINT,
        host=InfluxType.TAG,
        _=InfluxType.PLACEHOLDER,
        running=InfluxType.BOOL,
        users=InfluxType.INT,
    ), name='MyPoint', rm_none=True)
    p = MyPoint("a", 2, None, "b", None, 5)
    assert b'running' not in p.to_lineprotocol()


def test_fill_none():
    MyPoint = datapoint(dict(
        measurement=InfluxType.MEASUREMENT,
        time=InfluxType.TIMEINT,
        host=InfluxType.TAG,
        _=InfluxType.PLACEHOLDER,
        running=InfluxType.BOOL,
        users=InfluxType.INT,
        userz=InfluxType.ENUM,
        userx=InfluxType.TAGENUM,
    ), name='MyPoint', rm_none=True, fill_none=True)
    p = MyPoint("a", 2, None, "b", users=2)
    assert b'running' not in p.to_lineprotocol()


def test_invalid_type():
    with pytest.raises(AttributeError):
        MyPoint = datapoint(dict(
            measurement=InfluxType.MEASUREMENT,
            time=InfluxType.TIMEINT,
            host=InfluxType.TAG,
            running=bool,
            users=InfluxType.INT,
        ), name='MyPoint')
        assert MyPoint("a", 2, "b", None, 5)

    # noinspection PyArgumentList
    MyEnum = enum.Enum('MyEnum', names=list('ABC'))
    with pytest.raises(TypeError):
        MyPoint = datapoint(dict(
            measurement=InfluxType.MEASUREMENT,
            time=InfluxType.TIMEINT,
            host=InfluxType.TAG,
            running=MyEnum.A,
            users=InfluxType.INT,
        ), name='MyPoint')
        assert MyPoint("a", 2, "b", None, 5)
