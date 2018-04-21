import pytest
from aioinflux import logger, pd, testing_utils as utils

if pd is not None:
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 100)


@utils.requires_pandas
def test_write_dataframe(df_client):
    df1 = utils.random_dataframe()
    df2 = utils.random_dataframe()
    df2.columns = df1.columns
    assert df_client.write(df1, measurement='m1', mytag='foo', tag_columns=['tag'])
    assert df_client.write(df2, measurement='m2', mytag='foo', tag_columns=['tag'])
    assert df_client.write(utils.random_dataframe(), measurement='m3')  # tag-less


@utils.requires_pandas
def test_select_into(df_client):
    df_client.query("SELECT * INTO m2_copy from m2")
    df = df_client.select_all(measurement='m2_copy')
    assert df.shape == (50, 8)
    logger.info(f'\n{df.head()}')


@utils.requires_pandas
def test_read_dataframe(df_client):
    df = df_client.select_all(measurement='m1')
    logger.info(f'\n{df.head()}')
    assert df.shape == (50, 8)


@utils.requires_pandas
def test_read_dataframe_groupby(df_client):
    df_dict = df_client.query('SELECT max(*) from /m[1-2]$/ GROUP BY "tag"')
    s = ['\n{}:\n{}'.format(k, v) for k, v in df_dict.items()]
    logger.info('\n'.join(s))
    m1 = pd.concat([df for k, df in df_dict.items() if k[0] == 'm1'])
    m2 = pd.concat([df for k, df in df_dict.items() if k[0] == 'm2'])
    assert m1.shape == (5, 6)
    assert m2.shape == (5, 6)


@utils.requires_pandas
def test_read_dataframe_with_tag_info(df_client):
    df_client.get_tag_info()
    logger.info(df_client.tag_cache)
    df = df_client.select_all(measurement='m1')
    assert pd.api.types.CategoricalDtype in {type(d) for d in df.dtypes}
    assert df.shape == (50, 8)


@utils.requires_pandas
def test_read_dataframe_show_databases(df_client):
    df = df_client.show_databases()
    assert isinstance(df.index, pd.RangeIndex)
    assert 'name' in df.columns
    logger.info(f'\n{df.head()}')


# noinspection PyUnresolvedReferences
@utils.requires_pandas
def test_mixed_args_kwargs_query_pattern(df_client):
    df1 = df_client.show_tag_values_from('m1', key='tag')
    df2 = df_client.show_tag_values_from('m1', 'tag')
    df3 = df_client.show_tag_values_from('tag', measurement='m1')
    assert (df1 == df2).all().all()
    assert (df1 == df3).all().all()
    assert (df2 == df3).all().all()


@utils.requires_pandas
@pytest.mark.asyncio
async def test_change_db(async_client):
    state = async_client.db, async_client.output
    async_client.output = 'dataframe'

    async_client.db = None
    async_client.db = 'foo'
    await async_client.ping()

    async_client.db, async_client.output = state


###############
# Error tests #
###############

@utils.requires_pandas
def test_invalid_data_write_dataframe(sync_client):
    with pytest.raises(ValueError) as e:
        # Non-DatetimeIndex DataFrame
        sync_client.write(utils.random_dataframe().reset_index(), measurement='foo')
    logger.error(e)

    with pytest.raises(ValueError) as e:
        # DataFrame write without specifying measurement
        sync_client.write(utils.random_dataframe())
    logger.error(e)


@utils.requires_pandas
def test_chunked_dataframe(df_client):
    with pytest.raises(ValueError) as e:
        _ = df_client.select_all('foo', chunked=True)
    logger.error(e)


@utils.requires_pandas
@pytest.mark.asyncio
async def test_async_chunked_dataframe(df_client):
    df_client.mode = 'async'
    with pytest.raises(ValueError) as e:
        _ = await df_client.select_all('foo', chunked=True)
    logger.error(e)
    df_client.mode = 'blocking'
