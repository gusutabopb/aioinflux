import pytest
from aioinflux import (InfluxDBClient, InfluxDBError, InfluxDBWriteError,
                       logger, testing_utils as utils)
from aioinflux.compat import pd


def test_ping(sync_client):
    r = sync_client.ping()
    assert 'X-Influxdb-Version' in r


def test_create_database(sync_client):
    resp = sync_client.create_database(db='mytestdb')
    assert resp


def test_drop_database(sync_client):
    sync_client.drop_database(db='mytestdb')


def test_simple_write(sync_client):
    logger.debug(sync_client.db)
    assert sync_client.write(utils.random_points(10))


def test_string_write(sync_client):
    point = 'cpu_load_short,host=server02,region=us-west value=0.55 1422568543702900257'
    assert sync_client.write(point)


def test_tagless_write(sync_client):
    point = b'cpu_load_short value=0.55 1423568543000000000'
    assert sync_client.write(point)


def test_special_values_write(sync_client):
    point = utils.random_point()
    point['tags']['boolean_tag'] = True
    point['tags']['none_tag'] = None
    point['tags']['blank_tag'] = ''
    point['fields']['boolean_field'] = False
    point['fields']['none_field'] = None
    point['fields']['backslash'] = "This is a backslash: \\"
    point['measurement'] = '"quo⚡️es and emoji"'
    with pytest.warns(UserWarning) as e:
        assert sync_client.write(point)
    logger.warning(e)


def test_simple_query(sync_client):
    resp = sync_client.select_all(measurement='test_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 10


def test_drop_measurement(sync_client):
    sync_client.drop_measurement(measurement='test_measurement')


def test_write_with_custom_measurement(sync_client):
    points = [p for p in utils.random_points(5)]
    for p in points:
        _ = p.pop('measurement')
    logger.info(points)
    with pytest.raises(ValueError):
        assert sync_client.write(points)
    assert sync_client.write(points, measurement='another_measurement')
    resp = sync_client.select_all(measurement='another_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 5


def test_write_without_tags(sync_client):
    points = [p for p in utils.random_points(7)]
    for p in points:
        _ = p.pop('tags')
    logger.info(points)
    assert sync_client.write(points, mytag='foo')
    resp = sync_client.select_all(measurement='test_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 7


def test_write_without_timestamp(sync_client):
    points = [p for p in utils.random_points(9)]
    for p in points:
        _ = p.pop('time')
        _ = p.pop('measurement')
    logger.info(points)
    assert sync_client.write(points, measurement='yet_another_measurement')
    resp = sync_client.select_all(measurement='yet_another_measurement')
    # Points with the same tag/timestamp set are overwritten
    assert len(resp['results'][0]['series'][0]['values']) == 1


def test_write_non_string_identifier_and_tags(sync_client):
    point = dict(tags={1: 2},
                 fields={3: 4})
    with pytest.warns(UserWarning):
        assert sync_client.write(point, measurement='my_measurement')
    resp = sync_client.select_all(measurement='my_measurement')
    logger.info(resp)
    assert len(resp['results'][0]['series'][0]['values']) == 1


def test_write_to_non_default_db(sync_client):
    points = [p for p in utils.random_points(5)]
    sync_client.create_database(db='temp_db')
    assert sync_client.db != 'temp_db'
    assert sync_client.write(points, db='temp_db')
    resp = sync_client.select_all(db='temp_db', measurement='test_measurement')
    logger.info(resp)
    assert len(resp['results'][0]['series'][0]['values']) == 5
    sync_client.drop_database(db='temp_db')


def test_write_to_non_default_rp(sync_client):
    db = sync_client.db
    sync_client.query(f"CREATE RETENTION POLICY myrp ON {db} DURATION 1h REPLICATION 1")
    points = [p for p in utils.random_points(5)]
    assert sync_client.write(points, rp='myrp')
    resp = sync_client.query(f"SELECT * from {db}.myrp.test_measurement")
    logger.info(resp)
    assert len(resp['results'][0]['series'][0]['values']) == 5


def test_repr(sync_client):
    logger.info(sync_client)


def test_query_pattern_keyword(sync_client):
    assert sync_client.select_all("order")


###############
# Error tests #
###############

def test_invalid_data_write(sync_client):
    with pytest.raises(InfluxDBWriteError) as e:
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


def test_invalid_client_mode():
    with pytest.raises(ValueError) as e:
        _ = InfluxDBClient(db='mytestdb', mode=utils.random_string())
    logger.error(e)


def test_no_default_database_warning():
    with pytest.warns(UserWarning) as e:
        _ = InfluxDBClient(db=None)
    logger.error(e)


def test_invalid_output_format(sync_client):
    with pytest.raises(ValueError) as e:
        sync_client.output = utils.random_string()
    logger.error(e)
    if pd is None:
        with pytest.raises(ValueError) as e:
            sync_client.output = 'dataframe'
        logger.error(e)


def test_invalid_query(sync_client):
    with pytest.raises(InfluxDBError) as e:
        sync_client.query('NOT A VALID QUERY')
    logger.error(e)


def test_invalid_query_pattern(sync_client):
    with pytest.warns(UserWarning) as e:
        sync_client.set_query_pattern('my_query', 'SELECT {q} from {epoch}')
    logger.warning(e)


def test_invalid_query_pattern_name(sync_client):
    with pytest.warns(UserWarning) as e:
        sync_client.set_query_pattern(r'wr\ite', 'SELECT {foo} from {bar}')
    logger.warning(e)


def test_missing_kwargs(sync_client):
    with pytest.raises(ValueError) as e:
        sync_client.select_all()
    logger.error(e)


def test_statement_error(sync_client):
    with pytest.raises(InfluxDBError) as e:
        sync_client.query('SELECT * FROM my_measurement', db='fake_db')
    logger.error(e)
