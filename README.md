# aioinflux

Asynchronous Python client for InfluxDB. 
Built on top of [`aiohttp`](https://github.com/aio-libs/aiohttp) and 
[`asyncio`](https://docs.python.org/3/library/asyncio.html).

InfluxDB is an open-source distributed time series database.
Find more about InfluxDB at http://influxdata.com/


## Installation

Aioinflux is not yet listed on PyPI. Install directly from sources:

    # Latest stable version
    $ pip install git+https://github.com/plugaai/aioinflux
    
    # Latest development commit
    $ pip install git+https://github.com/plugaai/aioinflux@dev


### Dependencies

Aioinflux supports Python 3.6+ **ONLY**. For older Python versions please use the 
[official Python client](https://github.com/influxdata/influxdb-python) 

Third-party library dependencies are: [`aiohttp`](https://github.com/aio-libs/aiohttp) 
for all HTTP request handling and [`pandas`](https://github.com/pandas-dev/pandas) for 
`DataFrame` reading/writing support.


## Usage

### TL;DR:

This sums most of what you can do with `aioinflux`:

```python
import asyncio
from aioinflux import AsyncInfluxDBClient

point = dict(time='2009-11-10T23:00:00Z',
             measurement='cpu_load_short',
             tags={'host': 'server01',
                   'region': 'us-west'},
             fields={'value': 0.64})

client = AsyncInfluxDBClient(database='testdb')

coros = [client.create_database(db='testdb'),
         client.ping(),
         client.write(point),
         client.query('SELECT value FROM cpu_load_short')]
         
loop = asyncio.get_event_loop() 
results = loop.run_until_complete(asyncio.gather(*coros))
for result in results:
    print(result)
```

### Sync mode

Despite its name, `AsyncInfluxDBClient` can also run in sync/blocking mode:

```python
client = AsyncInfluxDBClient(database='testdb', async=False)
client.ping()
client.write(point)
client.query('SELECT value FROM cpu_load_short')
```

### Writing data

Input data can be:
1) A string properly formatted in InfluxDB's line protocol
2) A dictionary containing the following keys: `measurement`, `time`, `tags`, `fields`
3) A Pandas DataFrame with a DatetimeIndex
4) An iterable of one of the above

Input data in formats 2-4 are parsed into the 
[line protocol](https://docs.influxdata.com/influxdb/v1.2/write_protocols/line_protocol_reference/) 
before being written to InfluxDB. 
All parsing functionality is located at [`serialization.py`](aioinflux/serialization.py).
Beware that serialization is not highly optimized (PRs are welcome!) and may become a bottleneck depending 
on your application.


The `write` method returns `True` when successful and raises an `InfluxDBError` otherwise.  


#### Writting dictionary-like objects

Aioinflux accepts any dictionary-like object (mapping) as input. However, that dictionary must 
be properly formated and contain the following keys:

1) **`measurement`**: Optional. Must be a string-like object. If ommited, must be specified when 
  calling `AsyncInfluxDBClient.write` by passing a `measurement` argument.
1) **`time`**: Optional. The value can be `datetime.datetime`, date-like string 
  (e.g., `2017-01-01`, `2009-11-10T23:00:00Z`) or anything else that can be parsed by Pandas 
  [`Timestamp`](https://pandas.pydata.org/pandas-docs/stable/timeseries.html) class.
1) **`tags`**: Optional. This must contain another mapping of field names and values.
  Both tag keys and values should be strings.  
1) **`fields`**: Mandatory. This must contain another mapping of field names and values.
  Field keys should be strings. Field values can be `float`, `int`, `str`, or `bool` or any equivalent type. 

Any fields other then the above will be ignored when writing data to InfluxDB.


A typical dictionary-like point would look something like the following:

```python
{'time': '2009-11-10T23:00:00Z',
'measurement': 'cpu_load_short',
'tags': {'host': 'server01', 'region': 'us-west'},
'fields': {'value1': 0.64, 'value2': True, 'value3': 10}}
```


#### Writting DataFrames

Aioinflux also accepts Pandas dataframes as input. The only requirements for the dataframe is
that the **index must be of type `DatetimeIndex`**. Also, any column whose `dtype` is `object` will be 
converted to a string representation.

A typical DataFrame input should look something like the following:

```text
                                       LUY       BEM       AJW tag
2017-06-24 08:45:17.929097+00:00  2.545409  5.173134  5.532397   B
2017-06-24 10:15:17.929097+00:00 -0.306673 -1.132941 -2.130625   E
2017-06-24 11:45:17.929097+00:00  0.894738 -0.561979 -1.487940   B
2017-06-24 13:15:17.929097+00:00 -1.799512 -1.722805 -2.308823   D
2017-06-24 14:45:17.929097+00:00  0.390137 -0.016709 -0.667895   E
```

The measurement name must be specified with the `measurement` argument when calling `AsyncInfluxDBClient.write`.
Additional tags can also be passed using arbitrary keyword arguments. See `AsyncInfluxDBClient.write` docstring 
for details.


### Querying data

TODO


#### Retrieving DataFrames

TODO

#### Chunked responses

TODO

### Other functionality

#### Authentication

TODO

#### Database selection

TODO

#### Debugging

TODO


## Implementation

Since InfluxDB exposes all its functionality through an 
[HTTP API](https://docs.influxdata.com/influxdb/v1.2/tools/api/), 
`AsyncInfluxDBClient` tries to be nothing more than a thin and dry wrapper around that API.

The InfluxDB HTTP API exposes exactly three endpoints/functions: `ping`, `write` and `query`. 

`AsyncInfluxDBClient` merely wraps these three functions and provides some parsing functionality for generating 
line protocol data (when writing) and parsing JSON responses (when querying). 

Additionally, [partials](https://en.wikipedia.org/wiki/Partial_application) are used in order to provide 
convenient access to commonly used query patterns. See the full list [here](aioinflux/client.py#L177).


## Contributing

To contribute, fork the repository on GitHub, make your changes and submit a pull request.  
Aioinflux is not a mature project yet, so just simply raising issues is also greatly appreciated :)
