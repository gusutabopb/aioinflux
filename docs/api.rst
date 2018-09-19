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

.. autofunction:: aioinflux.serialization.common.escape
.. autofunction:: aioinflux.serialization.dataframe.serialize
.. autofunction:: aioinflux.serialization.dataframe.parse
.. autoclass:: aioinflux.serialization.datapoint.DataPoint
.. autoclass:: aioinflux.serialization.datapoint.InfluxType
.. autofunction:: aioinflux.serialization.datapoint.datapoint

