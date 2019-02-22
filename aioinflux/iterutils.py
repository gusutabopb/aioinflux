import inspect

from typing import Optional, Iterator, Callable, Any


def iterpoints(resp: dict, parser: Optional[Callable] = None) -> Iterator[Any]:
    """Iterates a response JSON yielding data point by point.

    Can be used with both regular and chunked responses.
    By default, returns just a plain list of values representing each point,
    without column names, or other metadata.

    In case a specific format is needed, an optional ``parser`` argument can be passed.
    ``parser`` is a function/callable that takes data point values
    and, optionally, a ``meta`` parameter containing which takes a
    dictionary containing all or a subset of the following:
    ``{'columns', 'name', 'tags', 'statement_id'}``.

    Sample parser functions:

    .. code:: python

       # Function optional meta argument
       def parser(*x, meta):
           return dict(zip(meta['columns'], x))

       # Namedtuple (callable)
       from collections import namedtuple
       parser = namedtuple('MyPoint', ['col1', 'col2', 'col3'])


    :param resp: Dictionary containing parsed JSON (output from InfluxDBClient.query)
    :param parser: Optional parser function/callable
    :return: Generator object
    """
    for statement in resp['results']:
        if 'series' not in statement:
            continue
        for series in statement['series']:
            if parser is None:
                return (x for x in series['values'])
            elif 'meta' in inspect.signature(parser).parameters:
                meta = {k: series[k] for k in series if k != 'values'}
                meta['statement_id'] = statement['statement_id']
                return (parser(*x, meta=meta) for x in series['values'])
            else:
                return (parser(*x) for x in series['values'])
    return iter([])
