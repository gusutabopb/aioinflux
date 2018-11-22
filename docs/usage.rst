User Guide
==========

TL;DR
-----

This sums most of what you can do with ``aioinflux``:

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

Despite the library's name, :class:`~aioinflux.client.InfluxDBClient` can also run in non-async
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


Writing data
------------

Input data can be:

1. A string (``str`` or ``bytes``) properly formatted in InfluxDB's line protocol
2. A mapping (e.g. ``dict``) containing the following keys: ``measurement``, ``time``, ``tags``, ``fields``
3. A Pandas :class:`~pandas.DataFrame` with a :class:`~pandas.DatetimeIndex`
4. A :func:`~aioinflux.serialization.datapoint.DataPoint` object (see `below <#writing-datapoint-objects>`__)
5. An iterable of one of the above

Input data in formats 2-4 are serialized into the `line protocol`_ before being written to InfluxDB.
``str`` or ``bytes`` are assumed to already be in line protocol format and are inserted into InfluxDB as they are.
All serialization from JSON (InfluxDB's only output format) and parsing to line protocol
(InfluxDB's only input format) functionality is located in the :mod:`~aioinflux.serialization` subpackage.

Beware that serialization is not highly optimized (C extensions / cythonization PRs are welcome!) and may become
a bottleneck depending on your application's performance requirements.
It is, however, `reasonably faster`_ than InfluxDB's official Python client.

The ``write`` method returns ``True`` when successful and raises an
``InfluxDBError`` otherwise.

.. _`line protocol`: https://docs.influxdata.com/influxdb/latest/write_protocols/line_protocol_reference/
.. _`reasonably faster`: https://gist.github.com/gusutabopb/42550f0f07628ba61b0ed6322f02855b

Writing dictionary-like objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Aioinflux accepts any dictionary-like object (mapping) as input.
However, that dictionary must be properly formatted and contain the
following keys:

1) **measurement**: Optional. Must be a string-like object. If
   omitted, must be specified when calling :meth:`~aioinflux.client.InfluxDBClient.write`
   by passing a ``measurement`` argument.
2) **time**: Optional. The value can be :class:`datetime.datetime`,
   date-like string (e.g., ``2017-01-01``, ``2009-11-10T23:00:00Z``) or
   anything else that can be parsed by :class:`pandas.Timestamp`.
   See the :ref:`Pandas documentation <pandas:timeseries>` for details.
   If Pandas is not available, |ciso8601|_ is used instead for string parsing.
3) **tags**: Optional. This must contain another mapping of field
   names and values. Both tag keys and values should be strings.
4) **fields**: Mandatory. This must contain another mapping of field
   names and values. Field keys should be strings. Field values can be
   ``float``, ``int``, ``str``, ``bool`` or ``None`` or any its subclasses.
   Attempting to use Numpy types will cause errors as ``np.int64``, ``np.float64``, etc are not
   subclasses of Python's builti-in numeric types.
   Use dataframes for writing data using Numpy types.

.. |ciso8601| replace:: ``ciso8601``
.. _ciso8601: https://github.com/closeio/ciso8601/

Any fields other then the above will be ignored when writing data to
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
   explicitly noted. Aioinflux does the same and assumes any timezone-unaware ``datetime`` object
   or datetime-like strings is in UTC.
   Aioinflux does not raise any warnings when timezone-unaware input is passed
   and silently assumes it to be in UTC.

.. _`broadly agreed`: http://lucumr.pocoo.org/2011/7/15/eppur-si-muove/

Writing DataFrames
^^^^^^^^^^^^^^^^^^

Aioinflux also accepts Pandas dataframes as input. The only requirements
for the dataframe is that the index **must** be of type
:class:`~pandas.DatetimeIndex`. Also, any column whose ``dtype`` is ``object`` will
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
when calling :meth:`~aioinflux.client.InfluxDBClient.write`.
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
:class:`~pandas.DatetimeIndex` will be treated as InfluxDB field values.

Any other keyword arguments passed to :meth:`~aioinflux.client.InfluxDBClient.write` are
treated as extra tags which will be attached to the data being written
to InfluxDB. Any string which is a valid `InfluxDB identifier`_ and
valid `Python identifier`_ can be used as an extra tag key (with the
exception of the strings ``data``, ``measurement`` and ``tag_columns``).

See `API reference <api.html#aioinflux.client.InfluxDBClient.write>`__ for details.

.. _`InfluxDB identifier`: https://docs.influxdata.com/influxdb/latest/query_language/spec/#identifiers
.. _`Python identifier`: https://docs.python.org/3/reference/lexical_analysis.html#identifiers


Writing DataPoint objects
^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 0.4.0

:class:`~aioinflux.serialization.datapoint.DataPoint` are namedtuple-like objects that
provide fast line protocol serialization by defining a schema.

A :class:`~aioinflux.serialization.datapoint.DataPoint` class can be defined using the
:class:`~aioinflux.serialization.datapoint.datapoint` class factory function with some special types annotations:

.. code:: python

   from aioinflux.serialization import datapoint, InfluxType

   @datapoint
   class Trade:
       timestamp: InfluxType.TIMEINT
       instrument: InfluxType.TAGENUM
       source: InfluxType.TAG
       side: InfluxType.TAG
       price: InfluxType.FLOAT
       size: InfluxType.INT
       trade_id: InfluxType.STR

Alternatively, it can also be defined functionally:

.. code:: python

    Trade = datapoint(dict(
       timestamp=InfluxType.TIMEINT,
       instrument=InfluxType.TAG,
       source=InfluxType.TAG,
       side=InfluxType.TAG,
       price=InfluxType.FLOAT,
       size=InfluxType.INT,
       trade_id=InfluxType.STR,
    ), name='Trade')


The class can then be be instantiated by positional or keyword arguments:

.. code:: python

   # Positional
   trade = Trade(1540184368785116000, 'APPL', 'NASDAQ', 'BUY',
                 219.23, 100, '34a1e085-3122-429c-9662-7ce82039d287')

   # Keyword
   trade = Trade(
      timestamp=1540184368785116000,
      instrument='AAPL',
      source='NASDAQ',
      side='BUY',
      price=219.23,
      size=100,
      trade_id='34a1e085-3122-429c-9662-7ce82039d287'
   )

Attributes can be accessed by dot notation (``__getattr__``) or dictionary-like notation (``__getitem__``).
Iteration is also supported:

.. code:: python

   trade.price  # 219.23
   trade['price']  # 219.23
   list(trade)  # ['timestamp', 'source', 'instrument', 'size', 'price', 'trade_id', 'side']
   list(trade.items()  # [('timestamp', 1540184368785116000), ('source', 'APPL'), ('instrument', 'NASDAQ'), ('size', 'BUY'), ('price', 219.23), ('trade_id', 100), ('side', '34a1e085-3122-429c-9662-7ce82039d287')]


Every DataPoint object has a :meth:`~aioinflux.serialization.datapoint.DataPoint.to_lineprotocol` method which
generates a line protocol representation of the datapoint:

.. code:: python

   trade.to_lineprotocol()
   # b'Trade,source=APPL,instrument=NASDAQ size=BUYi,price=219.23,trade_id="100",side="34a1e085-3122-429c-9662-7ce82039d287" 1540184368785116000'

:meth:`~aioinflux.client.InfluxDBClient.write` can write DataPoint objects (or iterables of DataPoint objects) to InfluxDB
(by using :meth:`~aioinflux.serialization.datapoint.DataPoint.to_lineprotocol` internally):

.. code:: python

   client = InfluxDBClient()
   await client.write(trade)

Every class generated by :class:`~aioinflux.serialization.datapoint.datapoint` has
:class:`~aioinflux.serialization.datapoint.DataPoint` as its base class:

.. code:: python

   isintance(trade, DataPoint)  # True



DataPoint Types
"""""""""""""""

.. note::

   In this section, the word "types" refers to members of
   the :class:`~aioinflux.serialization.datapoint.InfluxType` enum

DataPoint types are defined using the :class:`~aioinflux.serialization.datapoint.InfluxType` enum.
All type annotations MUST be a :class:`~aioinflux.serialization.datapoint.InfluxType` member.
The types available are based on the native types of InfluxDB
(see the `InfluxDB docs <https://docs.influxdata.com/influxdb/v1.6/write_protocols/line_protocol_reference/#data-types>`__ for
details), with some extra types to help the serialization to line protocol and/or allow more flexible usage
(such as the use of :py:class:`~enum.Enum` objects).


.. list-table::
   :header-rows: 1
   :widths: 10 30
   :align: center

   * - Datapoint type
     - Description
   * - ``MEASUREMENT``
     - Optional. If missing, the measurement becomes the class name
   * - ``TIMEINT``
     - Timestamp is a nanosecond UNIX timestamp
   * - ``TIMESTR``
     - Timestamp is a datetime string (somewhat compliant to ISO 8601)
   * - ``TIMEDT``
     - Timestamp is a :py:class:`~datetime.datetime` (or subclasses such as :class:`pandas.Timestamp`)
   * - ``TAG``
     - Treats field as an InfluxDB tag
   * - ``TAGENUM``
     - Same as ``TAG`` but allows the use of :py:class:`~enum.Enum`
   * - ``PLACEHOLDER``
     - | Boolean field which is always true and NOT present in the class constructor.
       | Workaround for creating field-less points (which is not supported natively by InfluxDB)
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


DataPoint options
"""""""""""""""""

The :func:`~aioinflux.serialization.datapoint.datapoint` function/decorator provides some options to
customize object instantiation/serialization.
See the `API reference <api.html#aioinflux.serialization.datapoint.datapoint>`__ for details.


Advantages compared to dictionary-like objects
""""""""""""""""""""""""""""""""""""""""""""""

- Faster (see below)
- Explicit field names: better IDE support
- Explicit types: avoids types errors when writing to InfluxDB (e.g.: ``float`` field getting parsed as a ``float``)
- Optional ``None`` support
- No need to use nested data structures


Performance
"""""""""""

Serialization using :class:`~aioinflux.serialization.datapoint.DataPoint` is about 3x faster
than dictionary-like objects.
See this `notebook <https://github.com/gusutabopb/aioinflux/tree/master/notebooks/datapoint_benchmark.ipynb>`__  and
the `API reference <api.html#aioinflux.serialization.datapoint.datapoint>`__ for details.
Regarding object instantiation performance, dictionaries are slightly faster,
but the time difference is negligible and 1-2 orders of magnitude smaller than time required for serialization.


Querying data
-------------

Querying data is as simple as passing an InfluxDB query string to
:meth:`~aioinflux.client.InfluxDBClient.query`:

.. code:: python

    client.query('SELECT myfield FROM mymeasurement')

The result (in ``blocking`` and ``async`` modes) is a dictionary
containing the parsed JSON data returned by the InfluxDB `HTTP API`_:

.. _`HTTP API`: https://docs.influxdata.com/influxdb/latest/guides/querying_data/#querying-data-using-the-http-api

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


Output formats
^^^^^^^^^^^^^^

When querying data, ``InfluxDBClient`` can return data in one of the following formats:

1) ``json``: Default. Returns the a dictionary containing the JSON response received from InfluxDB.
2) ``bytes``: Returns raw, non-parsed JSON binary blob as received from InfluxDB.
   The contents of the returns JSON blob are not checked at all. Useful for response caching.
3) ``dataframe``: Parses the result into a Pandas dataframe or a dictionary of dataframes.
   See `Retrieving DataFrames <#retrieving-dataframes>`__ for details.
4) ``iterable``: Wraps the JSON response in a ``InfluxDBResult`` or ``InfluxDBChunkedResult``
   object. This object main purpose is to facilitate iteration of data.
   See `Iterating responses <#iterating-responses>`__ for details.


The output format for can be switched on-the-fly by changing the ``output`` attribute:

.. code:: python

    client = InfluxDBClient(output='dataframe')
    client.mode = 'json'


Retrieving DataFrames
^^^^^^^^^^^^^^^^^^^^^

When the client is in ``dataframe`` mode, :meth:`~aioinflux.client.InfluxDBClient.query`
will return a :class:`pandas.DataFrame`:


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
   (such as a ``GROUP by "tag"`` query), a dictionary of dataframes or a list of
   dictionaries of dataframes may be returned. 
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
:meth:`~aioinflux.client.InfluxDBClient.query`, returns an ``AsyncGenerator`` object,
which can asynchronously iterated.
Using chunked requests allows response processing to be partially done before
the full response is retrieved, reducing overall query time.

.. code:: python

    chunks = await client.query("SELECT * FROM mymeasurement", chunked=True)
    async for chunk in chunks:
        # do something
        await process_chunk(...)

Chunked responses are not supported when using the ``dataframe`` output format.

Iterating responses
^^^^^^^^^^^^^^^^^^^

By default, :meth:`~aioinflux.client.InfluxDBClient.query`
returns a parsed JSON response from InfluxDB.
In order to easily iterate over that JSON response point by point, Aioinflux
provides the ``iterpoints`` function, which returns a generator object:

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

``iterpoints`` can also be used with chunked responses:

.. code:: python

    chunks = await client.query('SELECT * from h2o_quality', chunked=True)
    async for chunk in chunks:
        for point in iterpoints(chunk):
            # do something

By default, the generator returned by ``iterpoints`` yields a plain list of values without
doing any expensive parsing.
However, in case a specific format is needed, an optional ``parser`` argument can be passed.
``parser`` is a function that takes the raw value list for each data point and an additional
metadata dictionary containing all or a subset of the following:
``{'columns', 'name', 'tags', 'statement_id'}``.


.. code:: python

    r = await client.query('SELECT * from h2o_quality LIMIT 5')
    for i in iterpoints(r, lambda x, meta: dict(zip(meta['columns'], x))):
        print(i)

.. code:: text

    {'time': 1439856000000000000, 'index': 41, 'location': 'coyote_creek', 'randtag': '1'}
    {'time': 1439856000000000000, 'index': 99, 'location': 'santa_monica', 'randtag': '2'}
    {'time': 1439856360000000000, 'index': 11, 'location': 'coyote_creek', 'randtag': '3'}
    {'time': 1439856360000000000, 'index': 56, 'location': 'santa_monica', 'randtag': '2'}
    {'time': 1439856720000000000, 'index': 65, 'location': 'santa_monica', 'randtag': '3'}

Besides being explicitly with a raw response, ``iterpoints`` is also be used "automatically"
by ``InfluxDBResult`` and ``InfluxDBChunkedResult`` when using ``iterable`` mode:

.. code:: python

    client.output = 'iterable'
    # Returns InfluxDBResult object
    r = client.query('SELECT * from h2o_quality LIMIT 10')
    for i in r:
        # do something

    # Returns InfluxDBChunkedResult object
    r = await client.query('SELECT * from h2o_quality', chunked=True)
    async for i in r:
        # do something

    # Returns InfluxDBChunkedResult object
    r = await client.query('SELECT * from h2o_quality', chunked=True)
    async for chunk in r.iterchunks():
        # do something with JSON chunk

Query patterns
^^^^^^^^^^^^^^

Aioinflux provides a wrapping mechanism around ``InfluxDBClient.query`` in
order to provide convenient access to commonly used query patterns.

Query patterns are query strings containing optional named "replacement fields"
surrounded by curly braces ``{}``, just as in |str_format|_.
Replacement field values are defined by keyword arguments when calling the method
associated with the query pattern. Differently from plain |str_format|, positional
arguments are also supported and can be mixed with keyword arguments.

Aioinflux built-in query patterns are defined here_.
Users can also dynamically define additional query patterns by using
the |set_qp|_ helper function.
User-defined query patterns have the disadvantage of not being shown for
auto-completion in IDEs such as Pycharm.
However, they do show up in dynamic environments such as Jupyter.
If you have a query pattern that you think will used by many people and should be built-in,
please submit a PR.

Built-in query pattern examples:

.. code:: python

    client.create_database(db='foo')   # CREATE DATABASE {db}
    client.drop_measurement('bar')     # DROP MEASUREMENT {measurement}'
    client.show_users()                # SHOW USERS

    # Positional and keyword arguments can be mixed
    client.show_tag_values_from('bar', key='spam')  # SHOW TAG VALUES FROM {measurement} WITH key = "{key}"

Please refer to InfluxDB documentation_ for further query-related information.

.. _here: aioinflux/client.py#L330
.. _documentation: https://docs.influxdata.com/influxdb/latest/query_language/
.. |str_format| replace:: ``str_format()``
.. _str_format: https://docs.python.org/3/library/string.html#formatstrings
.. |set_qp| replace:: ``InfluxDBClient.set_query_pattern``
.. _set_qp: aioinflux/client.py#L345

Other functionality
-------------------

Authentication
^^^^^^^^^^^^^^

Aioinflux supports basic HTTP authentication provided by |basic_auth|_.
Simply pass ``username`` and ``password`` when instantiating ``InfluxDBClient``:

.. code:: python

    client = InfluxDBClient(username='user', password='pass)


.. |basic_auth| replace:: ``aiohttp.BasicAuth``
.. _basic_auth: https://docs.aiohttp.org/en/stable/client_reference.html#basicauth


Unix domain sockets
^^^^^^^^^^^^^^^^^^^

If your InfluxDB server uses UNIX domain sockets you can use ``unix_socket``
when instantiating ``InfluxDBClient``:

.. code:: python

    client = InfluxDBClient(unix_socket='/path/to/socket')

See |unix_connector|_ for details.

.. |unix_connector| replace:: ``aiohttp.UnixConnector``
.. _unix_connector: https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.UnixConnector


HTTPS/SSL
^^^^^^^^^
Aioinflux/InfluxDB uses HTTP by default, but HTTPS can be used by passing ``ssl=True``
when instantiating ``InfluxDBClient``. If you are acessing your your InfluxDB instance
over the public internet, setting up HTTPS is
`strongly recommended <https://docs.influxdata.com/influxdb/v1.6/administration/https_setup/>`__.


.. code:: python

    client = InfluxDBClient(host='my.host.io', ssl=True)


Database selection
^^^^^^^^^^^^^^^^^^

After the instantiation of the ``InfluxDBClient`` object, database
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
