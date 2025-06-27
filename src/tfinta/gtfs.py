#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
"""GTFS: Loading, parsing, etc.

See: https://gtfs.org/documentation/schedule/reference/
"""

import argparse
import contextlib
import csv
import dataclasses
import datetime
import functools
import io
import logging
import os
import os.path
# import pdb
import sys
import time
import types
from typing import Any, Callable, Generator, IO, Optional
from typing import get_args as GetTypeArgs
from typing import get_type_hints as GetTypeHints
import urllib.request
import zipfile
import zoneinfo

from balparda_baselib import base
import prettytable

from . import gtfs_data_model as dm

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 2)


# defaults
_DEFAULT_DAYS_FRESHNESS = 10
_DAYS_CACHE_FRESHNESS = 1
_SECONDS_IN_DAY = 60 * 60 * 24
DAYS_OLD: Callable[[float], float] = lambda t: (time.time() - t) / _SECONDS_IN_DAY
DEFAULT_DATA_DIR: str = base.MODULE_PRIVATE_DIR(__file__, '.tfinta-data')
_DB_FILE_NAME = 'transit.db'

# cache sizes (in entries)
_SMALL_CACHE = 1 << 10   # 1024
_MEDIUM_CACHE = 1 << 14  # 16384
_LARGE_CACHE = 1 << 16   # 65536

# type maps for efficiency and memory (so we don't build countless enum objects)
_LOCATION_TYPE_MAP: dict[int, dm.LocationType] = {e.value: e for e in dm.LocationType}
_STOP_POINT_TYPE_MAP: dict[int, dm.StopPointType] = {e.value: e for e in dm.StopPointType}
_ROUTE_TYPE_MAP: dict[int, dm.RouteType] = {e.value: e for e in dm.RouteType}


class Error(Exception):
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
  operator: str   # GTFS Operator, from CSV Official Sources (required)
  link: str       # GTFS ZIP file URL location               (required)
  file_name: str  # file name (ex: 'feed_info.txt')          (required)


# useful aliases
_GTFSRowHandler = Callable[
    [_TableLocation, int, dict[str, None | str | int | float | bool]], None]


def HMSToSeconds(time_str: str) -> int:
  """Accepts 'H:MM:SS' or 'HH:MM:SS' and returns total seconds since 00:00:00.

  Supports hours ≥ 0 with no upper bound. Very flexible, will even accept 'H:M:S' for example.

  Args:
    time_str: String to convert ('H:MM:SS' or 'HH:MM:SS')

  Raises:
    ValueError: malformed input
  """
  try:
    h_str, m_str, s_str = time_str.split(':')
  except ValueError as err:
    raise ValueError(f'bad time literal {time_str!r}') from err
  h, m, s = int(h_str), int(m_str), int(s_str)
  if not (0 <= m < 60 and 0 <= s < 60):
    raise ValueError(f'bad time literal {time_str!r}: minute and second must be 0-59')
  return h * 3600 + m * 60 + s


def SecondsToHMS(sec: int) -> str:
  """Seconds from midnight to 'HH:MM:SS' representation. Supports any positive integer."""
  if sec < 0:
    raise ValueError(f'no negative time allowed, got {sec}')
  h, sec = divmod(sec, 3600)
  m, s = divmod(sec, 60)
  return f'{h:02d}:{m:02d}:{s:02d}'


class GTFS:
  """GTFS database."""

  def __init__(self, db_dir_path: str) -> None:
    """Constructor.

    Args:
      db_dir_path: Path to directory in which to save DB 'transit.db'
    """
    # save the dir/path, create directory if needed
    self._dir_path: str = db_dir_path.strip()
    if not self._dir_path:
      raise Error('DB dir path cannot be empty')
    if not os.path.isdir(self._dir_path):
      os.mkdir(self._dir_path)
      logging.info('Created data directory: %s', self._dir_path)
    self._db_path: str = os.path.join(self._dir_path, _DB_FILE_NAME)
    self._db: dm.GTFSData
    self._changed = False
    # load DB, or create if new
    if os.path.exists(self._db_path):
      # DB exists: load
      with base.Timer() as tm_load:
        self._db = base.BinDeSerialize(file_path=self._db_path, compress=True)
      logging.info('Loaded DB from %r (%s)', self._db_path, tm_load.readable)
      logging.info('DB freshness: %s', base.STD_TIME_STRING(self._db.tm))
    else:
      # DB does not exist: create empty
      self._db = dm.GTFSData(  # empty DB
          tm=0.0, files=dm.OfficialFiles(tm=0.0, files={}),
          agencies={}, calendar={}, shapes={}, stops={})
      self.Save(force=True)
    # create file handlers structure
    self._file_handlers: dict[str, tuple[_GTFSRowHandler, type, dict[str, tuple[type, bool]], set[str]]] = {  # type:ignore
        # {file_name: (handler, TypedDict_row_definition,
        #              {field: (type, required?)}, {required1, required2, ...})}
        'feed_info.txt': (self._HandleFeedInfoRow, dm.ExpectedFeedInfoCSVRowType, {}, set()),                 # type:ignore
        'agency.txt': (self._HandleAgencyRow, dm.ExpectedAgencyCSVRowType, {}, set()),                        # type:ignore
        'calendar.txt': (self._HandleCalendarRow, dm.ExpectedCalendarCSVRowType, {}, set()),                  # type:ignore
        'calendar_dates.txt': (self._HandleCalendarDatesRow, dm.ExpectedCalendarDatesCSVRowType, {}, set()),  # type:ignore
        'routes.txt': (self._HandleRoutesRow, dm.ExpectedRoutesCSVRowType, {}, set()),                        # type:ignore
        'shapes.txt': (self._HandleShapesRow, dm.ExpectedShapesCSVRowType, {}, set()),                        # type:ignore
        'trips.txt': (self._HandleTripsRow, dm.ExpectedTripsCSVRowType, {}, set()),                           # type:ignore
        'stops.txt': (self._HandleStopsRow, dm.ExpectedStopsCSVRowType, {}, set()),                           # type:ignore
        'stop_times.txt': (self._HandleStopTimesRow, dm.ExpectedStopTimesCSVRowType, {}, set()),              # type:ignore
    }
    # fill in types, derived from the _Expected*CSVRowType TypedDicts
    for file_name, (_, expected, fields, required) in self._file_handlers.items():
      for field, type_descriptor in GetTypeHints(expected).items():
        if type_descriptor in (str, int, float, bool):
          # no optional, so field is required
          required.add(field)
          fields[field] = (type_descriptor, True)
        else:
          # it is optional and something else, so find out which
          field_args = GetTypeArgs(type_descriptor)
          if len(field_args) != 2:
            raise Error(f'incorrect type len {file_name}/{field}: {field_args!r}')
          field_type = field_args[0] if field_args[1] == types.NoneType else field_args[1]
          if field_type not in (str, int, float, bool):
            raise Error(f'incorrect type {file_name}/{field}: {field_args!r}')
          fields[field] = (field_type, False)

  def Save(self, force: bool = False) -> None:
    """Save DB to file.

    Args:
      force: (default False) Saves even if no changes to data were detected
    """
    if force or self._changed:
      with base.Timer() as tm_save:
        # (compressing is responsible for ~95% of save time)
        self._db.tm = time.time()
        base.BinSerialize(self._db, file_path=self._db_path, compress=True)
      self._changed = False
      logging.info('Saved DB to %r (%s)', self._db_path, tm_save.readable)

  @functools.lru_cache(maxsize=_MEDIUM_CACHE)  # remember to update self._InvalidateCaches()
  def FindRoute(self, route_id: str) -> Optional[dm.Agency]:
    """Find route by finding its Agency."""
    for agency in self._db.agencies.values():
      if route_id in agency.routes:
        return agency
    return None

  @functools.lru_cache(maxsize=_LARGE_CACHE)  # remember to update self._InvalidateCaches()
  def FindTrip(self, trip_id: str) -> tuple[
      Optional[dm.Agency], Optional[dm.Route], Optional[dm.Trip]]:
    """Find route by finding its Agency & Route. Return (agency, route, trip)."""
    for agency in self._db.agencies.values():
      for route in agency.routes.values():
        if trip_id in route.trips:
          return (agency, route, route.trips[trip_id])
    return (None, None, None)

  @functools.lru_cache(maxsize=_SMALL_CACHE)  # remember to update self._InvalidateCaches()
  def StopName(self, stop_id: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Gets (code, name, description) for a Stop object of `id`."""
    if stop_id not in self._db.stops:
      return (None, None, None)
    stop: dm.BaseStop = self._db.stops[stop_id]
    return (stop.code, stop.name, stop.description)

  @functools.lru_cache(maxsize=_SMALL_CACHE)  # remember to update self._InvalidateCaches()
  def StopNameTranslator(self, stop_id: str) -> str:
    """Translates a stop ID into a name. If not found raises."""
    name: Optional[str] = self.StopName(stop_id)[1]
    if not name:
      raise Error(f'Invalid stop code found: {stop_id}')
    return name

  @functools.lru_cache(maxsize=_SMALL_CACHE)  # remember to update self._InvalidateCaches()
  def StopIDFromNameFragmentOrID(self, stop_name_or_id: str) -> str:
    """Searches for `stop_id` based on either an ID (verifies exists) or stop name.

    If searching by name, will search for a case-insensitive partial match that is UNIQUE.

    Args:
      stop_name_or_id: either a stop_id (case-sensitive) or a partial station name match (case-insensitive)

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
          '--- Use ID or be more specific')
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

  def ServicesForDay(self, day: datetime.date) -> set[int]:
    """Return set[int] of services active (available/running/operating) on this day."""
    weekday: int = day.weekday()
    services: set[int] = set()
    # go over available services
    for service, calendar in self._db.calendar.items():
      if calendar.days.start <= day <= calendar.days.end:
        # day is in range for this service; check day of week and the exceptions
        weekday_service: bool = calendar.week[weekday]
        service_exception: Optional[bool] = calendar.exceptions.get(day)
        has_service: bool = service_exception if service_exception is not None else weekday_service
        if has_service:
          services.add(service)
    return services

  def FindAgencyRoute(
      self, agency_name: str, route_type: dm.RouteType, short_name: str,
      long_name: Optional[str] = None) -> tuple[Optional[dm.Agency], Optional[dm.Route]]:
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
      self, operator: str, link: str, freshness: int = _DEFAULT_DAYS_FRESHNESS,
      allow_unknown_file: bool = True, allow_unknown_field: bool = False,
      force_replace: bool = False, override: Optional[str] = None) -> None:
    """Downloads and parses GTFS data.

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
          operator, link,
          allow_unknown_file=allow_unknown_file, allow_unknown_field=allow_unknown_field,
          force_replace=force_replace, override=override)
    if (not force_replace and operator in self._db.files.files and
        link in self._db.files.files[operator] and
        self._db.files.files[operator][link] and
        (age := DAYS_OLD(self._db.files.files[operator][link].tm)) <= freshness):  # type:ignore
      logging.info('GTFS sources are fresh (%0.2f days old) - SKIP', age)
    else:
      logging.info('Parsing GTFS ZIP source (%0.2f days old)', age)
      self._LoadGTFSSource(
          operator, link,
          allow_unknown_file=allow_unknown_file, allow_unknown_field=allow_unknown_field,
          force_replace=force_replace, override=None)

  def _LoadCSVSources(self) -> None:
    """Loads GTFS official sources from CSV."""
    # get the file and parse it
    new_files: dict[str, dict[str, Optional[dm.FileMetadata]]] = {}
    with urllib.request.urlopen(dm.OFFICIAL_GTFS_CSV) as gtfs_csv:
      text_csv = io.TextIOWrapper(gtfs_csv, encoding='utf-8')
      for i, row in enumerate(csv.reader(text_csv)):
        if len(row) != 2:
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
        len(new_files), sum(len(urls) for urls in new_files.values()))

  @contextlib.contextmanager
  def _ParsingSession(self) -> Generator[None, Any, None]:
    """Context manager that invalidates caches before/after a parsing block."""
    self._InvalidateCaches()  # fresh start
    try:
      yield  # run parsing body
    except Exception:
      # ensure caches are clean even on failure
      self._InvalidateCaches()
      raise  # propagate the original error
    finally:
      # success path – still clear once more for safety
      self.Save()
      self._InvalidateCaches()

  def _LoadGTFSSource(
      self, operator: str, link: str,
      allow_unknown_file: bool = True, allow_unknown_field: bool = False,
      force_replace: bool = False, override: Optional[str] = None) -> None:
    """Loads a single GTFS ZIP file and parses all inner data files.

    Args:
      operator: Operator for GTFS file
      link: URL for GTFS file
      allow_unknown_file: (default True) If False will raise on unknown GTFS file
      allow_unknown_field: (default False) If False will raise on unknown field in file
      force_replace: (default False) If True will parse a repeated version of the ZIP file
      override: (default None) If given, this ZIP file path will override the download

    Raises:
      ParseError: missing files or fields
      ParseImplementationError: unknown file or field (if "allow" is False)
    """
    # check that we are asking for a valid and known source
    operator, link = operator.strip(), link.strip()
    if not operator or operator not in self._db.files.files:
      raise Error(f'invalid operator {operator!r}')
    operator_files: dict[str, Optional[dm.FileMetadata]] = self._db.files.files[operator]
    if not link or link not in operator_files:
      raise Error(f'invalid URL {link!r}')
    # load ZIP from URL
    done_files: set[str] = set()
    file_name: str
    cache_file_name: str = link.replace('://', '__').replace('/', '_')
    cache_file_path: str = os.path.join(self._dir_path, cache_file_name)
    save_cache_file: bool
    with self._ParsingSession():
      if override:
        if not os.path.exists(override):
          raise Error(f'Override file does not exist: {override!r}')
        url_opener = open(override, 'rb')
        save_cache_file = False
      else:
        if (not force_replace and os.path.exists(cache_file_path) and
            (age := DAYS_OLD(os.path.getmtime(cache_file_path))) <= _DAYS_CACHE_FRESHNESS):
          # we will used the cached ZIP
          logging.warning('Loading from %0.2f days old cache on disk! (use -r to override)', age)
          url_opener = open(cache_file_path, 'rb')
          save_cache_file = False
        else:
          # we will re-download from the URL
          url_opener = urllib.request.urlopen(link)
          save_cache_file = True
      # open from whatever source
      with url_opener as gtfs_zip:
        # get ZIP binary content, and if we got from URL save to cache
        gtfs_zip_bytes: bytes = gtfs_zip.read()
        logging.info(
            'Loading %r data, %s, from %r%s',
            operator, base.HumanizedBytes(len(gtfs_zip_bytes)),
            link if save_cache_file else cache_file_name,
            ' => SAVING to cache' if save_cache_file else '')
        if save_cache_file:
          with open(cache_file_path, 'wb') as cache_file_obj:
            cache_file_obj.write(gtfs_zip_bytes)
        # extract files from ZIP
        for file_name, file_data in _UnzipFiles(io.BytesIO(gtfs_zip_bytes)):
          file_name = file_name.strip()
          location = _TableLocation(operator=operator, link=link, file_name=file_name)
          try:
            self._LoadGTFSFile(
                location, file_data,
                allow_unknown_file=allow_unknown_file, allow_unknown_field=allow_unknown_field)
          except ParseIdenticalVersionError as err:
            if force_replace:
              logging.warning('Replacing existing data: %s', err)
              continue
            logging.warning('Version already known (will SKIP): %s', err)
            return
          finally:
            done_files.add(file_name)
      # finished loading the files, check that we loaded all required files
      if (missing_files := dm.REQUIRED_FILES - done_files):
        raise ParseError(f'Missing required files: {operator} {missing_files!r}')
      self._changed = True

  def _LoadGTFSFile(
      self, location: _TableLocation, file_data: bytes,
      allow_unknown_file: bool, allow_unknown_field: bool) -> None:
    """Loads a single txt (actually CSV) file and parses all fields, sending rows to handlers.

    Args:
      location: (operator, link, file_name)
      file_data: File bytes
      allow_unknown_file: If False will raise on unknown GTFS file
      allow_unknown_field: If False will raise on unknown field in file

    Raises:
      ParseError: missing fields
      ParseImplementationError: unknown file or field (if "allow" is False)
    """
    # check if we know how to process this file
    file_name: str = location.file_name
    if file_name not in self._file_handlers or not file_data:
      message: str = (
          f'Unsupported GTFS file: {file_name if file_name else "<empty>"} '
          f'({base.HumanizedBytes(len(file_data))})')
      if allow_unknown_file:
        logging.warning(message)
        return
      raise ParseImplementationError(message)
    # supported type of GTFS file, so process the data into the DB
    logging.info('Processing: %s (%s)', file_name, base.HumanizedBytes(len(file_data)))
    # get fields data, and process CSV with a dict reader
    file_handler, _, field_types, required_fields = self._file_handlers[file_name]
    i: int = 0
    for i, row in enumerate(csv.DictReader(
        io.TextIOWrapper(io.BytesIO(file_data), encoding='utf-8'))):
      parsed_row: dict[str, None | str | int | float | bool] = {}
      field_value: Optional[str]
      # process field-by-field
      for field_name, field_value in row.items():
        # strip and nullify the empty value
        field_value = field_value.strip()  # type:ignore
        field_value = field_value if field_value else None
        if field_name in field_types:
          # known/expected field
          field_type, field_required = field_types[field_name]
          if field_value is None:
            # field is empty
            if field_required:
              raise ParseError(f'Empty required field: {file_name}/{i} {field_name!r}: {row}')
            parsed_row[field_name] = None
          else:
            # field has a value
            if field_type == str:
              parsed_row[field_name] = field_value  # vanilla string
            elif field_type == bool:
              parsed_row[field_name] = field_value == '1'  # convert to bool '0'/'1'
            else:
              parsed_row[field_name] = field_type(field_value)  # convert int/float
        else:
          # unknown field, check if we message/raise only in first row
          if not i:
            message = f'Extra fields found: {file_name}/0 {field_name!r}'
            if allow_unknown_field:
              logging.warning(message)
            else:
              raise ParseImplementationError(message)
          # if allowed, then place as nullable string
          parsed_row[field_name] = field_value
      # we have a row, check for missing required fields
      parsed_row_fields = set(parsed_row.keys())
      if (missing_required := required_fields - parsed_row_fields):
        raise ParseError(f'Missing required fields: {file_name}/{i} {missing_required!r}: {row}')
      # add known fields that are missing (with None as value)
      for field in (set(field_types.keys()) - parsed_row_fields):
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
  #     self, location: _TableLocation, count: int, row: dm.ExpectedFILENAMECSVRowType) -> None:
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
      self, location: _TableLocation, count: int, row: dm.ExpectedFeedInfoCSVRowType) -> None:
    """Handler: "feed_info.txt" Information on the GTFS ZIP file being processed.

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
          f'feed_info.txt table ({location}) is only supported to have 1 row (got {count}): {row}')
    # get data, check
    start: datetime.date = dm.DATE_OBJ(row['feed_start_date'])
    end: datetime.date = dm.DATE_OBJ(row['feed_end_date'])
    if start > end:
      raise RowError(f'incompatible start/end dates in {location}: {row}')
    # check against current version (and log)
    tm: float = time.time()
    current_data: Optional[dm.FileMetadata] = self._db.files.files[location.operator][location.link]
    if current_data is None:
      logging.info(
          'Loading version %r @ %s for %s/%s',
          row['feed_version'], base.STD_TIME_STRING(tm), location.operator, location.link)
    else:
      if (row['feed_version'] == current_data.version and
          row['feed_publisher_name'] == current_data.publisher and
          row['feed_lang'] == current_data.language and
          start == current_data.days.start and
          end == current_data.days.end):
        # same version of the data!
        # note that since we `raise` we don't update the timestamp, so the timestamp
        # is the time we first processed this version of the ZIP file
        raise ParseIdenticalVersionError(
            f'{row["feed_version"]} @ {base.STD_TIME_STRING(current_data.tm)} '
            f'{location.operator} / {location.link}')
      logging.info(
          'Updating version %r @ %s -> %r @ %s for %s/%s',
          current_data.version, base.STD_TIME_STRING(current_data.tm),
          row['feed_version'], base.STD_TIME_STRING(tm), location.operator, location.link)
    # update
    self._db.files.files[location.operator][location.link] = dm.FileMetadata(
        tm=tm, publisher=row['feed_publisher_name'], url=row['feed_publisher_url'],
        language=row['feed_lang'], days=dm.DaysRange(start=start, end=end),
        version=row['feed_version'], email=row['feed_contact_email'])

  def _HandleAgencyRow(
      self, unused_location: _TableLocation,
      unused_count: int, row: dm.ExpectedAgencyCSVRowType) -> None:
    """Handler: "agency.txt" Transit agencies.

    pk: agency_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    # update
    self._db.agencies[row['agency_id']] = dm.Agency(
        id=row['agency_id'], name=row['agency_name'], url=row['agency_url'],
        zone=zoneinfo.ZoneInfo(row['agency_timezone']), routes={})

  def _HandleCalendarRow(
      self, location: _TableLocation, count: int, row: dm.ExpectedCalendarCSVRowType) -> None:
    """Handler: "calendar.txt" Service dates specified using a weekly schedule & start/end dates.

    pk: service_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    # get data, check
    start: datetime.date = dm.DATE_OBJ(row['start_date'])
    end: datetime.date = dm.DATE_OBJ(row['end_date'])
    if start > end:
      raise RowError(f'inconsistent row @{count} / {location}: {row}')
    # update
    self._db.calendar[row['service_id']] = dm.CalendarService(
        id=row['service_id'],
        week=(row['monday'], row['tuesday'], row['wednesday'],
              row['thursday'], row['friday'], row['saturday'], row['sunday']),
        days=dm.DaysRange(start=start, end=end), exceptions={})

  def _HandleCalendarDatesRow(
      self, unused_location: _TableLocation, unused_count: int,
      row: dm.ExpectedCalendarDatesCSVRowType) -> None:
    """Handler: "calendar_dates.txt" Exceptions for the services defined in the calendar table.

    pk: (calendar/service_id, date) / ref: calendar/service_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    self._db.calendar[row['service_id']].exceptions[dm.DATE_OBJ(row['date'])] = (
        row['exception_type'] == '1')

  def _HandleRoutesRow(
      self, unused_location: _TableLocation, unused_count: int,
      row: dm.ExpectedRoutesCSVRowType) -> None:
    """Handler: "routes.txt" Routes: group of trips that are displayed to riders as a single service.

    pk: route_id / ref: agency/agency_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    self._db.agencies[row['agency_id']].routes[row['route_id']] = dm.Route(
        id=row['route_id'], agency=row['agency_id'], short_name=row['route_short_name'],
        long_name=row['route_long_name'], route_type=_ROUTE_TYPE_MAP[row['route_type']],
        description=row['route_desc'], url=row['route_url'],
        color=row['route_color'], text_color=row['route_text_color'], trips={})

  def _HandleShapesRow(
      self, location: _TableLocation, count: int, row: dm.ExpectedShapesCSVRowType) -> None:
    """Handler: "shapes.txt" Rules for mapping vehicle travel paths (aka. route alignments).

    pk: (shape_id, shape_pt_sequence)

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    # check
    if (not -90.0 <= row['shape_pt_lat'] <= 90.0 or
        not -180.0 <= row['shape_pt_lon'] <= 180.0 or
        row['shape_dist_traveled'] < 0.0):
      raise RowError(f'invalid row @{count} / {location}: {row}')
    # update
    if row['shape_id'] not in self._db.shapes:
      self._db.shapes[row['shape_id']] = dm.Shape(id=row['shape_id'], points={})
    self._db.shapes[row['shape_id']].points[row['shape_pt_sequence']] = dm.ShapePoint(
        id=row['shape_id'], seq=row['shape_pt_sequence'],
        point=dm.Point(latitude=row['shape_pt_lat'], longitude=row['shape_pt_lon']),
        distance=row['shape_dist_traveled'])

  def _HandleTripsRow(
      self, location: _TableLocation, count: int, row: dm.ExpectedTripsCSVRowType) -> None:
    """Handler: "trips.txt" Trips for each route.

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
    agency: Optional[dm.Agency] = self.FindRoute(row['route_id'])
    if agency is None:
      raise RowError(f'agency in row was not found @{count} / {location}: {row}')
    # update
    self._db.agencies[agency.id].routes[row['route_id']].trips[row['trip_id']] = dm.Trip(
        id=row['trip_id'], route=row['route_id'], agency=agency.id,
        service=row['service_id'], shape=row['shape_id'], headsign=row['trip_headsign'],
        name=row['trip_short_name'], block=row['block_id'],
        direction=row['direction_id'], stops={})

  def _HandleStopsRow(
      self, location: _TableLocation, count: int, row: dm.ExpectedStopsCSVRowType) -> None:
    """Handler: "stops.txt" Stops where vehicles pick up or drop-off riders.

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
        _LOCATION_TYPE_MAP[row['location_type']] if row['location_type'] else dm.LocationType.STOP)
    if not -90.0 <= row['stop_lat'] <= 90.0 or not -180.0 <= row['stop_lon'] <= 180.0:
      raise RowError(f'invalid latitude/longitude @{count} / {location}: {row}')
    if row['parent_station'] and row['parent_station'] not in self._db.stops:
      #  the GTFS spec does not guarantee parents precede children, but for now we will enforce it
      raise RowError(f'parent_station in row was not found @{count} / {location}: {row}')
    # update
    self._db.stops[row['stop_id']] = dm.BaseStop(
        id=row['stop_id'], parent=row['parent_station'], code=row['stop_code'],
        name=row['stop_name'], point=dm.Point(latitude=row['stop_lat'], longitude=row['stop_lon']),
        zone=row['zone_id'], description=row['stop_desc'],
        url=row['stop_url'], location=location_type)

  def _HandleStopTimesRow(
      self, location: _TableLocation, count: int, row: dm.ExpectedStopTimesCSVRowType) -> None:
    """Handler: "stop_times.txt" Times that a vehicle arrives/departs from stops for each trip.

    pk: (trips/trip_id, stop_sequence) / ref: stops/stop_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    # get data, check if empty
    arrival: int = HMSToSeconds(row['arrival_time'])
    departure: int = HMSToSeconds(row['departure_time'])
    pickup: dm.StopPointType = (
        _STOP_POINT_TYPE_MAP[row['pickup_type']] if row['pickup_type'] else
        dm.StopPointType.REGULAR)
    dropoff: dm.StopPointType
    if row['drop_off_type'] is not None:
      dropoff = dm.StopPointType(row['drop_off_type'])  # new spelling
    elif row['dropoff_type'] is not None:
      dropoff = dm.StopPointType(row['dropoff_type'])   # old spelling
    else:
      dropoff = dm.StopPointType.REGULAR
    if arrival < 0 or departure < 0 or arrival > departure:
      raise RowError(f'invalid row @{count} / {location}: {row}')
    if row['stop_id'] not in self._db.stops:
      raise RowError(f'stop_id in row was not found @{count} / {location}: {row}')
    agency, route, trip = self.FindTrip(row['trip_id'])
    if not agency or not route or not trip:
      raise RowError(f'trip_id in row was not found @{count} / {location}: {row}')
    # update
    self._db.agencies[agency.id].routes[route.id].trips[row['trip_id']].stops[row['stop_sequence']] = dm.Stop(
        id=row['trip_id'], seq=row['stop_sequence'], stop=row['stop_id'],
        agency=agency.id, route=route.id,
        scheduled=dm.ScheduleStop(arrival=arrival, departure=departure, timepoint=row['timepoint']),
        headsign=row['stop_headsign'], pickup=pickup, dropoff=dropoff)

  ##################################################################################################
  # GTFS PRETTY PRINTS
  ##################################################################################################

  def PrettyPrintTrip(self, trip_id: str) -> Generator[str, None, None]:
    """Generate a pretty version of a Trip."""
    agency, route, trip = self.FindTrip(trip_id)
    if not agency or not route or not trip:
      raise Error(f'trip id {trip_id!r} was not found')
    yield f'{base.TERM_MAGENTA}GTFS Trip ID {base.TERM_BOLD}{trip.id}{base.TERM_END}'
    yield ''
    yield f'Agency:        {base.TERM_BOLD}{base.TERM_YELLOW}{agency.name}{base.TERM_END}'
    yield f'Route:         {base.TERM_BOLD}{base.TERM_YELLOW}{route.id}{base.TERM_END}'
    yield f'  Short name:  {base.TERM_BOLD}{base.TERM_YELLOW}{route.short_name}{base.TERM_END}'
    yield f'  Long name:   {base.TERM_BOLD}{base.TERM_YELLOW}{route.long_name}{base.TERM_END}'
    yield (f'  Description: {base.TERM_BOLD}'
           f'{route.description if route.description else dm.NULL_TEXT}{base.TERM_END}')
    yield (f'Direction:     {base.TERM_BOLD}{base.TERM_YELLOW}'
           f'{"inbound" if trip.direction else "outbound"}{base.TERM_END}')
    yield f'Service:       {base.TERM_BOLD}{base.TERM_YELLOW}{trip.service}{base.TERM_END}{base.TERM_END}'
    yield f'Shape:         {base.TERM_BOLD}{trip.shape if trip.shape else dm.NULL_TEXT}{base.TERM_END}'
    yield f'Headsign:      {base.TERM_BOLD}{trip.headsign if trip.headsign else dm.NULL_TEXT}{base.TERM_END}'
    yield f'Name:          {base.TERM_BOLD}{trip.name if trip.name else dm.NULL_TEXT}{base.TERM_END}'
    yield f'Block:         {base.TERM_BOLD}{trip.block if trip.block else dm.NULL_TEXT}{base.TERM_END}'
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.TERM_BOLD}{base.TERM_CYAN}#{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Stop ID{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Name{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Arrival{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Departure{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Code{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Description{base.TERM_END}'])
    for seq in range(1, len(trip.stops) + 1):
      stop: dm.Stop = trip.stops[seq]
      stop_code, stop_name, stop_description = self.StopName(stop.stop)
      table.add_row([
          f'{base.TERM_BOLD}{base.TERM_CYAN}{seq}{base.TERM_END}',
          f'{base.TERM_BOLD}{stop.stop}{base.TERM_END}',
          f'{base.TERM_BOLD}{base.TERM_YELLOW}{stop_name if stop_name else dm.NULL_TEXT}{base.TERM_END}',
          f'{base.TERM_BOLD}{SecondsToHMS(stop.scheduled.arrival)}{base.TERM_END}',
          f'{base.TERM_BOLD}{SecondsToHMS(stop.scheduled.departure)}{base.TERM_END}',
          f'{base.TERM_BOLD}{stop_code}{base.TERM_END}',
          f'{base.TERM_BOLD}{stop_description if stop_description else dm.NULL_TEXT}{base.TERM_END}',
      ])
    yield from table.get_string().splitlines()  # type:ignore


def _UnzipFiles(in_file: IO[bytes]) -> Generator[tuple[str, bytes], None, None]:
  """Unzips `in_file` bytes buffer. Manages multiple files, preserving case-sensitive _LOAD_ORDER.

  Args:
    in_file: bytes buffer (io.BytesIO for example) with ZIP data

  Yields:
    (file_name, file_data_bytes)

  Raises:
    BadZipFile: ZIP error
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


def main(argv: Optional[list[str]] = None) -> int:  # pylint: disable=invalid-name
  """Main entry point."""
  # parse the input arguments, add subparser for `command`
  parser: argparse.ArgumentParser = argparse.ArgumentParser()
  command_arg_subparsers = parser.add_subparsers(dest='command')
  # "read" command
  read_parser: argparse.ArgumentParser = command_arg_subparsers.add_parser(
      'read', help='Read DB from official sources')
  read_parser.add_argument(
      '-f', '--freshness', type=int, default=_DEFAULT_DAYS_FRESHNESS,
      help=f'Number of days to cache; 0 == always load (default: {_DEFAULT_DAYS_FRESHNESS})')
  read_parser.add_argument(
      '-u', '--unknownfile', type=int, default=1,
      help='0 == disallows unknown files ; 1 == allows unknown files (default: 1)')
  read_parser.add_argument(
      '-i', '--unknownfield', type=int, default=0,
      help='0 == disallows unknown fields ; 1 == allows unknown fields (default: 0)')
  read_parser.add_argument(
      '-r', '--replace', type=int, default=0,
      help='0 == does not load the same version again ; 1 == forces replace version (default: 0)')
  read_parser.add_argument(
      '-o', '--override', type=str, default='',
      help='If given, this ZIP file path will override the download (default: empty)')
  # "print" command
  print_parser: argparse.ArgumentParser = command_arg_subparsers.add_parser(
      'print', help='Print DB')
  print_arg_subparsers = print_parser.add_subparsers(dest='print_command')
  trip_parser: argparse.ArgumentParser = print_arg_subparsers.add_parser(
      'trip', help='Print Trip')
  trip_parser.add_argument('-i', '--id', type=str, default='', help='Trip ID (default: "")')
  # ALL commands
  # parser.add_argument(
  #     '-r', '--readonly', type=bool, default=False,
  #     help='If "True" will not save database (default: False)')
  args: argparse.Namespace = parser.parse_args(argv)
  command = args.command.lower().strip() if args.command else ''
  database = GTFS(DEFAULT_DATA_DIR)
  # look at main command
  match command:
    case 'read':
      database.LoadData(
          dm.IRISH_RAIL_OPERATOR, dm.IRISH_RAIL_LINK, freshness=args.freshness,
          allow_unknown_file=args.unknownfile == 1,
          allow_unknown_field=args.unknownfield == 1,
          force_replace=bool(args.replace),
          override=args.override.strip() if args.override else None)
    case 'print':
      # look at sub-command for print
      print_command = args.print_command.lower().strip() if args.print_command else ''
      print()
      match print_command:
        case 'trip':
          for line in database.PrettyPrintTrip(args.id):
            print(line)
        case _:
          raise NotImplementedError()
      print()
    case _:
      raise NotImplementedError()
  return 0


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  sys.exit(main())
