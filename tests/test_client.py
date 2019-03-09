import pytest
from aioinflux import InfluxDBClient, InfluxDBError, InfluxDBWriteError, iterpoints
from aioinflux.compat import pd
import testing_utils as utils
from testing_utils import logger


def test_repr(client):
    logger.info(client)


@pytest.mark.asyncio
async def test_ping(client):
    r = await client.ping()
    assert 'X-Influxdb-Version' in r


#########
# Write #
#########

@pytest.mark.asyncio
async def test_write_simple(client):
    assert await client.write(utils.random_points(100))


@pytest.mark.asyncio
async def test_write_string(client):
    point = 'cpu_load_short,host=server02,region=us-west value=0.55 1422568543702900257'
    assert await client.write(point)


@pytest.mark.asyncio
async def test_write_tagless(client):
    point = b'cpu_load_short value=0.55 1423568543000000000'
    assert await client.write(point)


@pytest.mark.asyncio
async def test_write_special_values(client):
    point = utils.random_point()
    point['tags']['boolean_tag'] = True
    point['tags']['none_tag'] = None
    point['tags']['blank_tag'] = ''
    point['fields']['boolean_field'] = False
    point['fields']['none_field'] = None
    point['fields']['backslash'] = "This is a backslash: \\"
    point['measurement'] = '"quo⚡️es and emoji"'
    with pytest.warns(UserWarning) as e:
        assert await client.write(point)
    logger.warning(e)


@pytest.mark.asyncio
async def test_write_with_custom_measurement(client):
    points = [p for p in utils.random_points(5)]
    for p in points:
        _ = p.pop('measurement')
    logger.info(points)
    with pytest.raises(ValueError):
        assert await client.write(points)
    assert await client.write(points, measurement='another_measurement')
    resp = await client.query('SELECT * FROM another_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 5


@pytest.mark.asyncio
async def test_write_without_timestamp(client):
    points = [p for p in utils.random_points(9)]
    for p in points:
        _ = p.pop('time')
        _ = p.pop('measurement')
    logger.info(points)
    assert await client.write(points, measurement='yet_another_measurement')
    resp = await client.query('SELECT * FROM yet_another_measurement')
    # Points with the same tag/timestamp set are overwritten
    assert len(resp['results'][0]['series'][0]['values']) == 1


@pytest.mark.asyncio
async def test_write_non_string_identifier_and_tags(client):
    point = dict(tags={1: 2},
                 fields={3: 4})
    with pytest.warns(UserWarning):
        assert await client.write(point, measurement='my_measurement')
    resp = await client.query('SELECT * FROM my_measurement')
    logger.info(resp)
    assert len(resp['results'][0]['series'][0]['values']) == 1


@pytest.mark.asyncio
async def test_write_to_non_default_db(client):
    points = [p for p in utils.random_points(5)]
    await client.create_database(db='temp_db')
    assert client.db != 'temp_db'
    assert await client.write(points, db='temp_db')
    resp = await client.query('SELECT * FROM temp_db..test_measurement')
    logger.info(resp)
    assert len(resp['results'][0]['series'][0]['values']) == 5
    await client.drop_database(db='temp_db')


@pytest.mark.asyncio
async def test_write_to_non_default_rp(client):
    db = client.db
    await client.query(f"CREATE RETENTION POLICY myrp ON {db} DURATION 1h REPLICATION 1")
    points = [p for p in utils.random_points(5)]
    assert await client.write(points, rp='myrp')
    resp = await client.query(f"SELECT * from {db}.myrp.test_measurement")
    logger.info(resp)
    assert len(resp['results'][0]['series'][0]['values']) == 5


#########
# Query #
#########

@pytest.mark.asyncio
async def test_simple_query(client):
    resp = await client.query('SELECT * FROM test_measurement')
    assert len(resp['results'][0]['series'][0]['values']) == 100


@pytest.mark.asyncio
async def test_chunked_query(client):
    resp = await client.query('SELECT * FROM test_measurement',
                              chunked=True, chunk_size=10)
    points = []
    async for chunk in resp:
        for point in iterpoints(chunk):
            points.append(point)
    assert len(points) == 100


@pytest.mark.asyncio
async def test_empty_chunked_query(client):
    resp = await client.query('SELECT * FROM fake', chunked=True, chunk_size=10)
    points = []
    async for chunk in resp:
        for point in iterpoints(chunk):
            points.append(point)
    assert len(points) == 0


####################
# Built-in queries #
####################


@pytest.mark.asyncio
async def test_create_database(client):
    resp = await client.create_database(db='mytestdb')
    assert resp


@pytest.mark.asyncio
async def test_drop_database(client):
    resp = await client.drop_database(db='mytestdb')
    assert resp


@pytest.mark.asyncio
async def test_drop_measurement(client):
    measurement = utils.random_string()
    assert await client.write(f'{measurement} foo=1')
    await client.drop_measurement(measurement=measurement)


@pytest.mark.asyncio
async def test_show_databases(client):
    r = await client.show_databases()
    assert r
    logger.debug(r)


@pytest.mark.asyncio
async def test_show_measurements(client):
    r = await client.show_measurements()
    assert r
    logger.debug(r)


@pytest.mark.asyncio
async def test_show_users(client):
    r = await client.show_users()
    assert r
    logger.debug(r)


@pytest.mark.asyncio
async def test_show_series(client):
    r = await client.show_series()
    assert r
    logger.debug(r)
    r = await client.show_series('cpu_load_short')
    assert r
    logger.debug(r)


@pytest.mark.asyncio
async def test_show_retention_policies(client):
    r = await client.show_retention_policies()
    assert r
    logger.debug(r)


@pytest.mark.asyncio
async def test_show_tag_keys(client):
    r = await client.show_tag_keys()
    assert r
    logger.debug(r)
    r = await client.show_tag_keys('cpu_load_short')
    assert r
    logger.debug(r)


@pytest.mark.asyncio
async def test_show_field_keys(client):
    r = await client.show_field_keys()
    assert r
    logger.debug(r)
    r = await client.show_field_keys('cpu_load_short')
    assert r
    logger.debug(r)


@pytest.mark.asyncio
async def test_show_tag_values(client):
    r = await client.show_tag_values('host')
    assert r
    logger.debug(r)
    r = await client.show_tag_values('host', 'cpu_load_short')
    assert r
    logger.debug(r)


@pytest.mark.asyncio
async def test_show_continuous_queries(client):
    r = await client.show_continuous_queries()
    assert r
    logger.debug(r)


###############
# Error tests #
###############

@pytest.mark.asyncio
async def test_chunked_query_error(client):
    with pytest.raises(InfluxDBError) as e:
        resp = await client.query('INVALID QUERY', chunked=True, chunk_size=10)
        _ = [i async for i in resp]
    logger.error(e)


@pytest.mark.asyncio
async def test_invalid_data_write(client):
    with pytest.raises(InfluxDBWriteError) as e:
        # Plain invalid data
        await client.write(utils.random_string())
    logger.error(e)

    with pytest.raises(ValueError) as e:
        # Pass function as input data
        await client.write(utils.random_string)
    logger.error(e)

    with pytest.raises(ValueError) as e:
        # Measurement missing
        point = utils.random_point()
        point.pop('measurement')
        await client.write(point)
    logger.error(e)


def test_invalid_client_mode():
    with pytest.raises(ValueError) as e:
        _ = InfluxDBClient(db='mytestdb', mode=utils.random_string())
    logger.error(e)


def test_no_default_database_warning():
    with pytest.warns(UserWarning) as e:
        _ = InfluxDBClient(db=None)
    logger.error(e)


def test_invalid_output_format(client):
    with pytest.raises(ValueError) as e:
        client.output = utils.random_string()
    logger.error(e)
    if pd is None:
        with pytest.raises(ValueError) as e:
            client.output = 'dataframe'
        logger.error(e)


@pytest.mark.asyncio
async def test_invalid_query(client):
    with pytest.raises(InfluxDBError) as e:
        await client.query('NOT A VALID QUERY')
    logger.error(e)


@pytest.mark.asyncio
async def test_statement_error(client):
    with pytest.raises(InfluxDBError) as e:
        await client.query('SELECT * FROM my_measurement', db='fake_db')
    logger.error(e)
