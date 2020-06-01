User Guide
==========

.. contents::
   :local:

TL;DR
-----

This sums most of what you can do with :mod:`aioinflux`:

.. code:: python

    import asyncio
    from aioinflux import InfluxDBClient

    point = {
        'time': '2009-11-10T23:00:00Z',
        'measurement': 'cpu_load_short',
        'tags': {'host': 'server01',
                 'region': 'us-west'},
        'fields': {'value': 0.64}
    }

    async def main():
        async with InfluxDBClient(db='testdb') as client:
           await client.create_database(db='testdb')
           await client.write(point)
           resp = await client.query('SELECT value FROM cpu_load_short')
           print(resp)


    asyncio.get_event_loop().run_until_complete(main())

Client modes
------------

Despite the library's name, |client| can also run in non-async
mode (a.k.a ``blocking``) mode. It can be useful for debugging and exploratory
data analysis.

The running mode for can be switched on-the-fly by changing the ``mode`` attribute:

.. code:: python

    client = InfluxDBClient(mode='blocking')
    client.mode = 'async'

The ``blocking`` mode is implemented through a decorator that automatically runs coroutines on
the event loop as soon as they are generated.
Usage is almost the same as in the ``async`` mode, but without the need of using ``await`` and
being able to run from outside of a coroutine function:

.. code:: python

    client = InfluxDBClient(db='testdb', mode='blocking')
    client.ping()
    client.write(point)
    client.query('SELECT value FROM cpu_load_short')

.. note::

    The need for the ``blocking`` mode has been somewhat supplanted
    by the new async REPL available with the release of IPython 7.0.
    See `this blog post <https://blog.jupyter.org/ipython-7-0-async-repl-a35ce050f7f7>`__ for details.

    If you are having issues running ``blocking`` mode with recent Python/IPython versions,
    see `this issue <https://github.com/gusutabopb/aioinflux/issues/17>`__ for other possible workarounds.

Writing data
------------

To write data to InfluxDB, use |client|'s
|write| method.
Successful writes will return ``True``. In case some error occurs :class:`~aioinflux.client.InfluxDBWriteError`
exception will be raised.

Input data to |write| can be:

1. A mapping (e.g. ``dict``) containing the keys: ``measurement``, ``time``, ``tags``, ``fields``
2. A :class:`pandas.DataFrame` with a |datetimeindex|
3. A user defined class decorated w/ |lineprotocol|
   (**recommended**, see :ref:`below <Writing user-defined class objects>`)
4. A string (``str`` or ``bytes``) properly formatted in InfluxDB's line protocol
5. An iterable of one of the above

Input data in formats 1-3 are serialized into the `line protocol`_ before being written to InfluxDB.
``str`` or ``bytes`` are assumed to already be in line protocol format and are inserted into InfluxDB as they are.
All functionality regarding JSON parsing (InfluxDB's only output format) and serialization to line protocol
(InfluxDB's only input format) is located in the :mod:`~aioinflux.serialization` subpackage.

Beware that serialization is not highly optimized (C extensions / cythonization PRs are welcome!) and may become
a bottleneck depending on your application's performance requirements.
It is, however, reasonably (3-10x) `faster`_ than InfluxDB's `official Python client`_.

.. _`official Python client`: https://github.com/influxdata/influxdb-python
.. _`line protocol`: https://docs.influxdata.com/influxdb/latest/write_protocols/line_protocol_reference/
.. _`faster`: https://gist.github.com/gusutabopb/42550f0f07628ba61b0ed6322f02855b

Writing dictionary-like objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::

    This is the same format as the one used by InfluxDB's `official Python client`_ and is implemented
    in Aioinflux for compatibility purposes only.
    Using dictionaries to write data to InfluxDB is slower and more error-prone than the other methods
    provided by Aioinflux and therefore **discouraged**.

Aioinflux accepts any dictionary-like object (mapping) as input.
The dictionary must contain the following keys:

1) **measurement**: Optional. Must be a string-like object. If
   omitted, must be specified when calling |write|
   by passing a ``measurement`` argument.
2) **time**: Optional. The value can be |datetime|,
   date-like string (e.g., ``2017-01-01``, ``2009-11-10T23:00:00Z``) or
   anything else that can be parsed by :class:`pandas.Timestamp`.
   See :ref:`Pandas documentation <pandas:timeseries>` for details.
   If Pandas is not available, |ciso8601|_ is used instead for date-like string parsing.
3) **tags**: Optional. This must contain another mapping of field
   names and values. Both tag keys and values should be strings.
4) **fields**: Mandatory. This must contain another mapping of field
   names and values. Field keys should be strings. Field values can be
   ``float``, ``int``, ``str``, ``bool`` or ``None`` or any its subclasses.
   Attempting to use Numpy types will cause errors as ``np.int64``, ``np.float64``, etc are not
   subclasses of Python's built-in numeric types.
   Use dataframes for writing data using Numpy types.

.. |ciso8601| replace:: ``ciso8601``
.. _ciso8601: https://github.com/closeio/ciso8601/

Any keys other then the above will be ignored when writing data to
InfluxDB.

A typical dictionary-like point would look something like the following:

.. code:: python

    {'time': '2009-11-10T23:00:00Z',
    'measurement': 'cpu_load_short',
    'tags': {'host': 'server01', 'region': 'us-west'},
    'fields': {'value1': 0.64, 'value2': True, 'value3': 10}}

.. note:: **Timestamps and timezones**

   Working with timezones in computing tends to be quite messy.
   To avoid such problems, the `broadly agreed`_ upon idea is to store
   timestamps in UTC. This is how both InfluxDB and Pandas treat timestamps internally.

   Pandas and many other libraries also assume all input timestamps are in UTC unless otherwise
   explicitly noted. Aioinflux does the same and assumes any timezone-unaware |datetime| object
   or datetime-like strings is in UTC.
   Aioinflux does not raise any warnings when timezone-unaware input is passed
   and silently assumes it to be in UTC.

.. _`broadly agreed`: http://lucumr.pocoo.org/2011/7/15/eppur-si-muove/

Writing DataFrames
^^^^^^^^^^^^^^^^^^

Aioinflux also accepts Pandas dataframes as input. The only requirements
for the dataframe is that the index **must** be of type
|datetimeindex|. Also, any column whose ``dtype`` is ``object`` will
be converted to a string representation.

A typical dataframe input should look something like the following:

.. code:: text

                                           LUY       BEM       AJW tag
    2017-06-24 08:45:17.929097+00:00  2.545409  5.173134  5.532397   B
    2017-06-24 10:15:17.929097+00:00 -0.306673 -1.132941 -2.130625   E
    2017-06-24 11:45:17.929097+00:00  0.894738 -0.561979 -1.487940   B
    2017-06-24 13:15:17.929097+00:00 -1.799512 -1.722805 -2.308823   D
    2017-06-24 14:45:17.929097+00:00  0.390137 -0.016709 -0.667895   E

The measurement name must be specified with the ``measurement`` argument
when calling |write|.
Columns that should be treated as tags must be specified by passing a sequence as the ``tag_columns`` argument.
Additional tags (not present in the actual dataframe) can also be passed using arbitrary keyword arguments.

**Example:**

.. code:: python

    client = InfluxDBClient(db='testdb', mode='blocking')
    client.write(df, measurement='prices', tag_columns=['tag'], asset_class='equities')

In the example above, ``df`` is the dataframe we are trying to write to
InfluxDB and ``measurement`` is the measurement we are writing to.

``tag_columns`` is in an optional iterable telling which of the
dataframe columns should be parsed as tag values. If ``tag_columns`` is
not explicitly passed, all columns in the dataframe whose dtype is not
|datetimeindex| will be treated as InfluxDB field values.

Any other keyword arguments passed to |write| are
treated as extra tags which will be attached to the data being written
to InfluxDB. Any string which is a valid `InfluxDB identifier`_ and
valid `Python identifier`_ can be used as an extra tag key (with the
exception of the strings ``data``, ``measurement`` and ``tag_columns``).

See :ref:`API reference <client interface>` for details.

.. _`InfluxDB identifier`: https://docs.influxdata.com/influxdb/latest/query_language/spec/#identifiers
.. _`Python identifier`: https://docs.python.org/3/reference/lexical_analysis.html#identifiers


Writing user-defined class objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionchanged:: 0.5.0

Aioinflux can add write any arbitrary user-defined class to InfluxDB through the use of the
|lineprotocol| decorator. This decorator monkey-patches an
existing class and adds a ``to_lineprotocol`` method, which is used internally by Aioinflux to serialize
the class data into a InfluxDB-compatible format. In order to generate ``to_lineprotocol``, a typed schema
must be defined using `type hints`_ in the form of type annotations or a schema dictionary.

This is the fastest and least error-prone method of writing data into InfluxDB provided by Aioinflux.

.. _`type hints`: https://docs.python.org/3/library/typing.html

We recommend using |lineprotocol| with :py:class:`~typing.NamedTuple`:


.. code:: python

   from aioinflux import *
   from typing import NamedTuple

   @lineprotocol
   class Trade(NamedTuple):
       timestamp: TIMEINT
       instrument: TAGENUM
       source: TAG
       side: TAG
       price: FLOAT
       size: INT
       trade_id: STR


Alternatively, the functional form of :py:func:`~collections.namedtuple` can also be used:

.. code:: python

    from collections import namedtuple

    schema = dict(
       timestamp=TIMEINT,
       instrument=TAG,
       source=TAG,
       side=TAG,
       price=FLOAT,
       size=INT,
       trade_id=STR,
    )

    # Create class
    Trade = namedtuple('Trade', schema.keys())

    # Monkey-patch existing class and add ``to_lineprotocol``
    Trade = lineprotocol(Trade, schema=schema)


Dataclasses (or any other user-defined class) can be used as well:

.. code:: python

   from dataclasses import dataclass

   @lineprotocol
   @dataclass
   class Trade:
       timestamp: TIMEINT
       instrument: TAGENUM
       source: TAG
       side: TAG
       price: FLOAT
       size: INT
       trade_id: STR

If you want to preserve type annotations for another use,
you can pass your serialization schema as a dictionary as well:

.. code:: python

   @lineprotocol(schema=dict(timestamp=TIMEINT, value=FLOAT))
   @dataclass
   class MyTypedClass:
       timestamp: int
       value: float

    print(MyTypedClass.__annotations__)
    # {'timestamp': <class 'int'>, 'value': <class 'float'>}

    MyTypedClass(1547710904202826000, 2.1).to_lineprotocol()
    # b'MyTypedClass value=2.1 1547710904202826000'


The modified class will have a dynamically generated ``to_lineprotocol`` method which
generates a line protocol representation of the data contained by the object:

.. code:: python

   trade = Trade(
      timestamp=1540184368785116000,
      instrument='AAPL',
      source='NASDAQ',
      side='BUY',
      price=219.23,
      size=100,
      trade_id='34a1e085-3122-429c-9662-7ce82039d287'
   )

   trade.to_lineprotocol()
   # b'Trade,instrument=AAPL,source=NASDAQ,side=BUY price=219.23,size=100i,trade_id="34a1e085-3122-429c-9662-7ce82039d287" 1540184368785116000'

Calling ``to_lineprotocol`` by the end-user is not necessary but may be useful for debugging.

``to_lineprotocol`` is automatically used by |write| when present.

.. code:: python

   client = InfluxDBClient()
   await client.write(trade)  # True


User-defined class schema/type annotations
""""""""""""""""""""""""""""""""""""""""""

In Aioinflux, InfluxDB types (and derived types) are represented by :py:class:`~typing.TypeVar`
defined in :mod:`aioinflux.serialization.usertype` module.
All schema types (type annotations) **must** be one of those types.
The types available are based on the native types of InfluxDB
(see the `InfluxDB docs <https://docs.influxdata.com/influxdb/v1.6/write_protocols/line_protocol_reference/#data-types>`__ for
details), with some extra types to help the serialization to line protocol and/or allow more flexible usage
(such as the use of :py:class:`~enum.Enum` objects).


.. list-table::
   :header-rows: 1
   :widths: 10 30
   :align: center

   * - Type
     - Description
   * - ``MEASUREMENT``
     - Optional. If missing, the measurement becomes the class name
   * - ``TIMEINT``
     - Timestamp is a nanosecond UNIX timestamp
   * - ``TIMESTR``
     - Timestamp is a datetime string (somewhat compliant to ISO 8601)
   * - ``TIMEDT``
     - Timestamp is a |datetime| (or subclasses such as :class:`pandas.Timestamp`)
   * - ``TAG``
     - Treats field as an InfluxDB tag
   * - ``TAGENUM``
     - Same as ``TAG`` but allows the use of :py:class:`~enum.Enum`
   * - ``BOOL``
     - Boolean field
   * - ``INT``
     - Integer field
   * - ``FLOAT``
     - Float field
   * - ``STR``
     - String field
   * - ``ENUM``
     - Same as ``STR`` but allows the use of :py:class:`~enum.Enum`

``TAG*`` types are optional. One and only one ``TIME*`` type must present. At least ONE field type be present.


``@lineprotocol`` options
"""""""""""""""""""""""""

The |lineprotocol| function/decorator provides some options to
customize how object serialization is performed.
See the :ref:`API reference <user-defined classes>` for details.

Performance
"""""""""""

Serialization using |lineprotocol| is about 3x faster
than dictionary-like objects (or about 10x faster than the `official Python client`_).
See this `notebook <https://github.com/gusutabopb/aioinflux/tree/master/notebooks/datapoint_benchmark.ipynb>`__
for a simple benchmark.

Beware that setting ``rm_none=True`` can have substantial performance impact especially when
the number of fields/tags is very large (20+).


Querying data
-------------

Querying data is as simple as passing an InfluxDB query string to |query|:

.. code:: python

    await client.query('SELECT myfield FROM mymeasurement')

By default, this returns JSON data:

.. code:: python

    {'results': [{'series': [{'columns': ['time', 'Price', 'Volume'],
         'name': 'mymeasurement',
         'values': [[1491963424224703000, 5783, 100],
          [1491963424375146000, 5783, 200],
          [1491963428374895000, 5783, 100],
          [1491963429645478000, 5783, 1100],
          [1491963429655289000, 5783, 100],
          [1491963437084443000, 5783, 100],
          [1491963442274656000, 5783, 900],
          [1491963442274657000, 5782, 5500],
          [1491963442274658000, 5781, 3200],
          [1491963442314710000, 5782, 100]]}],
       'statement_id': 0}]}

See `InfluxDB official docs <https://docs.influxdata.com/influxdb/latest/guides/querying_data/#querying-data-using-the-http-api>`_
for more on the InfluxDB's HTTP API specifics.

Output formats
^^^^^^^^^^^^^^

When using, |query| data can return data in one of the following formats:

1) ``json``: Default. Returns a dictionary representation of the JSON response received from InfluxDB.
2) ``dataframe``: Parses the result into a Pandas dataframe(s).
   See :ref:`Retrieving DataFrames` for details.


The output format for can be switched on-the-fly by changing the ``output`` attribute:

.. code:: python

    client = InfluxDBClient(output='dataframe')
    client.mode = 'json'

Beware that when passing ``chunked=True``, the result type will be an async generator.
See :ref:`Chunked responses` for details.


Retrieving DataFrames
^^^^^^^^^^^^^^^^^^^^^

When the client is in ``dataframe`` mode, |query|
will usually return a :class:`pandas.DataFrame`:


.. code:: text

                                      Price  Volume
    2017-04-12 02:17:04.224703+00:00   5783     100
    2017-04-12 02:17:04.375146+00:00   5783     200
    2017-04-12 02:17:08.374895+00:00   5783     100
    2017-04-12 02:17:09.645478+00:00   5783    1100
    2017-04-12 02:17:09.655289+00:00   5783     100
    2017-04-12 02:17:17.084443+00:00   5783     100
    2017-04-12 02:17:22.274656+00:00   5783     900
    2017-04-12 02:17:22.274657+00:00   5782    5500
    2017-04-12 02:17:22.274658+00:00   5781    3200
    2017-04-12 02:17:22.314710+00:00   5782     100

.. note::

   On multi-statement queries and/or statements that return multiple InfluxDB series
   (such as a ``GROUP by "tag"`` query), a list of dictionaries of dataframes will be returned.
   Aioinflux generates a dataframe for each series contained in the JSON returned by InfluxDB.
   See this `Github issue <https://github.com/gusutabopb/aioinflux/issues/19>`__ for further discussion.



When generating dataframes, InfluxDB types are mapped to the following Numpy/Pandas dtypes:

.. list-table::
   :header-rows: 1
   :align: center

   * - InfluxDB type
     - Dataframe column ``dtype``
   * - Float
     - ``float64``
   * - Integer
     - ``int64``
   * - String
     - ``object``
   * - Boolean
     - ``bool``
   * - Timestamp
     - ``datetime64``


Chunked responses
^^^^^^^^^^^^^^^^^
Aioinflux supports InfluxDB chunked queries. Passing ``chunked=True`` when calling
|query|, returns an :py:class:`~collections.abc.AsyncGenerator` object,
which can asynchronously iterated.
Using chunked requests allows response processing to be partially done before
the full response is retrieved, reducing overall query time
(at least in theory - your mileage may vary).

.. code:: python

    chunks = await client.query("SELECT * FROM mymeasurement", chunked=True)
    async for chunk in chunks:
        # do something
        await process_chunk(...)

When using chunked responses with ``dataframe`` output, the following construct may be useful:

.. code:: python

    cursor = await client.query("SELECT * FROM mymeasurement", chunked=True)
    df = pd.concat([i async for i in cursor])

If you need to keep track of when the chunks are being returned,
consider setting up a logging handler at ``DEBUG`` level (see :ref:`Debugging` for details).

See the `InfluxDB official docs <https://docs.influxdata.com/influxdb/v1.7/guides/querying_data/#chunking>`__
for more on chunked responses.

Iterating responses
^^^^^^^^^^^^^^^^^^^

By default, |query| returns a parsed JSON response from InfluxDB.
In order to easily iterate over that JSON response point by point, Aioinflux
provides the |iterpoints| function, which returns a generator object:

.. code:: python

    from aioinflux import iterpoints

    r = client.query('SELECT * from h2o_quality LIMIT 10')
    for i in iterpoints(r):
        print(i)

.. code:: text

    [1439856000000000000, 41, 'coyote_creek', '1']
    [1439856000000000000, 99, 'santa_monica', '2']
    [1439856360000000000, 11, 'coyote_creek', '3']
    [1439856360000000000, 56, 'santa_monica', '2']
    [1439856720000000000, 65, 'santa_monica', '3']

|iterpoints| can also be used with chunked responses:

.. code:: python

    chunks = await client.query('SELECT * from h2o_quality', chunked=True)
    async for chunk in chunks:
        for point in iterpoints(chunk):
            # do something


Using custom parsers
""""""""""""""""""""

By default, the generator returned by |iterpoints|
yields a plain list of values without doing any expensive parsing.
However, in case a specific format is needed, an optional ``parser`` argument can be passed.
``parser`` is a function/callable that takes data point values
and, optionally, a ``meta`` parameter containing which takes a
dictionary containing all or a subset of the following:
``{'columns', 'name', 'tags', 'statement_id'}``.

- Example using a regular function and ``meta``

.. code:: python

    r = await client.query('SELECT * from h2o_quality LIMIT 5')
    for i in iterpoints(r, lambda *x, meta: dict(zip(meta['columns'], x))):
        print(i)

.. code:: text

    {'time': 1439856000000000000, 'index': 41, 'location': 'coyote_creek', 'randtag': '1'}
    {'time': 1439856000000000000, 'index': 99, 'location': 'santa_monica', 'randtag': '2'}
    {'time': 1439856360000000000, 'index': 11, 'location': 'coyote_creek', 'randtag': '3'}
    {'time': 1439856360000000000, 'index': 56, 'location': 'santa_monica', 'randtag': '2'}
    {'time': 1439856720000000000, 'index': 65, 'location': 'santa_monica', 'randtag': '3'}


- Example using a :py:func:`~collections.namedtuple`

.. code:: python

    from collections import namedtuple
    nt = namedtuple('MyPoint', ['time', 'index', 'location', 'randtag'])

    r = await client.query('SELECT * from h2o_quality LIMIT 5')
    for i in iterpoints(r, parser=nt):
        print(i)

.. code:: text

    MyPoint(time=1439856000000000000, index=41, location='coyote_creek', randtag='1')
    MyPoint(time=1439856000000000000, index=99, location='santa_monica', randtag='2')
    MyPoint(time=1439856360000000000, index=11, location='coyote_creek', randtag='3')
    MyPoint(time=1439856360000000000, index=56, location='santa_monica', randtag='2')
    MyPoint(time=1439856720000000000, index=65, location='santa_monica', randtag='3')


Caching query results
^^^^^^^^^^^^^^^^^^^^^

.. versionchanged:: v0.10.0

Caching can is useful in highly iterative/repetitive workloads
(i.e.: machine learning / quantitative finance model tuning)
that constantly query InfluxDB for the same historical data repeatedly.
By saving query results locally, load on your InfluxDB instance can be greatly reduced.

Aioinflux used to provide a built-in caching local functionality using Redis.
However, due to low perceived usage, vendor lock-in (Redis) and extra complexity
added to Aioinflux, it was removed.

Here we explain how to add a simple caching layer using pickle.
The example below caches dataframes as compressed pickle files on disk.
It can be easily modified to use your preferred caching strategy, such as
using different serialization, compression, cache key generation, etc.
See function docstrings, code comments below for more details.

- Uncached code:

.. code:: python

    from aioinflux import InfluxDBClient

    c = InfluxDBClient(output='dataframe')
    q = """
        SELECT * FROM executions
        WHERE product_code='BTC_JPY'
        AND time >= '2020-05-22'
        AND time < '2020-05-23'
    """
    # If this query is repeated, it will keep hitting InfluxDB,
    # increasing the load on instance and using extra bandwidth
    df = await c.query(q)


- Caching code:

.. code:: python

    import re
    import hashlib
    import pathlib
    import pandas as pd

    def _hash_query(q: str) -> str:
        """Normalizes and hashes the query to generate a caching key"""
        q = re.sub("\s+", " ", q).strip().lower().encode()
        return hashlib.sha1(q).hexdigest()

    async def fetch(influxdb: InfluxDBClient, q: str) -> Tuple[pd.DataFrame, bool]:
        """Tries to see if query is cached, else fetches data from the database.

        Returns a tuple containing the query results and a boolean indicating whether or not
        the data came from local cache or directly from InfluxDB
        """
        p = pathlib.Path(_hash_query(q))
        if p.exists():
            return pd.read_pickle(p, compression="xz"), True
        df = await influxdb.query(q)
        df.to_pickle(str(p), compression="xz")
        return df, False


- Caching code usage:

.. code:: python

    df, cached = await fetch(c, q)
    print(cached)  # False - cache miss

    df, cached = await fetch(c, q)
    print(cached)  # True - cache hit


Other functionality
-------------------

Authentication
^^^^^^^^^^^^^^

Aioinflux supports basic HTTP authentication provided by :py:class:`aiohttp.BasicAuth`.
Simply pass ``username`` and ``password`` when instantiating |client|:

.. code:: python

    client = InfluxDBClient(username='user', password='pass)


Unix domain sockets
^^^^^^^^^^^^^^^^^^^

If your InfluxDB server uses UNIX domain sockets you can use ``unix_socket``
when instantiating |client|:

.. code:: python

    client = InfluxDBClient(unix_socket='/path/to/socket')

See |unix_connector|_ for details.

.. |unix_connector| replace:: ``aiohttp.UnixConnector``
.. _unix_connector: https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.UnixConnector


Custom timeouts
^^^^^^^^^^^^^^^

.. todo:: TODO

Other ``aiohttp`` functionality
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. todo:: Explain how to customize :class:`aiohttp.ClientSession` creation


HTTPS/SSL
^^^^^^^^^
Aioinflux/InfluxDB uses HTTP by default, but HTTPS can be used by passing ``ssl=True``
when instantiating |client|.
If you are acessing your your InfluxDB instance over the public internet, setting up HTTPS is
`strongly recommended <https://docs.influxdata.com/influxdb/v1.7/administration/https_setup/>`__.


.. code:: python

    client = InfluxDBClient(host='my.host.io', ssl=True)


Database selection
^^^^^^^^^^^^^^^^^^

After the instantiation of the |client| object, database
can be switched by changing the ``db`` attribute:

.. code:: python

    client = InfluxDBClient(db='db1')
    client.db = 'db2'

Beware that differently from some NoSQL databases (such as MongoDB),
InfluxDB requires that a databases is explicitly created (by using the
|CREATE_DATABASE|_ query) before doing any operations on it.

.. |CREATE_DATABASE| replace:: ``CREATE DATABASE``
.. _`CREATE_DATABASE`: https://docs.influxdata.com/influxdb/latest/query_language/database_management/#create-database


Debugging
^^^^^^^^^

If you are having problems while using Aioinflux, enabling logging might be useful.

Below is a simple way to setup logging from your application:

.. code:: python

    import logging

    logging.basicConfig()
    logging.getLogger('aioinflux').setLevel(logging.DEBUG)

For further information about logging, please refer to the
`official documentation <https://docs.python.org/3/library/logging.html>`__.


.. |lineprotocol| replace:: :func:`~aioinflux.serialization.usertype.lineprotocol`
.. |client| replace:: :class:`~aioinflux.client.InfluxDBClient`
.. |write| replace:: :meth:`~aioinflux.client.InfluxDBClient.write`
.. |query| replace:: :meth:`~aioinflux.client.InfluxDBClient.query`
.. |iterpoints| replace:: :func:`~aioinflux.iterutils.iterpoints`
.. |datetimeindex| replace:: :class:`~pandas.DatetimeIndex`
.. |datetime| replace:: :py:class:`datetime.datetime`
