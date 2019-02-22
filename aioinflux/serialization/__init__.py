# flake8: noqa 402
from ..compat import pd

if pd:
    from . import dataframe
from . import mapping


def serialize(data, measurement=None, tag_columns=None, **extra_tags):
    """Converts input data into line protocol format"""
    if isinstance(data, bytes):
        return data
    elif isinstance(data, str):
        return data.encode('utf-8')
    elif hasattr(data, 'to_lineprotocol'):
        return data.to_lineprotocol()
    elif pd is not None and isinstance(data, pd.DataFrame):
        return dataframe.serialize(data, measurement, tag_columns, **extra_tags)
    elif isinstance(data, dict):
        return mapping.serialize(data, measurement, **extra_tags)
    elif hasattr(data, '__iter__'):
        return b'\n'.join([serialize(i, measurement, tag_columns, **extra_tags) for i in data])
    else:
        raise ValueError('Invalid input', data)
