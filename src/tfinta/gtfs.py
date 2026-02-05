# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""GTFS: Loading, parsing, etc.

See: https://gtfs.org/documentation/schedule/reference/
"""

from __future__ import annotations

import contextlib
import csv
import dataclasses
import datetime
import functools
import io
import logging
import os.path
import pathlib
import time
import types
import urllib.request
import zipfile
import zoneinfo
from collections import abc
from typing import IO, Any, cast, get_args, get_type_hints

import click
import prettytable
import typer
from rich import console as rich_console
from transcrypto.cli import clibase
from transcrypto.core import key
from transcrypto.utils import human
from transcrypto.utils import logging as tc_logging

from . import __version__
from . import gtfs_data_model as dm
from . import tfinta_base as base

# TODO: use less of os.path.join and more of pathlib.Path for path manipulations


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class GTFSConfig(clibase.CLIConfig):
  """CLI global context, storing the configuration."""


# defaults
_DEFAULT_DAYS_FRESHNESS = 10
_DAYS_CACHE_FRESHNESS = 1
_SECONDS_IN_DAY = 60 * 60 * 24
DAYS_OLD: abc.Callable[[float], float] = lambda t: (time.time() - t) / _SECONDS_IN_DAY
DEFAULT_DATA_DIR: str = base.MODULE_PRIVATE_DIR(__file__, '.tfinta-data')
_DB_FILE_NAME = 'transit.db'

# cache sizes (in entries)
_SMALL_CACHE = 1 << 10  # 1024
_MEDIUM_CACHE = 1 << 14  # 16384
_LARGE_CACHE = 1 << 16  # 65536

# type maps for efficiency and memory (so we don't build countless enum objects)
_LOCATION_TYPE_MAP: dict[int, dm.LocationType] = {e.value: e for e in dm.LocationType}
_STOP_POINT_TYPE_MAP: dict[int, dm.StopPointType] = {e.value: e for e in dm.StopPointType}
_ROUTE_TYPE_MAP: dict[int, dm.RouteType] = {e.value: e for e in dm.RouteType}


class Error(base.Error):
  """GTFS exception."""


class ParseError(Error):
  """Exception parsing a GTFS file."""


class ParseImplementationError(ParseError):
  """Exception parsing a GTFS row."""


class ParseIdenticalVersionError(ParseError):
  """Exception parsing a GTFS row."""


class RowError(ParseError):
  """Exception parsing a GTFS row."""


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class _TableLocation:
  """GTFS table coordinates (just for parsing use for now)."""

  operator: str  # GTFS Operator, from CSV Official Sources (required)
  link: str  # GTFS ZIP file URL location               (required)
  file_name: str  # file name (ex: 'feed_info.txt')          (required)


# useful aliases
type _GTFSRowHandler[T: dm.BaseCVSRowType] = abc.Callable[[_TableLocation, int, T], None]


class GTFS:
  """GTFS database."""

  def __init__(self, db_dir_path: str, /) -> None:
    """Construct.

    Args:
      db_dir_path: Path to directory in which to save DB 'transit.db'


    Raises:
      Error: on invalid directory path

    """
    # save the dir/path, create directory if needed
    self._dir_path: str = db_dir_path.strip()
    if not self._dir_path:
      raise Error('DB dir path cannot be empty')
    if not pathlib.Path(self._dir_path).is_dir():
      pathlib.Path(self._dir_path).mkdir()
      logging.info('Created data directory: %s', self._dir_path)
    self._db_path: str = os.path.join(self._dir_path, _DB_FILE_NAME)  # noqa: PTH118
    self._db: dm.GTFSData
    self._changed = False
    # load DB, or create if new
    if pathlib.Path(self._db_path).exists():
      # DB exists: load
      self._db = cast('dm.GTFSData', key.DeSerialize(file_path=self._db_path))
      logging.info(f'Loaded DB from {self._db_path!r}')
      logging.info('DB freshness: %s', base.STD_TIME_STRING(self._db.tm))
    else:
      # DB does not exist: create empty
      self._db = dm.GTFSData(  # empty DB
        tm=0.0,
        files=dm.OfficialFiles(tm=0.0, files={}),
        agencies={},
        calendar={},
        shapes={},
        stops={},
      )
      self.Save(force=True)
    # create file handlers structure
    self._file_handlers: dict[
      str,
      tuple[_GTFSRowHandler[Any], type[dm.BaseCVSRowType], dict[str, tuple[type, bool]], set[str]],
    ] = {
      # {file_name: (handler, TypedDict_row_definition,
      #              {field: (type, required?)}, {required1, required2, ...})}
      'feed_info.txt': (self._HandleFeedInfoRow, dm.ExpectedFeedInfoCSVRowType, {}, set()),
      'agency.txt': (self._HandleAgencyRow, dm.ExpectedAgencyCSVRowType, {}, set()),
      'calendar.txt': (self._HandleCalendarRow, dm.ExpectedCalendarCSVRowType, {}, set()),
      'calendar_dates.txt': (
        self._HandleCalendarDatesRow,
        dm.ExpectedCalendarDatesCSVRowType,
        {},
        set(),
      ),
      'routes.txt': (self._HandleRoutesRow, dm.ExpectedRoutesCSVRowType, {}, set()),
      'shapes.txt': (self._HandleShapesRow, dm.ExpectedShapesCSVRowType, {}, set()),
      'trips.txt': (self._HandleTripsRow, dm.ExpectedTripsCSVRowType, {}, set()),
      'stops.txt': (self._HandleStopsRow, dm.ExpectedStopsCSVRowType, {}, set()),
      'stop_times.txt': (self._HandleStopTimesRow, dm.ExpectedStopTimesCSVRowType, {}, set()),
    }
    # fill in types, derived from the _Expected*CSVRowType TypedDicts
    for file_name, (_, expected, fields, required) in self._file_handlers.items():
      for field, type_descriptor in get_type_hints(expected).items():
        if type_descriptor in {str, int, float, bool}:
          # no optional, so field is required
          required.add(field)
          fields[field] = (type_descriptor, True)
        else:
          # it is optional and something else, so find out which
          field_args = get_args(type_descriptor)
          if len(field_args) != 2:  # noqa: PLR2004
            raise Error(f'incorrect type len {file_name}/{field}: {field_args!r}')
          field_type = field_args[0] if field_args[1] == types.NoneType else field_args[1]
          if field_type not in {str, int, float, bool}:
            raise Error(f'incorrect type {file_name}/{field}: {field_args!r}')
          fields[field] = (field_type, False)

  def Save(self, /, *, force: bool = False) -> None:
    """Save DB to file.

    Args:
      force: (default False) Saves even if no changes to data were detected

    """
    if force or self._changed:
      # (compressing is responsible for ~95% of save time)
      self._db.tm = time.time()
      key.Serialize(self._db, file_path=self._db_path)
      self._changed = False
      logging.info(f'Saved DB to {self._db_path!r}')

  # TODO: refactor to not depend on self, as this may lead to memory leaks if not careful
  @functools.lru_cache(  # noqa: B019
    maxsize=_MEDIUM_CACHE
  )  # remember to update self._InvalidateCaches()
  def FindRoute(self, route_id: str, /) -> dm.Agency | None:
    """Find route by finding its Agency.

    Args:
      route_id: Route ID to search for

    Returns:
      Agency containing the route, or None if not found

    """
    for agency in self._db.agencies.values():
      if route_id in agency.routes:
        return agency
    return None

  @functools.lru_cache(  # noqa: B019
    maxsize=_LARGE_CACHE
  )  # remember to update self._InvalidateCaches()
  def FindTrip(self, trip_id: str, /) -> tuple[dm.Agency | None, dm.Route | None, dm.Trip | None]:
    """Find trip by finding its Agency & Route.

    Args:
      trip_id: Trip ID to search for

    Returns:
      Tuple of (Agency, Route, Trip) or (None, None, None) if not found

    """
    for agency in self._db.agencies.values():
      for route in agency.routes.values():
        if trip_id in route.trips:
          return (agency, route, route.trips[trip_id])
    return (None, None, None)

  @functools.lru_cache(  # noqa: B019
    maxsize=_SMALL_CACHE
  )  # remember to update self._InvalidateCaches()
  def StopName(self, stop_id: str, /) -> tuple[str | None, str | None, str | None]:
    """Get (code, name, description) for a Stop object of given ID.

    Args:
      stop_id: Stop ID to look up

    Returns:
      Tuple of (code, name, description) or (None, None, None) if not found

    """
    if stop_id not in self._db.stops:
      return (None, None, None)
    stop: dm.BaseStop = self._db.stops[stop_id]
    return (stop.code, stop.name, stop.description)

  @functools.lru_cache(  # noqa: B019
    maxsize=_SMALL_CACHE
  )  # remember to update self._InvalidateCaches()
  def StopNameTranslator(self, stop_id: str, /) -> str:
    """Translate a stop ID into a name.

    Args:
      stop_id: Stop ID to translate

    Returns:
      Stop name

    Raises:
      Error: If stop ID is not found

    """
    name: str | None = self.StopName(stop_id)[1]
    if not name:
      raise Error(f'Invalid stop code found: {stop_id}')
    return name

  @functools.lru_cache(  # noqa: B019
    maxsize=_SMALL_CACHE
  )  # remember to update self._InvalidateCaches()
  def StopIDFromNameFragmentOrID(self, stop_name_or_id: str, /) -> str:
    """Search for stop_id based on either an ID (verifies exists) or stop name.

    If searching by name, will search for a case-insensitive partial match that is UNIQUE.

    Args:
      stop_name_or_id: either a stop_id (case-sensitive) or a
          partial station name match (case-insensitive)

    Returns:
      stop_id if found unique match; None otherwise

    Raises:
      Error: more than one match or no match

    """
    # test empty case
    stop_name_or_id = stop_name_or_id.strip()
    if not stop_name_or_id:
      raise Error('empty station ID/name')
    # test input as stop_id
    if stop_name_or_id in self._db.stops:
      return stop_name_or_id  # found, so just use it...
    # this will be a name-based search, which will be case-insensitive
    stop_name: str = stop_name_or_id.lower()
    matches: set[str] = set()
    for stop_id, stop in self._db.stops.items():
      if stop_name in stop.name.lower():
        matches.add(stop_id)
    # check what sort of results we got
    if not matches:
      # did not find anything
      raise Error(f'No matches for station {stop_name_or_id!r}')
    if len(matches) > 1:
      # cannot decide between many options
      raise Error(
        f'Station name {stop_name_or_id!r} matches stations: '
        f'{", ".join(f"{s}/{self._db.stops[s].name}" for s in sorted(matches))} '
        '--- Use ID or be more specific'
      )
    # exactly one real match, so that is the one
    return matches.pop()

  def _InvalidateCaches(self) -> None:
    """Clear all caches."""
    for method in (
      # list cache methods here
      self.FindRoute,
      self.FindTrip,
      self.StopName,
      self.StopNameTranslator,
      self.StopIDFromNameFragmentOrID,
    ):
      method.cache_clear()

  def ServicesForDay(self, day: datetime.date, /) -> set[int]:
    """Return set[int] of services active (available/running/operating) on this day.

    Returns:
        Set of service IDs active on this day

    """
    weekday: int = day.weekday()
    services: set[int] = set()
    # go over available services
    for service, calendar in self._db.calendar.items():
      if calendar.days.start <= day <= calendar.days.end:
        # day is in range for this service; check day of week and the exceptions
        weekday_service: bool = calendar.week[weekday]
        service_exception: bool | None = calendar.exceptions.get(day)
        has_service: bool = service_exception if service_exception is not None else weekday_service
        if has_service:
          services.add(service)
    return services

  def FindAgencyRoute(
    self,
    agency_name: str,
    route_type: dm.RouteType,
    short_name: str,
    /,
    *,
    long_name: str | None = None,
  ) -> tuple[dm.Agency | None, dm.Route | None]:
    """Find a route in an agency, by name.

    Args:
      agency_name: Agency name
      route_type: dm.RouteType
      short_name: Route short name
      long_name: (default None) If given, will also match long name

    Returns:
      (Agency, Route) or (None, None) if not found

    """
    agency_name = agency_name.strip()
    short_name = short_name.strip()
    long_name = long_name.strip() if long_name else None
    # find Agency
    for agency in self._db.agencies.values():
      if agency.name.lower() == agency_name.lower():
        break
    else:
      return (None, None)
    # find Route
    for route in agency.routes.values():
      if route.route_type == route_type and route.short_name == short_name:
        if long_name:
          if route.long_name == long_name:
            return (agency, route)
        else:
          return (agency, route)
    return (agency, None)

  def LoadData(
    self,
    operator: str,
    link: str,
    /,
    *,
    freshness: int = _DEFAULT_DAYS_FRESHNESS,
    allow_unknown_file: bool = True,
    allow_unknown_field: bool = False,
    force_replace: bool = False,
    override: str | None = None,
  ) -> None:
    """Download and parse GTFS data.

    Args:
      operator: Operator for GTFS file
      link: URL for GTFS file
      freshness: (default 10) Number of days before data is not fresh anymore and
          has to be reloaded from source
      allow_unknown_file: (default True) If False will raise on unknown GTFS file
      allow_unknown_field: (default False) If False will raise on unknown field in file
      force_replace: (default False) If True will parse a repeated version of the ZIP file
      override: (default None) If given, this ZIP file path will override the download

    """
    # first load the list of GTFS, if needed
    if (age := DAYS_OLD(self._db.files.tm)) > freshness:
      logging.info('Loading CSV sources (%0.2f days old)', age)
      self._LoadCSVSources()
    else:
      logging.info('CSV sources are fresh (%0.2f days old) - SKIP', age)
    # load GTFS data we are interested in
    if override:
      logging.info('OVERRIDE GTFS source: %s', override)
      self._LoadGTFSSource(
        operator,
        link,
        allow_unknown_file=allow_unknown_file,
        allow_unknown_field=allow_unknown_field,
        force_replace=force_replace,
        override=override,
      )
    if (
      not force_replace
      and operator in self._db.files.files
      and link in self._db.files.files[operator]
      and (file_metadata := self._db.files.files[operator][link]) is not None
      and (age := DAYS_OLD(file_metadata.tm)) <= freshness
    ):
      logging.info('GTFS sources are fresh (%0.2f days old) - SKIP', age)
    else:
      logging.info('Parsing GTFS ZIP source (%0.2f days old)', age)
      self._LoadGTFSSource(
        operator,
        link,
        allow_unknown_file=allow_unknown_file,
        allow_unknown_field=allow_unknown_field,
        force_replace=force_replace,
        override=None,
      )

  def _LoadCSVSources(self) -> None:
    """Load GTFS official sources from CSV.

    Raises:
      Error: on invalid CSV format or missing operators

    """
    # get the file and parse it
    new_files: dict[str, dict[str, dm.FileMetadata | None]] = {}
    with urllib.request.urlopen(dm.OFFICIAL_GTFS_CSV) as gtfs_csv:  # noqa: S310
      text_csv = io.TextIOWrapper(gtfs_csv, encoding='utf-8')
      for i, row in enumerate(csv.reader(text_csv)):
        if len(row) != 2:  # noqa: PLR2004
          raise Error(f'Unexpected row in GTFS CSV list: {row!r}')
        if not i:
          if row != ['Operator', 'Link']:
            raise Error(f'Unexpected start of GTFS CSV list: {row!r}')
          continue  # first row is as expected: skip it
        # we have a row
        new_files.setdefault(row[0], {})[row[1]] = None
    # check the operators we care about are included!
    for operator in dm.KNOWN_OPERATORS:
      if operator not in new_files:
        raise Error(f'Operator {operator!r} not in loaded CSV!')
    # we have the file loaded
    self._db.files.files = new_files
    self._db.files.tm = time.time()
    self._changed = True
    logging.info(
      'Loaded GTFS official sources with %d operators and %d links',
      len(new_files),
      sum(len(urls) for urls in new_files.values()),
    )

  @contextlib.contextmanager
  def _ParsingSession(self) -> abc.Generator[None, Any, None]:
    """Context manager that invalidates caches before/after a parsing block."""
    self._InvalidateCaches()  # fresh start
    try:
      yield  # run parsing body
    except Exception:
      # ensure caches are clean even on failure
      self._InvalidateCaches()
      raise  # propagate the original error
    finally:
      # success path - still clear once more for safety
      self.Save()
      self._InvalidateCaches()

  def _LoadGTFSSource(  # noqa: C901
    self,
    operator: str,
    link: str,
    /,
    *,
    allow_unknown_file: bool = True,
    allow_unknown_field: bool = False,
    force_replace: bool = False,
    override: str | None = None,
  ) -> None:
    """Load a single GTFS ZIP file and parse all inner data files.

    Args:
      operator: Operator for GTFS file
      link: URL for GTFS file
      allow_unknown_file: (default True) If False will raise on unknown GTFS file
      allow_unknown_field: (default False) If False will raise on unknown field in file
      force_replace: (default False) If True will parse a repeated version of the ZIP file
      override: (default None) If given, this ZIP file path will override the download

    Raises:
      Error: on invalid operator or URL
      ParseError: missing files or fields

    """
    # check that we are asking for a valid and known source
    operator, link = operator.strip(), link.strip()
    if not operator or operator not in self._db.files.files:
      raise Error(f'invalid operator {operator!r}')
    operator_files: dict[str, dm.FileMetadata | None] = self._db.files.files[operator]
    if not link or link not in operator_files:
      raise Error(f'invalid URL {link!r}')
    # load ZIP from URL
    done_files: set[str] = set()
    clean_file_name: str
    cache_file_name: str = link.replace('://', '__').replace('/', '_')
    cache_file_path: str = os.path.join(self._dir_path, cache_file_name)  # noqa: PTH118
    save_cache_file: bool
    url_opener: abc.Callable[[], IO[bytes]]
    with self._ParsingSession():
      if override:
        if not pathlib.Path(override).exists():
          raise Error(f'Override file does not exist: {override!r}')
        url_opener = lambda: pathlib.Path(override).open('rb')  # noqa: SIM115
        save_cache_file = False
      elif (
        not force_replace
        and pathlib.Path(cache_file_path).exists()
        and (age := DAYS_OLD(pathlib.Path(cache_file_path).stat().st_mtime))
        <= _DAYS_CACHE_FRESHNESS
      ):
        # we will used the cached ZIP
        logging.warning('Loading from %0.2f days old cache on disk! (use -r to override)', age)
        url_opener = lambda: pathlib.Path(cache_file_path).open('rb')  # noqa: SIM115
        save_cache_file = False
      else:
        # we will re-download from the URL
        url_opener = lambda: urllib.request.urlopen(link)  # noqa: S310
        save_cache_file = True
      # open from whatever source
      with url_opener() as gtfs_zip:
        # get ZIP binary content, and if we got from URL save to cache
        gtfs_zip_bytes: bytes = gtfs_zip.read()
        logging.info(
          'Loading %r data, %s, from %r%s',
          operator,
          human.HumanizedBytes(len(gtfs_zip_bytes)),
          link if save_cache_file else cache_file_name,
          ' => SAVING to cache' if save_cache_file else '',
        )
        if save_cache_file:
          pathlib.Path(cache_file_path).write_bytes(gtfs_zip_bytes)
        # extract files from ZIP
        for file_name, file_data in _UnzipFiles(io.BytesIO(gtfs_zip_bytes)):
          clean_file_name = file_name.strip()
          location = _TableLocation(operator=operator, link=link, file_name=clean_file_name)
          try:
            self._LoadGTFSFile(
              location,
              file_data,
              allow_unknown_file=allow_unknown_file,
              allow_unknown_field=allow_unknown_field,
            )
          except ParseIdenticalVersionError as err:
            if force_replace:
              logging.warning('Replacing existing data: %s', err)
              continue
            logging.warning('Version already known (will SKIP): %s', err)
            return
          finally:
            done_files.add(clean_file_name)
      # finished loading the files, check that we loaded all required files
      if missing_files := dm.REQUIRED_FILES - done_files:
        raise ParseError(f'Missing required files: {operator} {missing_files!r}')
      self._changed = True

  def _LoadGTFSFile(  # noqa: C901, PLR0912
    self,
    location: _TableLocation,
    file_data: bytes,
    /,
    *,
    allow_unknown_file: bool,
    allow_unknown_field: bool,
  ) -> None:
    """Load a single txt (actually CSV) file and parse all fields, sending rows to handlers.

    Args:
      location: (operator, link, file_name)
      file_data: File bytes
      allow_unknown_file: If False will raise on unknown GTFS file
      allow_unknown_field: If False will raise on unknown field in file

    Raises:
      Error: on invalid file data
      ParseError: missing fields
      ParseImplementationError: unknown file or field (if "allow" is False)

    """
    # check if we know how to process this file
    file_name: str = location.file_name
    if file_name not in self._file_handlers or not file_data:
      message: str = (
        f'Unsupported GTFS file: {file_name or "<empty>"} ({human.HumanizedBytes(len(file_data))})'
      )
      if allow_unknown_file:
        logging.warning(message)
        return
      raise ParseImplementationError(message)
    # supported type of GTFS file, so process the data into the DB
    logging.info('Processing: %s (%s)', file_name, human.HumanizedBytes(len(file_data)))
    # get fields data, and process CSV with a dict reader
    file_handler, _, field_types, required_fields = self._file_handlers[file_name]
    i: int = 0
    for i, row in enumerate(
      csv.DictReader(io.TextIOWrapper(io.BytesIO(file_data), encoding='utf-8'))
    ):
      parsed_row: dm.ExpectedRowData = {}
      clean_field_value: str | None
      # process field-by-field
      for field_name, field_value in row.items():
        # strip and nullify the empty value
        clean_field_value = field_value.strip() or None
        if field_name in field_types:
          # known/expected field
          field_type, field_required = field_types[field_name]
          if clean_field_value is None:
            # field is empty
            if field_required:
              raise ParseError(f'Empty required field: {file_name}/{i} {field_name!r}: {row}')
            parsed_row[field_name] = None
          # field has a value
          elif field_type is str:
            parsed_row[field_name] = clean_field_value  # vanilla string
          elif field_type is bool:
            try:
              parsed_row[field_name] = base.BOOL_FIELD[clean_field_value]  # convert to bool '0'/'1'
            except KeyError as err:
              raise ParseError(
                f'invalid bool value {file_name}/{i}/{field_name}: {clean_field_value!r}'
              ) from err
          elif field_type in {int, float}:
            try:
              parsed_row[field_name] = field_type(clean_field_value)  # convert int/float
            except ValueError as err:
              raise ParseError(
                f'invalid int/float value {file_name}/{i}/{field_name}: {clean_field_value!r}'
              ) from err
          else:
            raise Error(f'invalid field type {file_name}/{i}/{field_name!r}: {field_type!r}')
        else:
          # unknown field, check if we message/raise only in first row
          if not i:
            message = f'Extra fields found: {file_name}/0 {field_name!r}'
            if allow_unknown_field:
              logging.warning(message)
            else:
              raise ParseImplementationError(message)
          # if allowed, then place as nullable string
          parsed_row[field_name] = clean_field_value
      # we have a row, check for missing required fields
      parsed_row_fields: set[str] = set(parsed_row.keys())
      if missing_required := required_fields - parsed_row_fields:
        raise ParseError(f'Missing required fields: {file_name}/{i} {missing_required!r}: {row}')
      # add known fields that are missing (with None as value)
      for field in set(field_types.keys()) - parsed_row_fields:
        parsed_row[field] = None
      # done: send to row handler
      file_handler(location, i, parsed_row)
    # finished
    self._changed = True
    logging.info('Read %d records from %s', i + 1, file_name)

  ##################################################################################################
  # GTFS ROW HANDLERS
  ##################################################################################################

  # HANDLER TEMPLATE (copy and uncomment)
  # def _HandleTABLENAMERow(
  #     self, location: _TableLocation, count: int, row: dm.ExpectedFILENAMECSVRowType, /) -> None:
  #   """Handler: "FILENAME.txt" DESCRIPTION.
  #
  #   Args:
  #     location: _TableLocation info on current GTFS table
  #     count: row count, starting on 1
  #     row: the row as a dict {field_name: Optional[field_data]}
  #
  #   Raises:
  #     RowError: error parsing this record
  #   """

  def _HandleFeedInfoRow(
    self, location: _TableLocation, count: int, row: dm.ExpectedFeedInfoCSVRowType, /
  ) -> None:
    """Handle: "feed_info.txt" Information on the GTFS ZIP file being processed.

    (no primary key)

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
      ParseIdenticalVersionError: version is already known/parsed

    """
    # there can be only one!
    if count != 0:
      raise RowError(
        f'feed_info.txt table ({location}) is only supported to have 1 row (got {count}): {row}'
      )
    # check against current version (and log)
    tm: float = time.time()
    current_data: dm.FileMetadata | None = self._db.files.files[location.operator][location.link]
    start: datetime.date = base.DATE_OBJ_GTFS(row['feed_start_date'])
    end: datetime.date = base.DATE_OBJ_GTFS(row['feed_end_date'])
    if current_data is None:
      logging.info(
        'Loading version %r @ %s for %s/%s',
        row['feed_version'],
        base.STD_TIME_STRING(tm),
        location.operator,
        location.link,
      )
    else:
      if (
        row['feed_version'] == current_data.version
        and row['feed_publisher_name'] == current_data.publisher
        and row['feed_lang'] == current_data.language
        and start == current_data.days.start
        and end == current_data.days.end
      ):
        # same version of the data!
        # note that since we `raise` we don't update the timestamp, so the timestamp
        # is the time we first processed this version of the ZIP file
        raise ParseIdenticalVersionError(
          f'{row["feed_version"]} @ {base.STD_TIME_STRING(current_data.tm)} '
          f'{location.operator} / {location.link}'
        )
      logging.info(
        'Updating version %r @ %s -> %r @ %s for %s/%s',
        current_data.version,
        base.STD_TIME_STRING(current_data.tm),
        row['feed_version'],
        base.STD_TIME_STRING(tm),
        location.operator,
        location.link,
      )
    # update
    self._db.files.files[location.operator][location.link] = dm.FileMetadata(
      tm=tm,
      publisher=row['feed_publisher_name'],
      url=row['feed_publisher_url'],
      language=row['feed_lang'],
      days=base.DaysRange(start=start, end=end),
      version=row['feed_version'],
      email=row['feed_contact_email'],
    )

  def _HandleAgencyRow(
    self,
    location: _TableLocation,  # noqa: ARG002
    count: int,  # noqa: ARG002
    row: dm.ExpectedAgencyCSVRowType,
    /,
  ) -> None:
    """Handle: "agency.txt" Transit agencies.

    pk: agency_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    """
    # update
    self._db.agencies[row['agency_id']] = dm.Agency(
      id=row['agency_id'],
      name=row['agency_name'],
      url=row['agency_url'],
      zone=zoneinfo.ZoneInfo(row['agency_timezone']),
      routes={},
    )

  def _HandleCalendarRow(
    self,
    location: _TableLocation,  # noqa: ARG002
    count: int,  # noqa: ARG002
    row: dm.ExpectedCalendarCSVRowType,
    /,
  ) -> None:
    """Handle: "calendar.txt" Service dates specified using a weekly schedule & start/end dates.

    pk: service_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    """
    self._db.calendar[row['service_id']] = dm.CalendarService(
      id=row['service_id'],
      week=(
        row['monday'],
        row['tuesday'],
        row['wednesday'],
        row['thursday'],
        row['friday'],
        row['saturday'],
        row['sunday'],
      ),
      days=base.DaysRange(
        start=base.DATE_OBJ_GTFS(row['start_date']), end=base.DATE_OBJ_GTFS(row['end_date'])
      ),
      exceptions={},
    )

  def _HandleCalendarDatesRow(
    self,
    location: _TableLocation,  # noqa: ARG002
    count: int,  # noqa: ARG002
    row: dm.ExpectedCalendarDatesCSVRowType,
    /,
  ) -> None:
    """Handle: "calendar_dates.txt" Exceptions for the services defined in the calendar table.

    pk: (calendar/service_id, date) / ref: calendar/service_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    """
    self._db.calendar[row['service_id']].exceptions[base.DATE_OBJ_GTFS(row['date'])] = (
      row['exception_type'] == '1'
    )

  def _HandleRoutesRow(
    self,
    location: _TableLocation,  # noqa: ARG002
    count: int,  # noqa: ARG002
    row: dm.ExpectedRoutesCSVRowType,
    /,
  ) -> None:
    """Handle: "routes.txt" Routes: group of trips that are displayed to riders as a single service.

    pk: route_id / ref: agency/agency_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    """
    self._db.agencies[row['agency_id']].routes[row['route_id']] = dm.Route(
      id=row['route_id'],
      agency=row['agency_id'],
      short_name=row['route_short_name'],
      long_name=row['route_long_name'],
      route_type=_ROUTE_TYPE_MAP[row['route_type']],
      description=row['route_desc'],
      url=row['route_url'],
      color=row['route_color'],
      text_color=row['route_text_color'],
      trips={},
    )

  def _HandleShapesRow(
    self,
    location: _TableLocation,  # noqa: ARG002
    count: int,  # noqa: ARG002
    row: dm.ExpectedShapesCSVRowType,
    /,
  ) -> None:
    """Handle: "shapes.txt" Rules for mapping vehicle travel paths (aka. route alignments).

    pk: (shape_id, shape_pt_sequence)

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    """
    if row['shape_id'] not in self._db.shapes:
      self._db.shapes[row['shape_id']] = dm.Shape(id=row['shape_id'], points={})
    self._db.shapes[row['shape_id']].points[row['shape_pt_sequence']] = dm.ShapePoint(
      id=row['shape_id'],
      seq=row['shape_pt_sequence'],
      point=base.Point(latitude=row['shape_pt_lat'], longitude=row['shape_pt_lon']),
      distance=row['shape_dist_traveled'],
    )

  def _HandleTripsRow(
    self, location: _TableLocation, count: int, row: dm.ExpectedTripsCSVRowType, /
  ) -> None:
    """Handle: "trips.txt" Trips for each route.

    A trip is a sequence of two or more stops that occur during a specific time period.
    pk: trip_id / ref: routes.route_id, calendar.service_id, shapes.shape_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record

    """
    # check
    agency: dm.Agency | None = self.FindRoute(row['route_id'])
    if agency is None:
      raise RowError(f'agency in row was not found @{count} / {location}: {row}')
    # update
    self._db.agencies[agency.id].routes[row['route_id']].trips[row['trip_id']] = dm.Trip(
      id=row['trip_id'],
      route=row['route_id'],
      agency=agency.id,
      service=row['service_id'],
      shape=row['shape_id'],
      headsign=row['trip_headsign'],
      name=row['trip_short_name'],
      block=row['block_id'],
      direction=row['direction_id'],
      stops={},
    )

  def _HandleStopsRow(
    self, location: _TableLocation, count: int, row: dm.ExpectedStopsCSVRowType, /
  ) -> None:
    """Handle: "stops.txt" Stops where vehicles pick up or drop-off riders.

    Also defines stations and station entrances.
    pk: stop_id / self-ref: parent_station=stop/stop_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record

    """
    # get data, check
    location_type: dm.LocationType = (
      _LOCATION_TYPE_MAP[row['location_type']] if row['location_type'] else dm.LocationType.STOP
    )
    if row['parent_station'] and row['parent_station'] not in self._db.stops:
      #  the GTFS spec does not guarantee parents precede children, but for now we will enforce it
      raise RowError(f'parent_station in row was not found @{count} / {location}: {row}')
    # update
    self._db.stops[row['stop_id']] = dm.BaseStop(
      id=row['stop_id'],
      parent=row['parent_station'],
      code=row['stop_code'],
      name=row['stop_name'],
      point=base.Point(latitude=row['stop_lat'], longitude=row['stop_lon']),
      zone=row['zone_id'],
      description=row['stop_desc'],
      url=row['stop_url'],
      location=location_type,
    )

  def _HandleStopTimesRow(
    self, location: _TableLocation, count: int, row: dm.ExpectedStopTimesCSVRowType, /
  ) -> None:
    """Handle: "stop_times.txt" Times that a vehicle arrives/departs from stops for each trip.

    pk: (trips/trip_id, stop_sequence) / ref: stops/stop_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record

    """
    # get data, check if empty
    pickup: dm.StopPointType = (
      _STOP_POINT_TYPE_MAP[row['pickup_type']] if row['pickup_type'] else dm.StopPointType.REGULAR
    )
    dropoff: dm.StopPointType
    if row['drop_off_type'] is not None:
      dropoff = dm.StopPointType(row['drop_off_type'])  # new spelling
    elif row['dropoff_type'] is not None:
      dropoff = dm.StopPointType(row['dropoff_type'])  # old spelling
    else:
      dropoff = dm.StopPointType.REGULAR
    if row['stop_id'] not in self._db.stops:
      raise RowError(f'stop_id in row was not found @{count} / {location}: {row}')
    agency, route, trip = self.FindTrip(row['trip_id'])
    if not agency or not route or not trip:
      raise RowError(f'trip_id in row was not found @{count} / {location}: {row}')
    # update
    self._db.agencies[agency.id].routes[route.id].trips[row['trip_id']].stops[
      row['stop_sequence']
    ] = dm.Stop(
      id=row['trip_id'],
      seq=row['stop_sequence'],
      stop=row['stop_id'],
      agency=agency.id,
      route=route.id,
      scheduled=dm.ScheduleStop(
        times=base.DayRange(
          arrival=base.DayTime.FromHMS(row['arrival_time']),
          departure=base.DayTime.FromHMS(row['departure_time']),
        ),
        timepoint=row['timepoint'],
      ),
      headsign=row['stop_headsign'],
      pickup=pickup,
      dropoff=dropoff,
    )

  ##################################################################################################
  # GTFS PRETTY PRINTS
  ##################################################################################################

  def PrettyPrintBasics(self) -> abc.Generator[str, None, None]:
    """Generate a pretty version of basic DB data: Versions, agencies routes.

    Yields:
        Lines of pretty-printed data

    """
    n_items: int = len(self._db.agencies)
    for i, agency_id in enumerate(sorted(self._db.agencies)):
      agency: dm.Agency = self._db.agencies[agency_id]
      yield f'[magenta]Agency [bold]{agency.name} ({agency.id})[/]'
      yield f'  {agency.url} ({agency.zone})'
      yield ''
      table = prettytable.PrettyTable(
        [
          '[bold cyan]Route[/]',
          '[bold cyan]Name[/]',
          '[bold cyan]Long Name[/]',
          '[bold cyan]Type[/]',
          '[bold cyan]Desc.[/]',
          '[bold cyan]URL[/]',
          '[bold cyan]Color[/]',
          '[bold cyan]Text[/]',
          '[bold cyan]# Trips[/]',
        ]
      )
      for route_id in sorted(agency.routes):
        route: dm.Route = agency.routes[route_id]
        table.add_row(
          [
            f'[bold cyan]{route.id}[/]',
            f'[bold yellow]{route.short_name}[/]',
            f'[bold yellow]{route.long_name}[/]',
            f'[bold]{route.route_type.name}[/]',
            f'[bold]{route.description or base.NULL_TEXT}[/]',
            f'[bold]{route.url or base.NULL_TEXT}[/]',
            f'[bold]{route.color or base.NULL_TEXT}[/]',
            f'[bold]{route.text_color or base.NULL_TEXT}[/]',
            f'[bold]{len(route.trips)}[/]',
          ]
        )
      yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]
      if i < n_items - 1:
        yield ''
        yield '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        yield ''
    yield ''
    yield (f'[bold magenta]Files @ {base.STD_TIME_STRING(self._db.files.tm)}[/]')
    yield ''
    table = prettytable.PrettyTable(['[bold cyan]Agency[/]', '[bold cyan]URLs / Data[/]'])
    for agency_name in sorted(self._db.files.files):
      urls = self._db.files.files[agency_name]
      for url in sorted(urls):
        meta: dm.FileMetadata | None = urls[url]
        table.add_row(
          [
            f'[bold cyan]{agency_name}[/]',
            f'[bold]{url}[/]',
          ]
        )
        if meta:
          table.add_row(
            [
              '',
              (
                f'Version: [bold yellow]{meta.version}[/]\n'
                f'Last load: [bold yellow]{base.STD_TIME_STRING(meta.tm)}[/]\n'
                f'Publisher: [bold]{meta.publisher or base.NULL_TEXT}[/]\n'
                f'URL: [bold]{meta.url or base.NULL_TEXT}[/]\n'
                f'Language: [bold]{meta.language or base.NULL_TEXT}[/]\n'
                f'Days range: [bold yellow]{base.PRETTY_DATE(meta.days.start)} -'
                f' {base.PRETTY_DATE(meta.days.end)}[/]\n'
                f'Mail: [bold]{meta.email or base.NULL_TEXT}[/]'
              ),
            ]
          )
    yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]

  def PrettyPrintCalendar(
    self, /, *, filter_to: set[int] | None = None
  ) -> abc.Generator[str, None, None]:
    """Generate a pretty version of calendar data.

    Yields:
        Lines of pretty-printed data

    Raises:
        Error: if no calendar data is found

    """
    table = prettytable.PrettyTable(
      [
        '[bold cyan]Service[/]',
        '[bold cyan]Start[/]',
        '[bold cyan]End[/]',
        '[bold cyan]Mon[/]',
        '[bold cyan]Tue[/]',
        '[bold cyan]Wed[/]',
        '[bold cyan]Thu[/]',
        '[bold cyan]Fri[/]',
        '[bold cyan]Sat[/]',
        '[bold cyan]Sun[/]',
        '[bold cyan]Exceptions[/]',
      ]
    )
    has_data = False
    for service in sorted(self._db.calendar):
      if filter_to is not None and service not in filter_to:
        continue
      has_data = True
      calendar: dm.CalendarService = self._db.calendar[service]
      table.add_row(
        [
          f'[bold cyan]{calendar.id}[/]',
          f'[bold yellow]{base.PRETTY_DATE(calendar.days.start)}[/]',
          (
            f'[bold]'
            f'{
              base.PRETTY_DATE(
                calendar.days.end if calendar.days.end != calendar.days.start else None
              )
            }'
            f'[/]'
          ),
          f'[bold]{base.PRETTY_BOOL(calendar.week[0])}[/]',
          f'[bold]{base.PRETTY_BOOL(calendar.week[1])}[/]',
          f'[bold]{base.PRETTY_BOOL(calendar.week[2])}[/]',
          f'[bold]{base.PRETTY_BOOL(calendar.week[3])}[/]',
          f'[bold]{base.PRETTY_BOOL(calendar.week[4])}[/]',
          f'[bold]{base.PRETTY_BOOL(calendar.week[5])}[/]',
          f'[bold]{base.PRETTY_BOOL(calendar.week[6])}[/]',
          '\n'.join(
            f'[bold]{base.PRETTY_DATE(d)} {base.PRETTY_BOOL(calendar.exceptions[d])}[/]'
            for d in sorted(calendar.exceptions)
          )
          if calendar.exceptions
          else base.NULL_TEXT,
        ]
      )
    if not has_data:
      raise Error('No calendar data found')
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]

  def PrettyPrintStops(
    self, /, *, filter_to: set[str] | None = None
  ) -> abc.Generator[str, None, None]:
    """Generate a pretty version of the stops.

    Yields:
        Lines of pretty-printed data

    Raises:
        Error: if no stops data is found

    """
    table = prettytable.PrettyTable(
      [
        '[bold cyan]Stop[/]',
        '[bold cyan]Code[/]',
        '[bold cyan]Name[/]',
        '[bold cyan]Type[/]',
        '[bold cyan]Location °[/]',
        '[bold cyan]Location[/]',
        '[bold cyan]Zone[/]',
        '[bold cyan]Desc.[/]',
        '[bold cyan]URL[/]',
      ]
    )
    has_data = False
    for _, stop_id in sorted((s.name, s.id) for s in self._db.stops.values()):
      if filter_to is not None and stop_id not in filter_to:
        continue
      has_data = True
      stop: dm.BaseStop = self._db.stops[stop_id]
      parent_code = (
        '' if stop.parent is None else f'\n[bold red]  \u2514\u2500 {stop.parent}[/]'
      )  # └─
      parent_name = (
        ''
        if stop.parent is None
        else f'\n[bold red]  \u2514\u2500 '  # └─
        f'{self._db.stops[stop.parent].name}[/]'
      )
      lat, lon = stop.point.ToDMS()
      table.add_row(
        [
          f'[bold cyan]{stop.id}[/]{parent_code}',
          f'[bold]{stop.code if stop.code and stop.code != "0" else base.NULL_TEXT}[/]',
          f'[bold yellow]{stop.name}[/]{parent_name}',
          f'[bold]{stop.location.name}[/]',
          f'[bold yellow]{lat}[/]\n[bold yellow]{lon}[/]',
          (f'[bold]{stop.point.latitude:0.7f}[/]\n[bold]{stop.point.longitude:0.7f}[/]'),
          f'[bold]{stop.zone or base.NULL_TEXT}[/]',
          f'[bold]{stop.description if stop.zone else base.NULL_TEXT}[/]',
          f'[bold]{stop.url or base.NULL_TEXT}[/]',
        ]
      )
    if not has_data:
      raise Error('No stop data found')
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]

  def PrettyPrintShape(self, /, *, shape_id: str) -> abc.Generator[str, None, None]:
    """Generate a pretty version of a shape.

    Yields:
        Lines of pretty-printed data

    Raises:
        Error: if shape id is not found

    """
    shape: dm.Shape | None = self._db.shapes.get(shape_id.strip(), None)
    if not shape_id.strip() or not shape:
      raise Error(f'shape id {shape_id!r} was not found')
    yield f'[magenta]GTFS Shape ID [bold]{shape.id}[/]'
    yield ''
    table = prettytable.PrettyTable(
      [
        '[bold cyan]#[/]',
        '[bold cyan]Distance[/]',
        '[bold cyan]Latitude °[/]',
        '[bold cyan]Longitude °[/]',
        '[bold cyan]Latitude[/]',
        '[bold cyan]Longitude[/]',
      ]
    )
    for seq in range(1, len(shape.points) + 1):
      point: dm.ShapePoint = shape.points[seq]
      lat, lon = point.point.ToDMS()
      table.add_row(
        [
          f'[bold cyan]{seq}[/]',
          f'[bold]{point.distance:0.2f}[/]',
          f'[bold yellow]{lat}[/]',
          f'[bold yellow]{lon}[/]',
          f'[bold]{point.point.latitude:0.7f}[/]',
          f'[bold]{point.point.longitude:0.7f}[/]',
        ]
      )
    yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]

  def PrettyPrintTrip(self, /, *, trip_id: str) -> abc.Generator[str, None, None]:
    """Generate a pretty version of a Trip.

    Yields:
        Lines of pretty-printed data

    Raises:
        Error: if trip id is not found

    """
    agency, route, trip = self.FindTrip(trip_id)
    if not agency or not route or not trip:
      raise Error(f'trip id {trip_id!r} was not found')
    yield f'[magenta]GTFS Trip ID [bold]{trip.id}[/]'
    yield ''
    yield f'Agency:        [bold yellow]{agency.name}[/]'
    yield f'Route:         [bold yellow]{route.id}[/]'
    yield f'  Short name:  [bold yellow]{route.short_name}[/]'
    yield f'  Long name:   [bold yellow]{route.long_name}[/]'
    yield (f'  Description: [bold]{route.description or base.NULL_TEXT}[/]')
    yield (f'Direction:     [bold yellow]{"inbound" if trip.direction else "outbound"}[/]')
    yield f'Service:       [bold yellow]{trip.service}[/]'
    yield f'Shape:         [bold]{trip.shape or base.NULL_TEXT}[/]'
    yield f'Headsign:      [bold]{trip.headsign or base.NULL_TEXT}[/]'
    yield f'Name:          [bold]{trip.name or base.NULL_TEXT}[/]'
    yield f'Block:         [bold]{trip.block or base.NULL_TEXT}[/]'
    yield ''
    table = prettytable.PrettyTable(
      [
        '[bold cyan]#[/]',
        '[bold cyan]Stop ID[/]',
        '[bold cyan]Name[/]',
        '[bold cyan]Arrival[/]',
        '[bold cyan]Departure[/]',
        '[bold cyan]Code[/]',
        '[bold cyan]Description[/]',
      ]
    )
    for seq in range(1, len(trip.stops) + 1):
      stop: dm.Stop = trip.stops[seq]
      stop_code, stop_name, stop_description = self.StopName(stop.stop)
      table.add_row(
        [
          f'[bold cyan]{seq}[/]',
          f'[bold]{stop.stop}[/]',
          f'[bold yellow]{stop_name or base.NULL_TEXT}[/]',
          (
            f'[bold]'
            f'{
              stop.scheduled.times.arrival.ToHMS()
              if stop.scheduled.times.arrival
              else base.NULL_TEXT
            }'
            f'[/]'
          ),
          (
            f'[bold]'
            f'{
              stop.scheduled.times.departure.ToHMS()
              if stop.scheduled.times.departure
              else base.NULL_TEXT
            }'
            f'[/]'
          ),
          f'[bold]{stop_code}[/]',
          f'[bold]{stop_description or base.NULL_TEXT}[/]',
        ]
      )
    yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]

  def PrettyPrintAllDatabase(self) -> abc.Generator[str, None, None]:
    """Print everything in the database.

    Yields:
        Lines of pretty-printed data

    """
    yield '██ ✿ BASIC DATA ✿ █████████████████████████████████████████████████████████████████'
    yield ''
    yield from self.PrettyPrintBasics()
    yield ''
    yield '██ ✿ CALENDAR ✿ ███████████████████████████████████████████████████████████████████'
    yield ''
    yield from self.PrettyPrintCalendar()
    yield ''
    yield '██ ✿ STOPS ✿ ██████████████████████████████████████████████████████████████████████'
    yield ''
    yield from self.PrettyPrintStops()
    yield ''
    yield '██ ✿ SHAPES ✿ █████████████████████████████████████████████████████████████████████'
    yield ''
    n_shapes: int = len(self._db.shapes)
    for i, shape_id in enumerate(sorted(self._db.shapes)):
      yield from self.PrettyPrintShape(shape_id=shape_id)
      if i < n_shapes - 1:
        yield ''
        yield '━' * 83
        yield ''
    yield ''
    yield '██ ✿ TRIPS ✿ ██████████████████████████████████████████████████████████████████████'
    yield ''
    for agency in sorted(self._db.agencies.keys()):
      for route in sorted(self._db.agencies[agency].routes.keys()):
        for trip in sorted(t.id for t in self._db.agencies[agency].routes[route].trips.values()):
          yield from self.PrettyPrintTrip(trip_id=trip)
          yield ''
          yield '━' * 83
          yield ''


def _UnzipFiles(in_file: IO[bytes], /) -> abc.Generator[tuple[str, bytes], None, None]:
  """Unzip `in_file` bytes buffer. Manages multiple files, preserving case-sensitive _LOAD_ORDER.

  Args:
    in_file: bytes buffer (io.BytesIO for example) with ZIP data

  Yields:
    (file_name, file_data_bytes)

  """
  with zipfile.ZipFile(in_file, 'r') as zip_ref:
    file_names: list[str] = sorted(zip_ref.namelist())
    for n in dm.LOAD_ORDER[::-1]:
      if n in file_names:
        file_names.remove(n)
        file_names.insert(0, n)
    for file_name in file_names:
      with zip_ref.open(file_name) as file_data:
        yield (file_name, file_data.read())


# CLI app setup, this is an important object and can be imported elsewhere and called
app = typer.Typer(
  add_completion=True,
  no_args_is_help=True,
  help='gtfs: CLI for GTFS (General Transit Feed Specification) data.',
  # keep in sync with Main().help
  epilog=(
    'Example:\n\n\n\n'
    '# --- Read GTFS data ---\n\n'
    'poetry run gtfs read\n\n\n\n'
    '# --- Print data ---\n\n'
    'poetry run gtfs print basics\n\n'
    'poetry run gtfs print trip 8001_17410\n\n\n\n'
    '# --- Generate documentation ---\n\n'
    'poetry run gtfs markdown > gtfs.md\n\n'
  ),
)


def Run() -> None:
  """Run the CLI."""
  app()


@app.callback(
  invoke_without_command=True,  # have only one; this is the "constructor"
  help='gtfs: CLI for GTFS (General Transit Feed Specification) data.',
  # keep message in sync with app.help
)
@clibase.CLIErrorGuard
def Main(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: click.Context,  # global context
  version: bool = typer.Option(False, '--version', help='Show version and exit.'),
  verbose: int = typer.Option(
    0,
    '-v',
    '--verbose',
    count=True,
    help='Verbosity (nothing=ERROR, -v=WARNING, -vv=INFO, -vvv=DEBUG).',
    min=0,
    max=3,
  ),
  color: bool | None = typer.Option(
    None,
    '--color/--no-color',
    help=(
      'Force enable/disable colored output (respects NO_COLOR env var if not provided). '
      'Defaults to having colors.'  # state default because None default means docs don't show it
    ),
  ),
) -> None:
  if version:
    typer.echo(__version__)
    raise typer.Exit(0)
  # initialize logging and get console
  console: rich_console.Console
  console, verbose, color = tc_logging.InitLogging(
    verbose,
    color=color,
    include_process=False,
  )
  # create context with the arguments we received.
  ctx.obj = GTFSConfig(
    console=console,
    verbose=verbose,
    color=color,
  )


@app.command(
  'read',
  help='Read DB from official sources',
  epilog=('Example:\n\n\n\n$ poetry run gtfs read\n\n<<loads latest GTFS data>>'),
)
@clibase.CLIErrorGuard
def ReadCommand(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: typer.Context,
  freshness: int = typer.Option(
    _DEFAULT_DAYS_FRESHNESS,
    '-f',
    '--freshness',
    min=0,
    help='Number of days to cache; 0 == always load',
  ),
  allow_unknown_file: bool = typer.Option(
    True,
    '--allow-unknown-file/--no-allow-unknown-file',
    help='Allow unknown files in GTFS ZIP. Defaults to allowing unknown files.',
  ),
  allow_unknown_field: bool = typer.Option(
    False,
    '--allow-unknown-field/--no-allow-unknown-field',
    help='Allow unknown fields in GTFS files. Defaults to not allowing unknown fields.',
  ),
  replace: bool = typer.Option(
    False,
    '--replace/--no-replace',
    help='Force replace DB version. Defaults to not loading the same version again.',
  ),
  override: str = typer.Option(
    '',
    '-o',
    '--override',
    help='Override ZIP file path (instead of downloading)',
  ),
) -> None:
  config: GTFSConfig = ctx.obj
  database = GTFS(DEFAULT_DATA_DIR)
  database.LoadData(
    dm.IRISH_RAIL_OPERATOR,
    dm.IRISH_RAIL_LINK,
    allow_unknown_file=allow_unknown_file,
    allow_unknown_field=allow_unknown_field,
    freshness=freshness,
    force_replace=replace,
    override=override.strip() if override else None,
  )
  config.console.print('[bold green]GTFS database loaded successfully[/]')


print_app = typer.Typer(
  no_args_is_help=True,
  help='Print DB',
)
app.add_typer(print_app, name='print')


@print_app.command(
  'all',
  help='Print all database information.',
  epilog=('Example:\n\n\n\n$ poetry run gtfs print all\n\n<<prints all GTFS data>>'),
)
@clibase.CLIErrorGuard
def PrintAll(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: GTFSConfig = ctx.obj
  database = GTFS(DEFAULT_DATA_DIR)
  for line in database.PrettyPrintAllDatabase():
    config.console.print(line)


@print_app.command(
  'basics',
  help='Print Basic Data.',
  epilog=('Example:\n\n\n\n$ poetry run gtfs print basics\n\n<<prints basic GTFS data>>'),
)
@clibase.CLIErrorGuard
def PrintBasics(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: GTFSConfig = ctx.obj
  database = GTFS(DEFAULT_DATA_DIR)
  for line in database.PrettyPrintBasics():
    config.console.print(line)


@print_app.command(
  'calendars',
  help='Print Calendars/Services.',
  epilog=('Example:\n\n\n\n$ poetry run gtfs print calendars\n\n<<prints GTFS service calendars>>'),
)
@clibase.CLIErrorGuard
def PrintCalendars(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: GTFSConfig = ctx.obj
  database = GTFS(DEFAULT_DATA_DIR)
  for line in database.PrettyPrintCalendar():
    config.console.print(line)


@print_app.command(
  'stops',
  help='Print Stops.',
  epilog=('Example:\n\n\n\n$ poetry run gtfs print stops\n\n<<prints all GTFS stops>>'),
)
@clibase.CLIErrorGuard
def PrintStops(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: GTFSConfig = ctx.obj
  database = GTFS(DEFAULT_DATA_DIR)
  for line in database.PrettyPrintStops():
    config.console.print(line)


@print_app.command(
  'shape',
  help='Print Shape.',
  epilog=(
    'Example:\n\n\n\n$ poetry run gtfs print shape 38002\n\n<<prints details for shape 38002>>'
  ),
)
@clibase.CLIErrorGuard
def PrintShape(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: typer.Context,
  shape_id: str = typer.Argument(..., help='Shape ID to print'),
) -> None:
  config: GTFSConfig = ctx.obj
  database = GTFS(DEFAULT_DATA_DIR)
  for line in database.PrettyPrintShape(shape_id=shape_id):
    config.console.print(line)


@print_app.command(
  'trip',
  help='Print GTFS Trip.',
  epilog=(
    'Example:\n\n\n\n'
    '$ poetry run gtfs print trip 8001_17410\n\n'
    '<<prints details for trip 8001_17410>>'
  ),
)
@clibase.CLIErrorGuard
def PrintTrip(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: typer.Context,
  trip_id: str = typer.Argument(..., help='Trip ID to print'),
) -> None:
  config: GTFSConfig = ctx.obj
  database = GTFS(DEFAULT_DATA_DIR)
  for line in database.PrettyPrintTrip(trip_id=trip_id):
    config.console.print(line)


@app.command(
  'markdown',
  help='Emit Markdown docs for the CLI (see README.md section "Creating a New Version").',
  epilog=('Example:\n\n\n\n$ poetry run gtfs markdown > gtfs.md\n\n<<saves CLI doc>>'),
)
@clibase.CLIErrorGuard
def Markdown(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: GTFSConfig = ctx.obj
  config.console.print(clibase.GenerateTyperHelpMarkdown(app, prog_name='gtfs'))
