import warnings

no_pandas_warning = "Pandas/Numpy is not available. Support for 'dataframe' mode is disabled."

try:
    import pandas as pd
    import numpy as np
except ModuleNotFoundError:
    pd = None
    np = None
    warnings.warn(no_pandas_warning)
