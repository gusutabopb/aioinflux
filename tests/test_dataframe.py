import pytest
import testing_utils as utils
from testing_utils import logger
from aioinflux.compat import pd, np

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
def test_write_dataframe_with_nan(df_client):
    df = utils.trading_df()
    df_client.write(df, f'fills00')
    for i in range(10):
        for _ in range(int(len(df) / 5)):
            i = np.random.randint(df.shape[0])
            j = np.random.randint(df.shape[1])
            df.iloc[i, j] = np.nan
        df_client.write(df, f'fills{i + 1:02d}')


@utils.requires_pandas
def test_select_into(df_client):
    df_client.query("SELECT * INTO m2_copy from m2")
    df = df_client.query('SELECT * from m2_copy')
    assert df.shape == (50, 8)
    logger.info(f'\n{df.head()}')


@utils.requires_pandas
def test_read_dataframe(df_client):
    df = df_client.query('SELECT * from m1')
    logger.info(f'\n{df.head()}')
    assert df.shape == (50, 8)


@utils.requires_pandas
@pytest.mark.asyncio
async def test_dataframe_chunked_query(client):
    client.output = 'dataframe'

    df1 = utils.random_dataframe()
    await client.write(df1, measurement='m3')

    cursor = await client.query('SELECT * FROM m3', chunked=True, chunk_size=10)
    dfs = []
    async for subdf in cursor:
        assert isinstance(subdf, pd.DataFrame)
        assert len(subdf) == 10
        dfs.append(subdf)
    df = pd.concat(dfs)
    assert df.shape == (50, 7)

    client.output = 'json'


@utils.requires_pandas
def test_read_dataframe_groupby(df_client):
    df_dict = df_client.query('SELECT max(*) from /m[1-2]$/ GROUP BY "tag"')
    s = ['\n{}:\n{}'.format(k, v) for k, v in df_dict.items()]
    logger.info('\n'.join(s))
    m1 = pd.concat([df for k, df in df_dict.items() if k.split(',')[0] == 'm1'])
    m2 = pd.concat([df for k, df in df_dict.items() if k.split(',')[0] == 'm2'])
    assert m1.shape == (5, 6)
    assert m2.shape == (5, 6)


@utils.requires_pandas
def test_read_dataframe_multistatement(df_client):
    df_list = df_client.query('SELECT max(*) from m1;SELECT min(*) from m2')
    logger.info(df_list)
    assert type(df_list) is list
    assert 'm1' in df_list[0]
    assert 'm2' in df_list[1]
    assert df_list[0]['m1'].shape == (1, 5)
    assert df_list[1]['m2'].shape == (1, 5)


@utils.requires_pandas
def test_read_dataframe_show_databases(df_client):
    df = df_client.show_databases()
    assert isinstance(df.index, pd.RangeIndex)
    assert 'name' in df.columns
    logger.info(f'\n{df.head()}')


@utils.requires_pandas
@pytest.mark.asyncio
async def test_change_db(client):
    state = client.db, client.output
    client.output = 'dataframe'

    client.db = 'foo'
    await client.ping()

    client.db, client.output = state


###############
# Error tests #
###############

@utils.requires_pandas
@pytest.mark.asyncio
async def test_invalid_data_write_dataframe(client):
    with pytest.raises(ValueError) as e:
        # Non-DatetimeIndex DataFrame
        await client.write(utils.random_dataframe().reset_index(), measurement='foo')
    logger.error(e)

    with pytest.raises(ValueError) as e:
        # DataFrame write without specifying measurement
        await client.write(utils.random_dataframe())
    logger.error(e)


@utils.requires_pandas
def test_chunked_dataframe(df_client):
    with pytest.raises(ValueError) as e:
        _ = df_client.query('SELECT * FROM foo', chunked=True)
    logger.error(e)
