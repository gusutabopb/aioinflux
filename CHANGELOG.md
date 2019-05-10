# Changelog


## [0.8.0] - 2019-05-10

This is version is backwards compatible with v0.7.x

### Added
- Add dataframe support for chunked queries (e3c2a0b)


## [0.7.1] - 2019-04-11

This is version is backwards compatible with v0.7.0

### Fixed
- Don't cache error responses (be7b87c)

### Docs
- Minor wording changes

### Internal
- Minor internal changes 



## [0.7.0] - 2019-03-22

This is version is mostly backwards compatible with v0.6.x 
(w/ the exception of query patterns functionality)

## Added
- Redis-based caching functionality. See the 
  [docs](https://aioinflux.readthedocs.io/en/latest/usage.html#caching-query-results) for details.
- Timeout functionality (#21 by @SuminAndrew)

### Changed
- Move `ClientSession` creation logic outside `__init__`. 
It is now easier to used advanced ``aiohttp.ClientSession`` options.
See the [docs](https://aioinflux.readthedocs.io/en/latest/usage.html#other-aiohttp-functionality) for details. 

### Removed
- Query patterns functionality

### Internal
- Refactor test suite
- Various other internal changes 


## [0.6.1] - 2019-02-01

This is version is backwards compatible with v0.6.0

### Fixed
- Type annotation error in Python 3.6 (febfe47)
- Suppress `The object should be created from async function` warning from aiohttp 3.5 (da950e9) 


## [0.6.0] - 2019-02-01

### Added
- Support serializing NaN integers in pandas 0.24+ 
  (See [blog post](https://pandas-dev.github.io/pandas-blog/pandas-extension-arrays.html)) (1c55217)
- Support for using `namedtuple` with `iterpoints` (bd93c53)

### Changed
- **[BREAKING]** Changed signature of `parser` argument of `iterpoints`  
  from `(x, meta)` to `(*x, meta)` (bd93c53)

### Removed
- **[BREAKING]** Removed iterable mode and `InfluxDBResult` / `InfluxDBChunkedResult`.
  Use `iterpoints` instead. (592c5ed)
- Deprecated `set_query_pattern` (1d36b07)

### Docs
- Various improvements (8c6cbd3, ce46596, b7db169, ba3edae)


## [0.5.1] - 2019-01-21

This is version is backwards compatible with v0.5.0

### Fixed
- Fix type annotations
- Fix internal API inconsistencies

### Docs
- Complete API section
- Add proper Sphinx links
- Update/fix various sections


## [0.5.0] - 2019-01-17

### Changed
- [BREAKING] Removed `DataPoint` functionality in favor of simpler and more
 flexible `@lineprotocol` decorator. See the 
  [docs](https://aioinflux.readthedocs.io/en/latest/usage.html#writing-user-defined-class-objects) for details.

### Docs
- Added detailed `@lineprotocol` usage 
 
 
## [0.4.1] - 2018-11-22

### Fixed
- Fixed bug when doing multi-statement queries when using `dataframe` mode

### Docs
- Added note regarding handling of multi-statement/multi-series queries when using `dataframe` mode

 
## [0.4.0] - 2018-10-22

### Added
- Added ability to write `datapoint` objects. See the 
  [docs](https://aioinflux.readthedocs.io/en/latest/usage.html#writing-datapoint-objects) for details.
- Added `bytes` output format. This is to facilitate the addition of a caching layer on top of InfluxDB. (cb4e3d1)

### Changed
- Change `write` method signature to match the `/write` endpoint docs 
    - Allow writing to non-default retention policy (#14)
    - (`precision` is not fully implemented yet)
- Renamed `raw` output format to `json`. Most users should be unaffected by this. (cb4e3d1)

### Fixed
- Improved docs

### Internal
- Refactored serialization/parsing functionality into a subpackage
- Fix test warnings (2e42d50)

 

## [0.3.4] - 2018-09-03
- Fixed `output='dataframe'` parsing bug (#15)
- Removed tag column -> categorical dtype conversion functionality
- Moved documentation to Read The Docs
- Added two query patterns (671013b)
- Added this CHANGELOG


## [0.3.3] - 2018-06-23
- Python 3.7 support
- Sphinx-based documentation hosted at Read the Docs
- Minor dataframe serialization debugging (364190fa)

## [0.3.2] - 2018-05-03
- Fix parsing bug for string ending in a backslash (db8846e)
- Add InfluxDBWriteError exception class (d8d0a01)
- Make InfluxDBClient.db attribute optional (039e088)

## [0.3.1] - 2018-04-29
- Fix bug where timezone-unaware datetime input was assumed to be in local time (#11 / a8c81b7)
- Minor improvement in dataframe parsing (1e33b92)

## [0.3.0] - 2018-04-24
### Highlights:

- Drop Pandas/Numpy requirement (#9)
- Improved iteration support (816a722)
- - Implement tag/key value caching (9a65787)
- Improve dataframe serialization
  - Speed improvements (ddc9ecc)
  - Memory usage improvements (a2b58bd)
  - Disable concatenating of dataframes of the same measurement when grouping by tag (331a0c9)
  - Queries now return tag columns with `pd.Categorical` dtype (efdea98)
  - Writes now automatically identify `pd.Categorical` dtype columns as tag columns (ddc9ecc)

### API changes:

- `mode` attribute was "split" into `mode` and `output`.
 Default behavior remains the same (async / raw).
- Iteration is now made easier through the `iterable` mode 
 and `InfluxDBResult` and `InfluxDBChunkedResult` classes


## [0.2.0] - 2018-03-20

### Highlights

- Documentation is now complete
- Improved iteration support (via `iter_resp`) (cfffbf5)
- Allow users to add custom query patterns
- Add support for positional arguments in query patterns
- Reimplement `__del__` (40d0a69 / #7)
- Improve/debug dataframe parsing (7beeb53 / 96d78a4)
- Improve write error message (7972946) (by @miracle2k)

### API changes:
- Rename `AsyncInfluxDBClient` to `InfluxDBClient` (54d98c9)
- Change return format of chunked responses (related: cfffbf5 / #6)
- Make some `__init__` arguments keyword-only (5d2edf6)


## [0.1.2] - 2018-02-28

- Add `__aenter__`/`__aexit__` support (5736446) (by @Kargathia)
- Add HTTPS URL support (49b8e89) (by @miracle2k)
- Add Unix socket support (8a8b069) (by @carlos-jenkins)
- Fix bug where tags where not being added to DataFrames when querying (a9f1d82)

## [0.1.1] - 2017-11-10

- Add error handling for chunked responses (db93c20)
- Fix DataFrame tag parsing bug (aa02faa)
- Fix boolean field parsing bug (4c2bff9)
- Increase test coverage

## [0.1.0] - 2017-10-04
Initial release.  
The API is relatively stable but there might be some bugs here and there.  
Discretion advised when using in production.  

