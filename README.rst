aioinflux
=========
.. image:: https://img.shields.io/circleci/project/github/gusutabopb/aioinflux.svg
   :target: https://circleci.com/gh/gusutabopb/aioinflux
   :alt: CI status

.. image:: https://img.shields.io/codecov/c/github/gusutabopb/aioinflux.svg
   :target: https://codecov.io/gh/gusutabopb/aioinflux
   :alt: Coverage

.. image:: https://img.shields.io/pypi/v/aioinflux.svg
   :target: https://pypi.python.org/pypi/aioinflux
   :alt: PyPI package

.. image:: https://img.shields.io/pypi/pyversions/aioinflux.svg
   :target: https://pypi.python.org/pypi/aioinflux
   :alt: Supported Python versions

.. image:: https://readthedocs.org/projects/aioinflux/badge/?version=latest
   :target: https://aioinflux.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation status


Asynchronous Python client for `InfluxDB`_. Built on top of
`aiohttp`_ and `asyncio`_.
Aioinflux is an alternative to the official InfluxDB Python client.

Aioinflux supports interacting with InfluxDB in a non-blocking way by using `aiohttp`_.
It also supports writing and querying of `Pandas`_ dataframes,
among other handy functionality.

.. _Pandas: http://pandas.pydata.org/
.. _InfluxDB: http://influxdata.com/
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _aiohttp: https://github.com/aio-libs/aiohttp

Please refer to the `documentation`_ for more details.

Installation
------------

Python 3.6+ is required.
You also need to have access to a running instance of InfluxDB.

.. code:: bash

   pip install aioinflux



Quick start
-----------

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


See the `documentation`_ for more detailed usage.

.. _documentation: http://aioinflux.readthedocs.io/en/latest/