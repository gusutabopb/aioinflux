from datetime import datetime

import pytz
import pytest
from aioinflux.serialization.mapping import _serialize_timestamp
from testing_utils import logger
from aioinflux.compat import pd


def test_timestamp_timezone_parsing():
    dt_naive = datetime(2018, 1, 1)
    dt_aware = datetime(2018, 1, 1, tzinfo=pytz.UTC)
    str_naive = str(dt_naive)
    str_aware = str(dt_aware)

    for i in [dt_naive, dt_aware, str_naive, str_aware]:
        assert _serialize_timestamp({'time': i}) == 1514764800000000000


@pytest.mark.skipif(pd is not None, reason='ciso8601-specific test')
def test_invalid_timestamp_parsing():
    with pytest.raises(ValueError) as e:
        _serialize_timestamp({'time': '2018/01/01'})
    logger.error(e)


def test_invalid_timestamp_parsing2():
    with pytest.raises(ValueError) as e:
        _serialize_timestamp({'time': 'foo'})
    logger.error(e)
