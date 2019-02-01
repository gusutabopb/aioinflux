from typing import Optional, Iterator, Callable


def iterpoints(resp: dict, parser: Optional[Callable] = None) -> Iterator:
    """Iterates a response JSON yielding data point by point.

    Can be used with both regular and chunked responses.
    By default, returns just a plain list of values representing each point,
    without column names, or other metadata.

    In case a specific format is needed, an optional ``parser`` argument can be passed.
    ``parser`` is a function that takes a list of values for each data point and a
    metadata dictionary containing all or a subset of the following:
    ``{'columns', 'name', 'tags', 'statement_id'}``.

    Sample parser function:

    .. code:: python

       def parser(x, meta):
           return dict(zip(meta['columns'], x))

    :param resp: Dictionary containing parsed JSON (output from InfluxDBClient.query)
    :param parser: Optional parser function
    :return: Generator object
    """
    for statement in resp['results']:
        if 'series' not in statement:
            continue
        for series in statement['series']:
            meta = {k: series[k] for k in series if k != 'values'}
            meta['statement_id'] = statement['statement_id']
            if parser is None:
                return (x for x in series['values'])
            else:
                return (parser(x, meta) for x in series['values'])
    return iter([])
