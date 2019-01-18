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

.. autoexception:: aioinflux.client.InfluxDBError
.. autoexception:: aioinflux.client.InfluxDBWriteError

Result iteration
""""""""""""""""
.. automodule:: aioinflux.iterutils
   :members:


Serialization
-------------

Mapping
"""""""
.. automodule:: aioinflux.serialization.mapping
   :members:

Dataframe
"""""""""
.. automodule:: aioinflux.serialization.dataframe
   :members:

User-defined classes
""""""""""""""""""""
.. automodule:: aioinflux.serialization.usertype
   :members:
   :undoc-members:
