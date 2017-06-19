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


#### Dictionary data format

TODO


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
