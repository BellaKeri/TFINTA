#!/usr/bin/python3 -O
#
# Copyright 2025 Balparda (balparda@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""GTFS: Loading, parsing, etc.

See: https://gtfs.org/documentation/schedule/reference/
"""

import argparse
import csv
import dataclasses
import datetime
import enum
import functools
import io
import logging
import os
import os.path
# import pdb
import time
import types
from typing import Callable, Generator, IO, Optional, TypedDict, Union
from typing import get_args as GetTypeArgs
from typing import get_type_hints as GetTypeHints
import urllib.request
import zipfile

from baselib import base

__author__ = 'balparda@github.com'
__version__ = (1, 0)


# defaults
_DEFAULT_DAYS_FRESHNESS = 1
_SECONDS_IN_DAY = 60 * 60 * 24
_DAYS_OLD: Callable[[float], float] = lambda t: (time.time() - t) / _SECONDS_IN_DAY
_DATA_DIR: str = base.MODULE_PRIVATE_DIR(__file__, '.tfinta-data')
_DEFAULT_DB_FILE: str = os.path.join(_DATA_DIR, 'transit.db')
_REQUIRED_FILES: set[str] = {
    'feed_info.txt',  # required because it has the date ranges and the version info
}
_LOAD_ORDER: list[str] = [
    # there must be a load order because of the table foreign ID references (listed below)
    'feed_info.txt',  # no primary key -> added to ZIP metadata
    'agency.txt',     # pk: agency_id
    'calendar.txt',        # pk: service_id
    'calendar_dates.txt',  # pk: (calendar/service_id, date) / ref: calendar/service_id
    'routes.txt',      # pk: route_id / ref: agency/agency_id
    'shapes.txt',      # pk: (shape_id, shape_pt_sequence)
    'trips.txt',       # pk: trip_id / ref: routes.route_id, calendar.service_id, shapes.shape_id
    'stops.txt',       # pk: stop_id / self-ref: parent_station=stop/stop_id
    'stop_times.txt',  # pk: (trips/trip_id, stop_sequence) / ref: stops/stop_id
]

# URLs
_OFFICIAL_GTFS_CSV = 'https://www.transportforireland.ie/transitData/Data/GTFS%20Operator%20Files.csv'
_KNOWN_OPERATORS: set[str] = {
    # the operators we care about and will load GTFS for
    'Iarnród Éireann / Irish Rail',
}

# data parsing utils
_DATETIME_OBJ: Callable[[str], datetime.datetime] = lambda s: datetime.datetime.strptime(
    s, '%Y%m%d')
_UTC_DATE: Callable[[str], float] = lambda s: _DATETIME_OBJ(s).replace(
    tzinfo=datetime.timezone.utc).timestamp()
_DATE_OBJ: Callable[[str], datetime.date] = lambda s: _DATETIME_OBJ(s).date()


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


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class FileMetadata:
  """GTFS file metadata (mostly from loading feed_info.txt tables)."""
  tm: float       # timestamp of first load of this version of this GTFS ZIP file
  publisher: str  # feed_info.txt/feed_publisher_name   (required)
  url: str        # feed_info.txt/feed_publisher_url    (required)
  language: str   # feed_info.txt/feed_lang             (required)
  start: datetime.date  # feed_info.txt/feed_start_date (required)
  end: datetime.date    # feed_info.txt/feed_end_date   (required)
  version: str          # feed_info.txt/feed_version    (required)
  email: Optional[str]  # feed_info.txt/feed_contact_email


class _ExpectedFeedInfoCSVRowType(TypedDict):
  """feed_info.txt"""
  feed_publisher_name: str
  feed_publisher_url: str
  feed_lang: str
  feed_start_date: str
  feed_end_date: str
  feed_version: str
  feed_contact_email: Optional[str]


class LocationType(enum.Enum):
  """Location type."""
  # https://gtfs.org/documentation/schedule/reference/?utm_source=chatgpt.com#stopstxt
  STOP = 0           # (or empty) - Stop (or Platform). A location where passengers board or disembark from a transit vehicle. Is called a platform when defined within a parent_station
  STATION = 1        # A physical structure or area that contains one or more platform
  ENTRANCE_EXIT = 2  # A location where passengers can enter or exit a station from the street. If an entrance/exit belongs to multiple stations, it may be linked by pathways to both, but the data provider must pick one of them as parent
  STATION_NODE = 3   # A location within a station, not matching any other location_type, that may be used to link together pathways define in pathways.txt
  BOARDING_AREA = 4  # A specific location on a platform, where passengers can board and/or alight vehicles


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class BaseStop:  # stops.txt
  """Stop where vehicles pick up or drop off riders."""
  id: str                # (PK) stops.txt/stop_id (required)
  parent: Optional[str]  # stops.txt/parent_station -> stops.txt/stop_id (required)
  code: int              # stops.txt/stop_code    (required)
  name: str              # stops.txt/stop_name    (required)
  latitude: float        # stops.txt/stop_lat - WGS84 latitude in decimal degrees (-90.0 <= lat <= 90.0)    (required)
  longitude: float       # stops.txt/stop_lon - WGS84 longitude in decimal degrees (-180.0 <= lat <= 180.0) (required)
  zone: Optional[str]    # stops.txt/zone_id
  description: Optional[str]  # stops.txt/stop_desc
  url: Optional[str]     # stops.txt/stop_url
  location: LocationType = LocationType.STOP  # stops.txt/location_type


class _ExpectedStopsCSVRowType(TypedDict):
  """stops.txt"""
  stop_id: str
  parent_station: Optional[str]
  stop_code: int
  stop_name: str
  stop_lat: float
  stop_lon: float
  zone_id: Optional[str]
  stop_desc: Optional[str]
  stop_url: Optional[str]
  location_type: Optional[int]


class StopPointType(enum.Enum):
  """Pickup/Drop-off type."""
  # https://gtfs.org/documentation/schedule/reference/?utm_source=chatgpt.com#stop_timestxt
  REGULAR = 0        # (or empty) Regularly scheduled pickup/drop-off
  NOT_AVAILABLE = 1  # No pickup/drop-off available
  AGENCY_ONLY = 2    # Must phone agency to arrange pickup/drop-off
  DRIVER_ONLY = 3    # Must coordinate with driver to arrange pickup/drop-off


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Stop:  # stop_times.txt
  """Time that a vehicle arrives/departs from a stop for a trip."""
  id: str    # (PK) stop_times.txt/trip_id            (required) -> trips.txt/trip_id
  seq: int   # (PK) stop_times.txt/stop_sequence      (required)
  stop: str  # stop_times.txt/stop_id                 (required) -> stops.txt/stop_id
  agency: int     # <<INFERRED>> -> agency.txt/agency_id
  route: str      # <<INFERRED>> -> routes.txt/route_id
  arrival: int    # stop_times.txt/arrival_time - seconds from midnight, to represent 'HH:MM:SS'   (required)
  departure: int  # stop_times.txt/departure_time - seconds from midnight, to represent 'HH:MM:SS' (required)
  timepoint: bool          # stop_times.txt/timepoint (required) - False==Times are considered approximate; True==Times are considered exact
  headsign: Optional[str]  # stop_times.txt/stop_headsign
  pickup: StopPointType = StopPointType.REGULAR   # stop_times.txt/pickup_type
  dropoff: StopPointType = StopPointType.REGULAR  # stop_times.txt/drop_off_type


class _ExpectedStopTimesCSVRowType(TypedDict):
  """stop_times.txt"""
  trip_id: str
  stop_sequence: int
  stop_id: str
  arrival_time: str
  departure_time: str
  timepoint: bool
  stop_headsign: Optional[str]
  pickup_type: Optional[int]
  drop_off_type: Optional[int]


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class Trip:
  """Trip for a route."""
  id: str          # (PK) trips.txt/trip_id     (required)
  route: str       # trips.txt/route_id         (required) -> routes.txt/route_id
  agency: int      # <<INFERRED>> -> agency.txt/agency_id
  service: int     # trips.txt/service_id       (required) -> calendar.txt/service_id
  shape: str       # trips.txt/shape_id         (required) -> shapes.txt/shape_id
  headsign: str    # trips.txt/trip_headsign    (required)
  name: str        # trips.txt/trip_short_name  (required)
  direction: bool  # trips.txt/direction_id     (required)
  block: str       # trips.txt/block_id         (required)
  stops: dict[int, Stop]  # {stop_times.txt/stop_sequence: Stop}


class _ExpectedTripsCSVRowType(TypedDict):
  """trips.txt"""
  trip_id: str
  route_id: str
  service_id: int
  shape_id: str
  trip_headsign: str
  trip_short_name: str
  direction_id: bool
  block_id: str


class RouteType(enum.Enum):
  """Route type."""
  # https://gtfs.org/documentation/schedule/reference/?utm_source=chatgpt.com#routestxt
  LIGHT_RAIL = 0   # Tram, Streetcar, Light rail. Any light rail or street level system within a metropolitan area
  SUBWAY = 1       # Subway, Metro. Any underground rail system within a metropolitan area
  RAIL = 2         # Used for intercity or long-distance travel
  BUS = 3          # Used for short- and long-distance bus routes
  FERRY = 4        # Used for short- and long-distance boat service
  CABLE_TRAM = 5   # Used for street-level rail cars where the cable runs beneath the vehicle (e.g., cable car in San Francisco)
  AERIAL_LIFT = 6  # Aerial lift, suspended cable car (e.g., gondola lift, aerial tramway). Cable transport where cabins, cars, gondolas or open chairs are suspended by means of one or more cables
  FUNICULAR = 7    # Any rail system designed for steep inclines
  TROLLEYBUS = 11  # Electric buses that draw power from overhead wires using poles
  MONORAIL = 12    # Railway in which the track consists of a single rail or a beam


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class Route:
  """Route: group of trips that are displayed to riders as a single service."""
  id: str                # (PK) routes.txt/route_id    (required)
  agency: int            # routes.txt/agency_id        (required) -> agency.txt/agency_id
  short_name: str        # routes.txt/route_short_name (required)
  long_name: str         # routes.txt/route_long_name  (required)
  route_type: RouteType  # routes.txt/route_type       (required)
  description: Optional[str]  # routes.txt/route_desc
  url: Optional[str]          # routes.txt/route_url
  color: Optional[str]        # routes.txt/route_color: encoded as a six-digit hexadecimal number (https://htmlcolorcodes.com)
  text_color: Optional[str]   # routes.txt/route_text_color: encoded as a six-digit hexadecimal number
  trips: dict[str, Trip]      # {trips.txt/trip_id: Trip}


class _ExpectedRoutesCSVRowType(TypedDict):
  """routes.txt"""
  route_id: str
  agency_id: int
  route_short_name: str
  route_long_name: str
  route_type: int
  route_desc: Optional[str]
  route_url: Optional[str]
  route_color: Optional[str]
  route_text_color: Optional[str]


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class Agency:
  """Transit agency."""
  id: int    # (PK) agency.txt/agency_id (required)
  name: str  # agency.txt/agency_name    (required)
  url: str   # agency.txt/agency_url     (required)
  zone: str  # agency.txt/agency_timezone: TZ timezone from the https://www.iana.org/time-zones (required)
  routes: dict[str, Route]  # {routes.txt/route_id: Route}


class _ExpectedAgencyCSVRowType(TypedDict):
  """agency.txt"""
  agency_id: int
  agency_name: str
  agency_url: str
  agency_timezone: str


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class CalendarService:
  """Service dates specified using a weekly schedule & start/end dates. Includes the exceptions."""
  id: int  # (PK) calendar.txt/service_id         (required)
  week: tuple[bool, bool, bool, bool, bool, bool, bool]  # calendar.txt/sunday...saturday (required)
  start: datetime.date  # calendar.txt/start_date (required)
  end: datetime.date    # calendar.txt/end_date   (required)
  exceptions: dict[datetime.date, bool]  # {calendar_dates.txt/date: has_service}
  # where `has_service` comes from calendar_dates.txt/exception_type


class _ExpectedCalendarCSVRowType(TypedDict):
  """calendar.txt"""
  service_id: int
  monday: bool
  tuesday: bool
  wednesday: bool
  thursday: bool
  friday: bool
  saturday: bool
  sunday: bool
  start_date: str
  end_date: str


class _ExpectedCalendarDatesCSVRowType(TypedDict):
  """calendar_dates.txt"""
  service_id: int
  date: str
  exception_type: bool


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class ShapePoint:
  """Point in a shape, a place in the real world."""
  id: str           # (PK) shapes.txt/shape_id          (required) -> shapes.txt/shape_id
  seq: int          # (PK) shapes.txt/shape_pt_sequence (required)
  latitude: float   # shapes.txt/shape_pt_lat - WGS84 latitude in decimal degrees (-90.0 <= lat <= 90.0)    (required)
  longitude: float  # shapes.txt/shape_pt_lon - WGS84 longitude in decimal degrees (-180.0 <= lat <= 180.0) (required)
  distance: float   # shapes.txt/shape_dist_traveled    (required)


class _ExpectedShapesCSVRowType(TypedDict):
  """shapes.txt"""
  shape_id: str
  shape_pt_sequence: int
  shape_pt_lat: float
  shape_pt_lon: float
  shape_dist_traveled: float


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class Shape:
  """Rule for mapping vehicle travel paths (aka. route alignments)."""
  id: str                        # (PK) shapes.txt/shape_id (required)
  points: dict[int, ShapePoint]  # {shapes.txt/shape_pt_sequence: ShapePoint}


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class OfficialFiles:
  """Official GTFS files."""
  tm: float  # timestamp of last pull of the official CSV
  files: dict[str, dict[str, Optional[FileMetadata]]]  # {provider: {url: FileMetadata}}


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class GTFSData:
  """GTFS data."""
  tm: float             # timestamp of last DB save
  files: OfficialFiles  # the available GTFS files
  agencies: dict[int, Agency]           # {agency.txt/agency_id, Agency}
  calendar: dict[int, CalendarService]  # {calendar.txt/service_id, CalendarService}
  shapes: dict[str, Shape]              # {shapes.txt/shape_id, Shape}
  stops: dict[str, BaseStop]            # {stops.txt/stop_id, BaseStop}


# useful aliases
_GTFSRowHandler = Callable[
    [_TableLocation, int, dict[str, Union[None, str, int, float, bool]]], None]


class GTFS:
  """GTFS database."""

  def __init__(self, db_path: str) -> None:
    """Constructor.

    Args:
      db_path: Complete path to save DB to
    """
    # save the path
    if not db_path:
      raise Error('DB path cannot be empty')
    self._db_path: str = db_path.strip()
    self._db: GTFSData
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
      self._db = GTFSData(  # empty DB
          tm=0.0, files=OfficialFiles(tm=0.0, files={}),
          agencies={}, calendar={}, shapes={}, stops={})
      self.Save(force=True)
    # create file handlers structure
    self._file_handlers: dict[str, tuple[_GTFSRowHandler, type, dict[str, tuple[type, bool]], set[str]]] = {  # type:ignore
        # {file_name: (handler, TypedDict_row_definition,
        #              {field: (type, required?)}, {required1, required2, ...})}
        'feed_info.txt': (self._HandleFeedInfoRow, _ExpectedFeedInfoCSVRowType, {}, set()),
        'agency.txt': (self._HandleAgencyRow, _ExpectedAgencyCSVRowType, {}, set()),
        'calendar.txt': (self._HandleCalendarRow, _ExpectedCalendarCSVRowType, {}, set()),
        'calendar_dates.txt': (self._HandleCalendarDatesRow, _ExpectedCalendarDatesCSVRowType, {}, set()),
        'routes.txt': (self._HandleRoutesRow, _ExpectedRoutesCSVRowType, {}, set()),
        'shapes.txt': (self._HandleShapesRow, _ExpectedShapesCSVRowType, {}, set()),
        'trips.txt': (self._HandleTripsRow, _ExpectedTripsCSVRowType, {}, set()),
        'stops.txt': (self._HandleStopsRow, _ExpectedStopsCSVRowType, {}, set()),
        'stop_times.txt': (self._HandleStopTimesRow, _ExpectedStopTimesCSVRowType, {}, set()),
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
        self._InvalidateCaches()
      self._changed = False
      logging.info('Saved DB to %r (%s)', self._db_path, tm_save.readable)

  @functools.lru_cache(maxsize=1 << 14)
  def _FindRoute(self, route_id: str) -> Optional[Agency]:
    """Find route by finding its Agency."""
    for agency in self._db.agencies.values():
      if route_id in agency.routes:
        return agency
    return None

  @functools.lru_cache(maxsize=1 << 16)
  def _FindTrip(self, trip_id: str) -> tuple[Optional[Agency], Optional[Route]]:
    """Find route by finding its Agency & Route."""
    for agency in self._db.agencies.values():
      for route in agency.routes.values():
        if trip_id in route.trips:
          return (agency, route)
    return (None, None)

  def _InvalidateCaches(self) -> None:
    self._FindRoute.cache_clear()
    self._FindTrip.cache_clear()

  def _LoadCSVSources(self) -> None:
    """Loads GTFS official sources from CSV."""
    # get the file and parse it
    new_files: dict[str, dict[str, Optional[FileMetadata]]] = {}
    with urllib.request.urlopen(_OFFICIAL_GTFS_CSV) as gtfs_csv:
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
    for operator in _KNOWN_OPERATORS:
      if operator not in new_files:
        raise Error(f'Operator {operator!r} not in loaded CSV!')
    # we have the file loaded
    self._db.files.files = new_files
    self._db.files.tm = time.time()
    self._changed = True
    logging.info(
        'Loaded GTFS official sources with %d operators and %d links',
        len(new_files), sum(len(urls) for urls in new_files.values()))

  def _LoadGTFSSource(
      self, operator: str, link: str,
      allow_unknown_file: bool = True, allow_unknown_field: bool = False,
      force_replace: bool = False) -> None:
    """Loads a single GTFS ZIP file and parses all inner data files.

    Args:
      operator: Operator for GTFS file
      link: URL for GTFS file
      allow_unknown_file: (default True) If False will raise on unknown GTFS file
      allow_unknown_field: (default False) If False will raise on unknown field in file
      force_replace: (default False) If True will parse a repeated version of the ZIP file

    Raises:
      ParseError: missing files or fields
      ParseImplementationError: unknown file or field (if "allow" is False)
    """
    # check that we are asking for a valid and known source
    operator, link = operator.strip(), link.strip()
    if not operator or operator not in self._db.files.files:
      raise Error(f'invalid operator {operator!r}')
    operator_files: dict[str, Optional[FileMetadata]] = self._db.files.files[operator]
    if not link or link not in operator_files:
      raise Error(f'invalid URL {link!r}')
    # load ZIP from URL
    done_files: set[str] = set()
    file_name: str
    self._InvalidateCaches()
    with urllib.request.urlopen(link) as gtfs_zip:
      # extract files from ZIP
      gtfs_zip_bytes: bytes = gtfs_zip.read()
      logging.info(
          'Loading %r data, %s,from %r',
          operator, base.HumanizedBytes(len(gtfs_zip_bytes)), link)
      for file_name, file_data in _UnzipFiles(io.BytesIO(gtfs_zip_bytes)):
        file_name = file_name.strip()
        location = _TableLocation(operator=operator, link=link, file_name=file_name)
        try:
          self._LoadGTFSFile(location, file_data, allow_unknown_file, allow_unknown_field)
        except ParseIdenticalVersionError as err:
          if force_replace:
            logging.warning('Replacing existing data: %s', err)
            continue
          logging.warning('Version already known (will SKIP): %s', err)
          return
        finally:
          done_files.add(file_name)
    # finished loading the files, check that we loaded all required files
    if (missing_files := _REQUIRED_FILES - done_files):
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
      parsed_row: dict[str, Union[None, str, int, float, bool]] = {}
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

  # HANDLER TEMPLATE (copy and uncomment)
  # def _HandleTABLENAMERow(
  #     self, location: _TableLocation, count: int, row: dict[str, Optional[str]]) -> None:
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
      self, location: _TableLocation, count: int, row: _ExpectedFeedInfoCSVRowType) -> None:
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
    start: datetime.date = _DATE_OBJ(row['feed_start_date'])
    end: datetime.date = _DATE_OBJ(row['feed_end_date'])
    if start > end:
      raise RowError(f'incompatible start/end dates in {location}: {row}')
    # check against current version (and log)
    tm: float = time.time()
    current_data: Optional[FileMetadata] = self._db.files.files[location.operator][location.link]
    if current_data is None:
      logging.info(
          'Loading version %r @ %s for %s/%s',
          row['feed_version'], base.STD_TIME_STRING(tm), location.operator, location.link)
    else:
      if (row['feed_version'] == current_data.version and
          row['feed_publisher_name'] == current_data.publisher and
          row['feed_lang'] == current_data.language and
          start == current_data.start and
          end == current_data.end):
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
    self._db.files.files[location.operator][location.link] = FileMetadata(
        tm=tm, publisher=row['feed_publisher_name'], url=row['feed_publisher_url'],
        language=row['feed_lang'], start=start, end=end,
        version=row['feed_version'], email=row['feed_contact_email'])

  def _HandleAgencyRow(
      self, location: _TableLocation, count: int, row: _ExpectedAgencyCSVRowType) -> None:
    """Handler: "agency.txt" Transit agencies.

    pk: agency_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    # there can be only one!
    if count != 0:
      raise RowError(
          f'agency.txt table ({location}) is only supported to have 1 row (got {count}): {row}')
    # check
    if row['agency_timezone'] != 'Europe/London':
      raise NotImplementedError(f'For now timezones are only UTC (got {row["agency_timezone"]})')
    # update
    self._db.agencies[row['agency_id']] = Agency(
        id=row['agency_id'], name=row['agency_name'], url=row['agency_url'],
        zone=row['agency_timezone'], routes={})

  def _HandleCalendarRow(
      self, location: _TableLocation, count: int, row: _ExpectedCalendarCSVRowType) -> None:
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
    start: datetime.date = _DATE_OBJ(row['start_date'])
    end: datetime.date = _DATE_OBJ(row['end_date'])
    if start > end:
      raise RowError(f'inconsistent row @{count} / {location}: {row}')
    # update
    self._db.calendar[row['service_id']] = CalendarService(
        id=row['service_id'],
        week=(row['sunday'], row['monday'], row['tuesday'], row['wednesday'],
              row['thursday'], row['friday'], row['saturday']),
        start=start, end=end, exceptions={})

  def _HandleCalendarDatesRow(
      self, unused_location: _TableLocation, unused_count: int,
      row: _ExpectedCalendarDatesCSVRowType) -> None:
    """Handler: "calendar_dates.txt" Exceptions for the services defined in the calendar table.

    pk: (calendar/service_id, date) / ref: calendar/service_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    self._db.calendar[row['service_id']].exceptions[_DATE_OBJ(row['date'])] = row['exception_type']

  def _HandleRoutesRow(
      self, unused_location: _TableLocation, unused_count: int,
      row: _ExpectedRoutesCSVRowType) -> None:
    """Handler: "routes.txt" Routes: group of trips that are displayed to riders as a single service.

    pk: route_id / ref: agency/agency_id

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 0
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    self._db.agencies[row['agency_id']].routes[row['route_id']] = Route(
        id=row['route_id'], agency=row['agency_id'], short_name=row['route_short_name'],
        long_name=row['route_long_name'], route_type=RouteType(row['route_type']),
        description=row['route_desc'], url=row['route_url'],
        color=row['route_color'], text_color=row['route_text_color'], trips={})

  def _HandleShapesRow(
      self, location: _TableLocation, count: int, row: _ExpectedShapesCSVRowType) -> None:
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
      raise RowError(f'empty/invalid row @{count} / {location}: {row}')
    # update
    if row['shape_id'] not in self._db.shapes:
      self._db.shapes[row['shape_id']] = Shape(id=row['shape_id'], points={})
    self._db.shapes[row['shape_id']].points[row['shape_pt_sequence']] = ShapePoint(
        id=row['shape_id'], seq=row['shape_pt_sequence'],
        latitude=row['shape_pt_lat'], longitude=row['shape_pt_lon'],
        distance=row['shape_dist_traveled'])

  def _HandleTripsRow(
      self, location: _TableLocation, count: int, row: _ExpectedTripsCSVRowType) -> None:
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
    agency: Optional[Agency] = self._FindRoute(row['route_id'])
    if agency is None:
      raise RowError(f'agency in row was not found @{count} / {location}: {row}')
    # update
    self._db.agencies[agency.id].routes[row['route_id']].trips[row['trip_id']] = Trip(
        id=row['trip_id'], route=row['route_id'], agency=agency.id,
        service=row['service_id'], shape=row['shape_id'], headsign=row['trip_headsign'],
        name=row['trip_short_name'], block=row['block_id'],
        direction=row['direction_id'], stops={})

  def _HandleStopsRow(
      self, location: _TableLocation, count: int, row: _ExpectedStopsCSVRowType) -> None:
    """Handler: "stops.txt" Stops where vehicles pick up or drop off riders.

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
    location_type: LocationType = LocationType(row['location_type']) if row['location_type'] else LocationType.STOP
    if not -90.0 <= row['stop_lat'] <= 90.0 or not -180.0 <= row['stop_lon'] <= 180.0:
      raise RowError(f'invalid latitude/longitude @{count} / {location}: {row}')
    if row['parent_station'] and row['parent_station'] not in self._db.stops:
      raise RowError(f'parent_station in row was not found @{count} / {location}: {row}')
    # update
    self._db.stops[row['stop_id']] = BaseStop(
        id=row['stop_id'], parent=row['parent_station'], code=row['stop_code'],
        name=row['stop_name'], latitude=row['stop_lat'], longitude=row['stop_lon'],
        zone=row['zone_id'], description=row['stop_desc'],
        url=row['stop_url'], location=location_type)

  def _HandleStopTimesRow(
      self, location: _TableLocation, count: int, row: _ExpectedStopTimesCSVRowType) -> None:
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
    pickup: StopPointType = StopPointType(row['pickup_type']) if row['pickup_type'] else StopPointType.REGULAR
    dropoff: StopPointType = StopPointType(row['drop_off_type']) if row['drop_off_type'] else StopPointType.REGULAR
    if arrival < 0 or departure < 0 or arrival > departure:
      raise RowError(f'invalid row @{count} / {location}: {row}')
    if row['stop_id'] not in self._db.stops:
      raise RowError(f'stop_id in row was not found @{count} / {location}: {row}')
    agency, route = self._FindTrip(row['trip_id'])
    if not agency or not route:
      raise RowError(f'trip_id in row was not found @{count} / {location}: {row}')
    # update
    self._db.agencies[agency.id].routes[route.id].trips[row['trip_id']].stops[row['stop_sequence']] = Stop(
        id=row['trip_id'], seq=row['stop_sequence'], stop=row['stop_id'],
        agency=agency.id, route=route.id, arrival=arrival, departure=departure,
        timepoint=row['timepoint'], headsign=row['stop_headsign'],
        pickup=pickup, dropoff=dropoff)

  def LoadData(
      self, freshness: int = _DEFAULT_DAYS_FRESHNESS, force_replace: bool = False) -> None:
    """Downloads and parses GTFS data.

    Args:
      freshness: (default 1) Number of days before data is not fresh anymore and
          has to be reloaded from source
      force_replace: (default False) If True will parse a repeated version of the ZIP file
    """
    # first load the list of GTFS, if needed
    if (age := _DAYS_OLD(self._db.files.tm)) > freshness:
      logging.info('Loading stations (%0.1f days old)', age)
      self._LoadCSVSources()
    else:
      logging.info('Stations are fresh (%0.1f days old) - SKIP', age)
    # load GTFS data we are interested in
    self._LoadGTFSSource(
        'Iarnród Éireann / Irish Rail',
        'https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip',
        force_replace=force_replace)


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
    for n in _LOAD_ORDER[::-1]:
      if n in file_names:
        file_names.remove(n)
        file_names.insert(0, n)
    for file_name in file_names:
      with zip_ref.open(file_name) as file_data:
        yield (file_name, file_data.read())


def HMSToSeconds(time_str: str) -> int:
  """Accepts 'H:MM:SS' or 'HH:MM:SS' and returns total seconds since 00:00:00.

  Supports hours ≥ 0 with no upper bound.

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


def Main() -> None:
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
      '-r', '--replace', type=int, default=0,
      help='0 == does not load the same version again ; 1 == forces replace version (default: 0)')
  # "print" command
  _: argparse.ArgumentParser = command_arg_subparsers.add_parser(
      'print', help='Print DB')
  # ALL commands
  # parser.add_argument(
  #     '-r', '--readonly', type=bool, default=False,
  #     help='If "True" will not save database (default: False)')
  args: argparse.Namespace = parser.parse_args()
  command = args.command.lower().strip() if args.command else ''
  # start
  print(f'{base.TERM_BLUE}{base.TERM_BOLD}***********************************************')
  print(f'**                 {base.TERM_LIGHT_RED}GTFS DB{base.TERM_BLUE}                   **')
  print('**   balparda@gmail.com (Daniel Balparda)    **')
  print(f'***********************************************{base.TERM_END}')
  success_message: str = f'{base.TERM_WARNING}premature end? user paused?'
  try:
    # open DB, create directory if needed
    if not os.path.isdir(_DATA_DIR):
      os.mkdir(_DATA_DIR)
      logging.info('Created data directory: %s', _DATA_DIR)
    database = GTFS(_DEFAULT_DB_FILE)
    # execute the command
    print()
    with base.Timer() as op_timer:
      # "read" command
      if command == 'read':
        try:
          database.LoadData(freshness=args.freshness, force_replace=bool(args.replace))
        finally:
          database.Save()
      # "print" command
      elif command == 'print':
        raise NotImplementedError()
      # no valid command
      else:
        parser.print_help()
      print()
      print()
    print(f'Executed in {base.TERM_GREEN}{op_timer.readable}{base.TERM_END}')
    print()
    success_message = f'{base.TERM_GREEN}success'
  except Exception as err:
    success_message = f'{base.TERM_FAIL}error: {err}'
    raise
  finally:
    print(f'{base.TERM_BLUE}{base.TERM_BOLD}THE END: {success_message}{base.TERM_END}')


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  Main()
