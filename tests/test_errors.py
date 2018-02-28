import pytest

from aioinflux import testing_utils as utils
from aioinflux import AsyncInfluxDBClient, InfluxDBError, logger, set_custom_queries


def test_invalid_data_write(sync_client):
    with pytest.raises(InfluxDBError) as e:
        # Plain invalid data
        sync_client.write(utils.random_string())
    logger.debug(e)

    with pytest.raises(ValueError) as e:
        # Pass function as input data
        sync_client.write(utils.random_string)
    logger.debug(e)

    with pytest.raises(ValueError) as e:
        # Measurement missing
        point = utils.random_point()
        point.pop('measurement')
        sync_client.write(point)
    logger.debug(e)

    with pytest.raises(ValueError) as e:
        # Non-DatetimeIndex DataFrame
        sync_client.write(utils.random_dataframe().reset_index(), measurement='foo')
    logger.debug(e)

    with pytest.raises(ValueError) as e:
        # DataFrame write without specifying measurement
        sync_client.write(utils.random_dataframe())
    logger.debug(e)


def test_invalid_client_mode():
    with pytest.raises(ValueError):
        _ = AsyncInfluxDBClient(db='mytestdb', mode=utils.random_string())


def test_invalid_query(sync_client):
    with pytest.raises(InfluxDBError):
        sync_client.query('NOT A VALID QUERY')


def test_invalid_query_pattern():
    set_custom_queries(my_query='SELECT {q} from {epoch}')
