import warnings
from collections import defaultdict
from typing import Mapping, Union, Dict

from . import pd, np

if pd is None:
    import ciso8601

# Special characters documentation:
# https://docs.influxdata.com/influxdb/v1.4/write_protocols/line_protocol_reference/#special-characters
# Although not in the official docs, new line characters are removed in order to avoid issues.
key_escape = str.maketrans({',': r'\,', ' ': r'\ ', '=': r'\=', '\n': ''})
tag_escape = str.maketrans({',': r'\,', ' ': r'\ ', '=': r'\=', '\n': ''})
str_escape = str.maketrans({'"': r'\"', '\n': ''})
measurement_escape = str.maketrans({',': r'\,', ' ': r'\ ', '\n': ''})


def escape(string, escape_pattern):
    """Assistant function for string escaping"""
    try:
        return string.translate(escape_pattern)
    except AttributeError:
        warnings.warn("Non-string-like data passed. "
                      "Attempting to convert to 'str'.")
        return str(string).translate(tag_escape)


def parse_data(data, measurement=None, tag_columns=None, **extra_tags):
    """Converts input data into line protocol format"""
    if isinstance(data, bytes):
        return data
    elif isinstance(data, str):
        return data.encode('utf-8')
    elif pd is not None and isinstance(data, pd.DataFrame):
        if measurement is None:
            raise ValueError("Missing 'measurement'")
        return parse_df(data, measurement, tag_columns, **extra_tags)
    elif isinstance(data, dict):
        return make_line(data, measurement, **extra_tags)
    elif hasattr(data, '__iter__'):
        return b'\n'.join([parse_data(i, measurement, tag_columns, **extra_tags) for i in data])
    else:
        raise ValueError('Invalid input', data)


def make_line(point: Mapping, measurement=None, **extra_tags):
    """Converts dictionary-like data into a single line protocol line (point)"""
    p = dict(measurement=_parse_measurement(point, measurement),
             tags=_parse_tags(point, extra_tags),
             fields=_parse_fields(point),
             timestamp=_parse_timestamp(point))
    if p['tags']:
        line = '{measurement},{tags} {fields} {timestamp}'.format(**p)
    else:
        line = '{measurement} {fields} {timestamp}'.format(**p)
    return line.encode('utf-8')


def _parse_measurement(point, measurement):
    try:
        return escape(point['measurement'], measurement_escape)
    except KeyError:
        if measurement is None:
            raise ValueError("'measurement' missing")
        return escape(measurement, measurement_escape)


def _parse_tags(point, extra_tags):
    output = []
    try:
        for k, v in {**point['tags'], **extra_tags}.items():
            k = escape(k, key_escape)
            v = escape(v, tag_escape)
            if not v:
                continue  # ignore blank/null string tags
            output.append('{k}={v}'.format(k=k, v=v))
    except KeyError:
        pass
    if output:
        return ','.join(output)
    else:
        return ''


def _parse_timestamp(point):
    if 'time' not in point:
        return ''
    elif pd is not None:
        return pd.Timestamp(point['time']).value
    elif isinstance(point['time'], (str, bytes)):
        dt = ciso8601.parse_datetime(point['time'])
        return int(dt.timestamp()) * 10 ** 9 + dt.microsecond * 1000
    else:
        dt = point['time']
        return int(dt.timestamp()) * 10 ** 9 + dt.microsecond * 1000


def _parse_fields(point):
    """Field values can be floats, integers, strings, or Booleans."""
    output = []
    for k, v in point['fields'].items():
        k = escape(k, key_escape)
        if isinstance(v, bool):
            output.append('{k}={v}'.format(k=k, v=v))
        elif isinstance(v, int):
            output.append('{k}={v}i'.format(k=k, v=v))
        elif isinstance(v, str):
            output.append('{k}="{v}"'.format(k=k, v=v.translate(str_escape)))
        elif v is None or (np is not None and np.isnan(v)):
            # Empty values
            continue
        else:
            # Floats
            output.append('{k}={v}'.format(k=k, v=v))
    return ','.join(output)


DataFrameType = None if pd is None else Union[bool, pd.DataFrame, Dict[str, pd.DataFrame]]


def make_df(resp, tag_cache=None) -> DataFrameType:
    """Makes list of DataFrames from a response object"""
    def maker(series) -> pd.DataFrame:
        df = pd.DataFrame(series['values'], columns=series['columns'])
        if 'time' not in df.columns:
            return df
        df: pd.DataFrame = df.set_index(pd.to_datetime(df['time'])).drop('time', axis=1)
        df.index = df.index.tz_localize('UTC')
        df.index.name = None
        if 'tags' in series:
            for k, v in series['tags'].items():
                df[k] = v
        if 'name' in series:
            df.name = series['name']
        return df

    def drop_zero_index(df):
        if isinstance(df.index, pd.DatetimeIndex):
            if all(i.value == 0 for i in df.index):
                df.reset_index(drop=True, inplace=True)

    # Parsing
    df_list = [((series['name'], tuple(series.get('tags', {}).items())), maker(series))
               for statement in resp['results'] if 'series' in statement
               for series in statement['series']]

    # Concatenation
    d = defaultdict(list)
    for k, df in sorted(df_list, key=lambda x: x[0]):
        d[k].append(df)
    dfs = {k: pd.concat(v, axis=0) for k, v in d.items()}

    # Post-processing
    for (name, tags), df in dfs.items():
        drop_zero_index(df)
        df.name = name
        if not tag_cache or name not in tag_cache:
            continue
        for col, tags in tag_cache[name].items():
            if col not in df.columns:
                continue
            # Change tag columns dtype from object to categorical
            dtype = pd.api.types.CategoricalDtype(categories=tags)
            df[col] = df[col].astype(dtype=dtype)

    # Return
    if len(dfs) == 1:
        return dfs[list(dfs.keys())[0]]
    return dfs


def parse_df(df, measurement, tag_columns=None, **extra_tags):
    """Converts a Pandas DataFrame into line protocol format"""

    # Calling t._asdict is more straightforward
    # but about 40% slower than using indexes
    def parser(df):
        for t in df.itertuples():
            tags = dict()
            fields = dict()
            # noinspection PyProtectedMember
            for i, k in enumerate(t._fields):
                if i in tag_indexes:
                    tags[k] = t[i]
                elif i == 0:
                    continue
                else:
                    fields[k] = t[i]
            tags.update(extra_tags)
            yield dict(measurement=measurement,
                       time=t[0],
                       tags=tags,
                       fields=fields)

    # Make a copy because modifications are made to the dataframe before insertion
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError('DataFrame index is not DatetimeIndex')
    for key, value in extra_tags.items():
        df[key] = value
    if tag_columns:
        tag_indexes = [df.columns.get_loc(tag) + 1 for tag in tag_columns + list(extra_tags)]
    else:
        tag_indexes = list()
    lines = [make_line(p) for p in parser(df)]
    return b'\n'.join(lines)
