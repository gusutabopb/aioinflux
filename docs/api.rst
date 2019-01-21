API Reference
=============

.. contents::
   :local:

Client Interface
----------------

.. autoclass:: aioinflux.client.InfluxDBClient
   :members:

    .. automethod:: __init__


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
