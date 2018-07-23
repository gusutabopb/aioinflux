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

.. autofunction:: aioinflux.serialization.make_df
.. autofunction:: aioinflux.serialization.parse_df

