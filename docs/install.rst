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

The main third-party library dependency is |aiohttp|, for all HTTP
request handling. and |pandas| for :class:`~pandas.DataFrame` reading/writing support.

There are currently no plans to support other HTTP libraries besides |aiohttp|.
If |aiohttp| + |asyncio| is not your soup, see :ref:`Alternatives`.

.. |asyncio| replace:: :py:mod:`asyncio`
.. |aiohttp| replace:: :py:mod:`aiohttp`
.. |pandas| replace:: :py:mod:`pandas`
.. _`official Python Client`: https://github.com/influxdata/influxdb-python