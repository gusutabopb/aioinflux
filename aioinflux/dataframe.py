import pandas as pd
from .line_protocol import make_line


def make_df(resp):
    """Makes list of DataFrames from a response object"""

    def maker(series):
        df = pd.DataFrame(series['values'], columns=series['columns'])
        df = df.set_index(pd.to_datetime(df['time'])).drop('time', axis=1)
        df.index = df.index.tz_localize('UTC')
        df.index.name = None
        if 'name' in series:
            df.name = series['name']
        return df

    return [(series['name'], maker(series))
            for statement in resp['results']
            for series in statement['series']]


def parse_df(df, measurement, tag_columns=None):

    # Calling t._asdict is more straightforward
    # but about 40% slower than using indexes
    def parser(df):
        for t in df.itertuples():
            tags = dict()
            fields = dict()
            for i, k in enumerate(t._fields[1:]):
                if i + 1 in tag_indexes:
                    tags[k] = t[i + 1]
                else:
                    fields[k] = t[i + 1]
            yield dict(measurement=measurement,
                       time=t[0],
                       tags=tags,
                       fields=fields)

    # TODO: check datatime index
    # TODO: check/stringify object dtypes, issue warnings

    tag_indexes = [list(df.columns).index(tag) + 1 for tag in tag_columns]
    lines = [make_line(p) for p in parser(df)]
    return b'\n'.join(lines)
