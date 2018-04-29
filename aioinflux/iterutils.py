from typing import Optional, Generator, Callable


class InfluxDBResult:
    __slots__ = ('_data', 'parser', 'query')

    def __init__(self, data, parser=None, query=None):
        self._data = data
        self.parser = parser
        self.query = query

    @property
    def data(self):
        return self._data

    @property
    def series_count(self):
        return len(self._count())

    def __len__(self):
        """Returns number of total points in data"""
        return sum(self._count())

    def __repr__(self):
        q = self.query[:80] + '...' if len(self.query) > 80 else self.query
        return f'<{type(self).__name__} [q="{q}"]>'

    def __iter__(self):
        return iterpoints(self.data, parser=self.parser)

    def show(self):
        return list(self)

    def _count(self):
        return [len(series['values'])
                for statement in self._data['results'] if 'series' in statement
                for series in statement['series']]


class InfluxDBChunkedResult:
    __slots__ = ('_gen', 'parser', 'query')

    def __init__(self, gen, parser=None, query=None):
        self._gen = gen
        self.parser = parser
        self.query = query

    @property
    def gen(self):
        return self._gen

    def __repr__(self):
        q = self.query[:80] + '...' if len(self.query) > 80 else self.query
        return f'<{type(self).__name__} [q="{q}"]>'

    def __aiter__(self):
        return self.iterpoints()

    async def iterpoints(self):
        async for chunk in self._gen:
            for i in iterpoints(chunk, parser=self.parser):
                yield i

    async def iterchunks(self, wrap=False):
        async for chunk in self._gen:
            if wrap:
                yield InfluxDBResult(chunk, parser=self.parser, query=self.query)
            else:
                yield chunk


def iterpoints(resp: dict, parser: Optional[Callable] = None) -> Generator:
    """Iterates a response JSON yielding data point by point.

    Can be used with both regular and chunked responses.
    By default, returns just a plain list of values representing each point,
    without column names, or other metadata.

    In case a specific format is needed, an optional ``parser`` argument can be passed.
    ``parser`` is a function that takes raw value list for each data point and a
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
    return (x for x in [])
