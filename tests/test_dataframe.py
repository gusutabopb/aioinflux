import aioinflux.testing_utils as utils
from aioinflux.client import logger


def test_write_dataframe(df_client):
    df1 = utils.random_dataframe()
    df2 = utils.random_dataframe()
    df2.columns = df1.columns
    assert df_client.write(df1, measurement='m1', mytag='foo', tag_columns=['tag'])
    assert df_client.write(df2, measurement='m2', mytag='foo', tag_columns=['tag'])
    assert df_client.write(utils.random_dataframe(), measurement='m3')  # tag-less


def test_select_into(df_client):
    df_client.query("SELECT * INTO m2_copy from m2")
    df = df_client.select_all(measurement='min_m2')
    logger.debug(df)


def test_read_dataframe(df_client):
    df = df_client.select_all(measurement='m1')
    logger.debug(df.head())
    assert df.shape == (50, 7)


def test_read_dataframe_groupby(df_client):
    df_dict = df_client.query('SELECT max(*) from /m[1-2]/ GROUP BY "tag"')
    logger.debug(df_dict)
    assert df_dict['m1'].shape == (5, 6)
    assert df_dict['m2'].shape == (5, 6)
