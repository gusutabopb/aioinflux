.. _api:

API Reference
=============

.. module:: aioinflux

This part of the documentation covers all the interfaces of Aioinflux

.. note:: 🚧 This section of the documentation is under writing and may be wrong/incomplete 🚧


Client Interface
----------------

.. autoclass:: aioinflux.client.InfluxDBClient
   :inherited-members:

.. autoexception:: aioinflux.client.InfluxDBWriteError


Serialization
-------------

.. automodule:: aioinflux.serialization
.. autofunction:: aioinflux.serialization.common.escape
.. autofunction:: aioinflux.serialization.dataframe.serialize
.. autofunction:: aioinflux.serialization.dataframe.parse
.. autofunction:: aioinflux.serialization.usertype.lineprotocol

