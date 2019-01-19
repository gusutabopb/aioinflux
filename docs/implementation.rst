Implementation details
======================

Since InfluxDB exposes all its functionality through an `HTTP
API <https://docs.influxdata.com/influxdb/latest/tools/api/>`__,
:class:`~aioinflux.client.InfluxDBClient` tries to be nothing more
than a thin and simple wrapper around that API.

The InfluxDB HTTP API exposes exactly three endpoints/functions:
:meth:`~aioinflux.client.InfluxDBClient.ping`,
:meth:`~aioinflux.client.InfluxDBClient.write` and
:meth:`~aioinflux.client.InfluxDBClient.query`.

:class:`~aioinflux.client.InfluxDBClient` merely wraps these three functions and provides
some parsing functionality for generating line protocol data (when
writing) and parsing JSON responses (when querying).

Additionally,
`partials <https://en.wikipedia.org/wiki/Partial_application>`__ are
used in order to provide convenient access to commonly used query
patterns. See the :ref:`Query patterns` section for details.
