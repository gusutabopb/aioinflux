aioinflux
=========
.. image:: https://img.shields.io/circleci/project/github/plugaai/aioinflux.svg
    :target: https://circleci.com/gh/plugaai/aioinflux
.. image:: https://img.shields.io/codecov/c/github/plugaai/aioinflux.svg
    :target: https://codecov.io/gh/plugaai/aioinflux
.. image:: https://img.shields.io/pypi/v/aioinflux.svg
    :target: https://pypi.python.org/pypi/aioinflux
.. image:: https://img.shields.io/pypi/pyversions/aioinflux.svg
    :target: https://pypi.python.org/pypi/aioinflux


Asynchronous Python client for InfluxDB. Built on top of
|aiohttp|_ and |asyncio|_.

InfluxDB is an open-source distributed time series database. Find more
about InfluxDB at http://influxdata.com/

Installation
------------

To install the latest release:

.. code:: bash

    $ pip install aioinflux

The library is still in beta, so you may also want to install the latest version from
the development branch:

.. code:: bash

    $ pip install git+https://github.com/plugaai/aioinflux@dev

Dependencies
~~~~~~~~~~~~

Aioinflux supports Python 3.6+ **ONLY**. For older Python versions
please use the `official Python client`_

Third-party library dependencies are: |aiohttp|_ for all HTTP
request handling and |pandas|_ for ``DataFrame`` reading/writing support.

.. |asyncio| replace:: ``asyncio``
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. |aiohttp| replace:: ``aiohttp``
.. _aiohttp: https://github.com/aio-libs/aiohttp
.. |pandas| replace:: ``pandas``
.. _pandas: https://github.com/pandas-dev/pandas
.. _`official Python Client`: https://github.com/influxdata/influxdb-python

Usage
-----

TL;DR:
~~~~~~

This sums most of what you can do with ``aioinflux``:

.. code:: python

    import asyncio
    from aioinflux import InfluxDBClient

    point = dict(time='2009-11-10T23:00:00Z',
                 measurement='cpu_load_short',
                 tags={'host': 'server01',
                       'region': 'us-west'},
                 fields={'value': 0.64})

    client = InfluxDBClient(db='testdb')

    coros = [client.create_database(db='testdb'),
             client.write(point),
             client.query('SELECT value FROM cpu_load_short')]

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(asyncio.gather(*coros))
    for result in results:
        print(result)

Client modes
~~~~~~~~~~~~

Despite its name, ``InfluxDBClient`` can also run in sync/blocking
modes. Available modes are: ``async`` (default), ``blocking`` and
``dataframe``.

Example using ``blocking`` mode:

.. code:: python

    client = InfluxDBClient(db='testdb', mode='blocking')
    client.ping()
    client.write(point)
    client.query('SELECT value FROM cpu_load_short')

See `Retrieving DataFrames <#retrieving-dataframes>`__ for ``dataframe``
mode usage.

Writing data
~~~~~~~~~~~~

Input data can be: 1) A string properly formatted in InfluxDB's line
protocol 2) A dictionary containing the following keys: ``measurement``,
``time``, ``tags``, ``fields`` 3) A Pandas DataFrame with a
DatetimeIndex 4) An iterable of one of the above

Input data in formats 2-4 are parsed into the `line
protocol`_ before being written to InfluxDB. All parsing functionality is located
at |serialization|_. Beware that
serialization is not highly optimized (PRs are welcome!) and may become
a bottleneck depending on your application.

The ``write`` method returns ``True`` when successful and raises an
``InfluxDBError`` otherwise.

.. _`line protocol`: https://docs.influxdata.com/influxdb/latest/write_protocols/line_protocol_reference/
.. |serialization| replace:: ``serialization.py``
.. _serialization: aioinflux/serialization.py

Writing dictionary-like objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Aioinflux accepts any dictionary-like object (mapping) as input.
However, that dictionary must be properly formatted and contain the
following keys:

1) **measurement**: Optional. Must be a string-like object. If
   omitted, must be specified when calling ``InfluxDBClient.write``
   by passing a ``measurement`` argument.
2) **time**: Optional. The value can be ``datetime.datetime``,
   date-like string (e.g., ``2017-01-01``, ``2009-11-10T23:00:00Z``) or
   anything else that can be parsed by Pandas' |Timestamp|_ class initializer.
3) **tags**: Optional. This must contain another mapping of field
   names and values. Both tag keys and values should be strings.
4) **fields**: Mandatory. This must contain another mapping of field
   names and values. Field keys should be strings. Field values can be
   ``float``, ``int``, ``str``, or ``bool`` or any equivalent type.

.. |Timestamp| replace:: ``Timestamp``
.. _Timestamp: https://pandas.pydata.org/pandas-docs/stable/timeseries.html


Any fields other then the above will be ignored when writing data to
InfluxDB.

A typical dictionary-like point would look something like the following:

.. code:: python

    {'time': '2009-11-10T23:00:00Z',
    'measurement': 'cpu_load_short',
    'tags': {'host': 'server01', 'region': 'us-west'},
    'fields': {'value1': 0.64, 'value2': True, 'value3': 10}}

Writing DataFrames
^^^^^^^^^^^^^^^^^^

Aioinflux also accepts Pandas dataframes as input. The only requirements
for the dataframe is that the index **must** be of type
``DatetimeIndex``. Also, any column whose ``dtype`` is ``object`` will
be converted to a string representation.

A typical DataFrame input should look something like the following:

.. code:: text

                                           LUY       BEM       AJW tag
    2017-06-24 08:45:17.929097+00:00  2.545409  5.173134  5.532397   B
    2017-06-24 10:15:17.929097+00:00 -0.306673 -1.132941 -2.130625   E
    2017-06-24 11:45:17.929097+00:00  0.894738 -0.561979 -1.487940   B
    2017-06-24 13:15:17.929097+00:00 -1.799512 -1.722805 -2.308823   D
    2017-06-24 14:45:17.929097+00:00  0.390137 -0.016709 -0.667895   E

The measurement name must be specified with the ``measurement`` argument
when calling ``InfluxDBClient.write``. Additional tags can also be
passed using arbitrary keyword arguments.

**Example:**

.. code:: python

    client = InfluxDBClient(db='testdb', mode='blocking')
    client.write(df, measurement='prices', tag_columns=['tag'], asset_class='equities')

In the example above, ``df`` is the DataFrame we are trying to write to
InfluxDB and ``measurement`` is the measurement we are writing to.

``tag_columns`` is in an optional iterable telling which of the
dataframe columns should be parsed as tag values. If ``tag_columns`` is
not explicitly passed, all columns in the dataframe will be treated as
InfluxDB field values.

Any other keyword arguments passed to ``InfluxDBClient.write`` are
treated as extra tags which will be attached to the data being written
to InfluxDB. Any string which is a valid `InfluxDB identifier`_ and
valid `Python identifier`_ can be used as an extra tag key (with the
exception of they strings ``data``, ``measurement`` and ``tag_columns``).

See ``InfluxDBClient.write`` docstring for details.

.. _`InfluxDB identifier`: https://docs.influxdata.com/influxdb/latest/query_language/spec/#identifiers
.. _`Python identifier`: https://docs.python.org/3/reference/lexical_analysis.html#identifiers

Querying data
~~~~~~~~~~~~~

Querying data is as simple as passing an InfluxDB query string to
``InfluxDBClient.query``:

.. code:: python

    client.query('SELECT myfield FROM mymeasurement')

The result (in ``blocking`` and ``async`` modes) is a dictionary
containing the raw JSON data returned by the InfluxDB `HTTP API`_:

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

Retrieving DataFrames
^^^^^^^^^^^^^^^^^^^^^

When the client is in ``dataframe`` mode, ``InfluxDBClient.query`` will
return a Pandas ``DataFrame``:


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

Mode can be chosen not only during object instantiation but also by
simply |changing_mode|_.


.. |changing_mode| replace:: changing the ``mode`` attribute
.. _changing_mode: #switching-modes


Chunked responses
^^^^^^^^^^^^^^^^^

TODO

Query patterns
^^^^^^^^^^^^^^

Aioinflux provides some wrappers around ``InfluxDBClient.query`` in
order to provide convenient access in IPython/Jupyter to commonly used query patterns.

Query patterns are query strings containing optional named "replacement fields"
surrounded by curly braces ``{}``, just as in |str_format|_.
Replacement field values are defined by keyword arguments when calling the method
associated with the query pattern.

Aioinflux comes with some built-in query patterns, defined in `queries.yml`_.
Users can define additional query patterns by using the |set_custom_queries|_ helper function.
However, for one-off queries, passing a raw query to directly to
``InfluxDBClient.query`` can be simpler.

Built-in query pattern examples:

.. code:: python

    client.create_database(db='foo')            # CREATE DATABASE {db}
    client.drop_measurement(measurement='bar')  # DROP MEASUREMENT {measurement}'
    client.show_users()                         # SHOW USERS

Please refer to InfluxDB documentation_ for further query-related information.

.. _`queries.yml`: aioinflux/queries.yml
.. _documentation: https://docs.influxdata.com/influxdb/latest/query_language/
.. |str_format| replace:: ``str_format()``
.. _str_format: https://docs.python.org/3/library/string.html#formatstrings
.. |set_custom_queries| replace:: ``aioinflux.set_custom_queries``
.. _set_custom_queries: aioinflux/client.py#L240

Other functionality
~~~~~~~~~~~~~~~~~~~

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
Aioinflux/InfluxDB use HTTP by default, but HTTPS can be used by passing ``ssl=True``
when instantiating ``InfluxDBClient``:


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

Switching modes
^^^^^^^^^^^^^^^

After the instantiation of the ``InfluxDBClient`` object, database
can be switched on-the-fly by changing the ``mode`` attribute:

.. code:: python

    client = InfluxDBClient(mode='blocking')
    client.mode = 'dataframe'


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


Implementation
--------------

Since InfluxDB exposes all its functionality through an `HTTP
API <https://docs.influxdata.com/influxdb/latest/tools/api/>`__,
``InfluxDBClient`` tries to be nothing more than a thin and simple
wrapper around that API.

The InfluxDB HTTP API exposes exactly three endpoints/functions:
``ping``, ``write`` and ``query``.

``InfluxDBClient`` merely wraps these three functions and provides
some parsing functionality for generating line protocol data (when
writing) and parsing JSON responses (when querying).

Additionally,
`partials <https://en.wikipedia.org/wiki/Partial_application>`__ are
used in order to provide convenient access to commonly used query
patterns. See the `Query patterns <#query-patterns>`__
section for details.

Contributing
------------

| To contribute, fork the repository on GitHub, make your changes and
  submit a pull request.
| Aioinflux is not a mature project yet, so just simply raising issues
  is also greatly appreciated :)

