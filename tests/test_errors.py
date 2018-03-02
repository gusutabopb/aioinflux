import pytest

from aioinflux import testing_utils as utils
from aioinflux import InfluxDBClient, InfluxDBError, logger, set_query_pattern


def test_invalid_data_write(sync_client):
    with pytest.raises(InfluxDBError) as e:
        # Plain invalid data
        sync_client.write(utils.random_string())
    logger.error(e)

    with pytest.raises(ValueError) as e:
        # Pass function as input data
        sync_client.write(utils.random_string)
    logger.error(e)

    with pytest.raises(ValueError) as e:
        # Measurement missing
        point = utils.random_point()
        point.pop('measurement')
        sync_client.write(point)
    logger.error(e)

    with pytest.raises(ValueError) as e:
        # Non-DatetimeIndex DataFrame
        sync_client.write(utils.random_dataframe().reset_index(), measurement='foo')
    logger.error(e)

    with pytest.raises(ValueError) as e:
        # DataFrame write without specifying measurement
        sync_client.write(utils.random_dataframe())
    logger.error(e)


def test_invalid_client_mode():
    with pytest.raises(ValueError) as e:
        _ = InfluxDBClient(db='mytestdb', mode=utils.random_string())
    logger.error(e)


def test_invalid_query(sync_client):
    with pytest.raises(InfluxDBError) as e:
        sync_client.query('NOT A VALID QUERY')
    logger.error(e)


def test_invalid_query_pattern():
    with pytest.warns(UserWarning) as e:
        set_query_pattern(my_query='SELECT {q} from {epoch}')
    logger.warning(e)


def test_missing_kwargs(sync_client):
    with pytest.raises(ValueError) as e:
        sync_client.select_all()
    logger.error(e)


def test_statement_error(sync_client):
    with pytest.raises(InfluxDBError) as e:
        sync_client.query('SELECT * FROM my_measurement', db='fake_db')
    logger.error(e)