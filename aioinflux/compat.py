import warnings

no_pandas_warning = "Pandas/Numpy is not available. Support for 'dataframe' mode is disabled."
no_redis_warning = "Redis is not available. Support for caching functionality is disabled."

try:
    import pandas as pd
    import numpy as np
except ModuleNotFoundError:
    pd = None
    np = None
    warnings.warn(no_pandas_warning)

try:
    import aioredis
    import lz4.block as lz4
except ModuleNotFoundError:
    aioredis = None
    lz4 = None

__all__ = ['no_pandas_warning', 'no_redis_warning', 'pd', 'np', 'aioredis', 'lz4']
