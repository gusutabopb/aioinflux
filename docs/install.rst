Installation
============

To install the latest release:

.. code:: bash

    $ pip install aioinflux
    $ pip install aioinflux[pandas]  # For DataFrame parsing support

The library is still in beta, so you may also want to install the latest version from
the development branch:

.. code:: bash

    $ pip install git+https://github.com/plugaai/aioinflux@dev

Dependencies
~~~~~~~~~~~~

Aioinflux supports Python 3.6+ **ONLY**. For older Python versions
please use the `official Python client`_.
However, there is `some discussion <https://github.com/plugaai/aioinflux/issues/10>`_
regarding Pypy/Python 3.5 support.

The main third-party library dependency is |aiohttp|_, for all HTTP
request handling. and |pandas|_ for ``DataFrame`` reading/writing support.

There are currently no plans to support other HTTP libraries besides ``aiohttp``.
If ``aiohttp`` + ``asyncio`` is not your soup, see `alternatives <index.html#alternatives>`__.

.. |asyncio| replace:: ``asyncio``
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. |aiohttp| replace:: ``aiohttp``
.. _aiohttp: https://github.com/aio-libs/aiohttp
.. |pandas| replace:: ``pandas``
.. _pandas: https://github.com/pandas-dev/pandas
.. _`official Python Client`: https://github.com/influxdata/influxdb-python