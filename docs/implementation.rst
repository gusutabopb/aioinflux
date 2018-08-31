Implementation details
======================

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
