#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=too-many-instance-attributes
"""GTFS Data Model: defines the data storage and the CSV formats.

See: https://gtfs.org/documentation/schedule/reference/
"""

import dataclasses
import datetime
import enum
import functools
# import pdb
from typing import Any, Callable, TypedDict
import zoneinfo

from . import tfinta_base as base

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = base.__version__


####################################################################################################
# BASIC CONSTANTS
####################################################################################################


# URLs and basic names for known parts of the Irish system
IRISH_RAIL_OPERATOR = 'Iarnród Éireann / Irish Rail'
OFFICIAL_GTFS_CSV = 'https://www.transportforireland.ie/transitData/Data/GTFS%20Operator%20Files.csv'
IRISH_RAIL_LINK = 'https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip'
KNOWN_OPERATORS: set[str] = {
    # the operators we care about and will load GTFS for
    IRISH_RAIL_OPERATOR,
}
DART_SHORT_NAME = 'DART'
DART_LONG_NAME = 'Bray - Howth'

# Files
REQUIRED_FILES: set[str] = {
    'feed_info.txt',  # required because it has the date ranges and the version info
}
LOAD_ORDER: list[str] = [
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


####################################################################################################
# BASIC GTFS DATA MODEL: Used to parse and store GTFS data
####################################################################################################


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class FileMetadata:
  """GTFS file metadata (mostly from loading feed_info.txt tables)."""
  tm: float        # timestamp of first load of this version of this GTFS ZIP file
  publisher: str   # feed_info.txt/feed_publisher_name           (required)
  url: str         # feed_info.txt/feed_publisher_url            (required)
  language: str    # feed_info.txt/feed_lang                     (required)
  days: base.DaysRange      # feed_info.txt/feed_start_date+feed_end_date (required)
  version: str              # feed_info.txt/feed_version                  (required)
  email: str | None = None  # feed_info.txt/feed_contact_email


class ExpectedFeedInfoCSVRowType(TypedDict):
  """feed_info.txt"""
  feed_publisher_name: str
  feed_publisher_url: str
  feed_lang: str
  feed_start_date: str
  feed_end_date: str
  feed_version: str
  feed_contact_email: str | None


class LocationType(enum.Enum):
  """Location type."""
  # https://gtfs.org/documentation/schedule/reference/?utm_source=chatgpt.com#stopstxt
  STOP = 0           # (or empty) - Stop (or Platform). A location where passengers board or disembark from a transit vehicle. Is called a platform when defined within a parent_station
  STATION = 1        # A physical structure or area that contains one or more platform
  ENTRANCE_EXIT = 2  # A location where passengers can enter or exit a station from the street. If an entrance/exit belongs to multiple stations, it may be linked by pathways to both, but the data provider must pick one of them as parent
  STATION_NODE = 3   # A location within a station, not matching any other location_type, that may be used to link together pathways define in pathways.txt
  BOARDING_AREA = 4  # A specific location on a platform, where passengers can board and/or alight vehicles


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class BaseStop:  # stops.txt
  """Stop where vehicles pick up or drop-off riders."""
  id: str                # (PK) stops.txt/stop_id (required)
  code: str              # stops.txt/stop_code    (required)
  name: str              # stops.txt/stop_name    (required)
  point: base.Point      # stops.txt/stop_lat+stop_lon - WGS84 latitude & longitude
  location: LocationType = LocationType.STOP  # stops.txt/location_type
  zone: str | None = None         # stops.txt/zone_id
  description: str | None = None  # stops.txt/stop_desc
  url: str | None = None          # stops.txt/stop_url
  parent: str | None = None  # stops.txt/parent_station -> stops.txt/stop_id

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, BaseStop):
      raise TypeError(f'invalid BaseStop type comparison {self!r} versus {other!r}')
    return self.name < other.name


class ExpectedStopsCSVRowType(TypedDict):
  """stops.txt"""
  stop_id: str
  parent_station: str | None
  stop_code: str
  stop_name: str
  stop_lat: float
  stop_lon: float
  zone_id: str | None
  stop_desc: str | None
  stop_url: str | None
  location_type: int | None


class StopPointType(enum.Enum):
  """Pickup/Drop-off type."""
  # https://gtfs.org/documentation/schedule/reference/?utm_source=chatgpt.com#stop_timestxt
  REGULAR = 0        # (or empty) Regularly scheduled pickup/drop-off
  NOT_AVAILABLE = 1  # No pickup/drop-off available
  AGENCY_ONLY = 2    # Must phone agency to arrange pickup/drop-off
  DRIVER_ONLY = 3    # Must coordinate with driver to arrange pickup/drop-off


STOP_TYPE_STR: dict[StopPointType, str] = {
    StopPointType.REGULAR: f'{base.GREEN}\u2713{base.NULL}',       # ✓
    StopPointType.NOT_AVAILABLE: f'{base.RED}\u2717{base.NULL}',   # ✗
    StopPointType.AGENCY_ONLY: f'{base.YELLOW}\u260E{base.NULL}',  # ☎
    StopPointType.DRIVER_ONLY: f'{base.YELLOW}\u2708{base.NULL}'   # ✈
}


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class ScheduleStop:
  """A timetable entry, with arrival & departure. Sortable (by departure first then arrival)."""
  times: base.DayRange    # stop_times.txt/arrival_time+departure_time - seconds from midnight, to represent 'HH:MM:SS' (required)
  timepoint: bool = True  # stop_times.txt/timepoint (required) - False==Times are considered approximate; True==Times are considered exact

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, ScheduleStop):
      raise TypeError(f'invalid ScheduleStop type comparison: {self!r} versus {other!r}')
    if self.timepoint != other.timepoint:
      raise TypeError(f'invalid mixed timepoint ScheduleStop comparison: {self!r} versus {other!r}')
    return self.times < other.times


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Stop:  # stop_times.txt
  """Time that a vehicle arrives/departs from a stop for a trip."""
  id: str    # (PK) stop_times.txt/trip_id            (required) -> trips.txt/trip_id
  seq: int   # (PK) stop_times.txt/stop_sequence      (required)
  stop: str  # stop_times.txt/stop_id                 (required) -> stops.txt/stop_id
  agency: int     # <<INFERRED>> -> agency.txt/agency_id
  route: str      # <<INFERRED>> -> routes.txt/route_id
  scheduled: ScheduleStop      # stop_times.txt/arrival_time+departure_time+timepoint - arrival & departure
  headsign: str | None = None  # stop_times.txt/stop_headsign
  pickup: StopPointType = StopPointType.REGULAR   # stop_times.txt/pickup_type
  dropoff: StopPointType = StopPointType.REGULAR  # stop_times.txt/drop_off_type


class ExpectedStopTimesCSVRowType(TypedDict):
  """stop_times.txt"""
  trip_id: str
  stop_sequence: int
  stop_id: str
  arrival_time: str
  departure_time: str
  timepoint: bool
  stop_headsign: str | None
  pickup_type: int | None
  drop_off_type: int | None
  dropoff_type: int | None  # legacy spelling, here for backwards compatibility


@functools.total_ordering  # limited sorting by ID only!!
@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class Trip:
  """Trip for a route."""
  id: str          # (PK) trips.txt/trip_id     (required)
  route: str       # trips.txt/route_id         (required) -> routes.txt/route_id
  agency: int      # <<INFERRED>> -> agency.txt/agency_id
  service: int     # trips.txt/service_id       (required) -> calendar.txt/service_id
  direction: bool  # trips.txt/direction_id     (required)
  # A trip_short_name value, if provided, should uniquely identify a trip within a service day
  stops: dict[int, Stop]       # {stop_times.txt/stop_sequence: Stop}
  shape: str | None = None     # trips.txt/shape_id -> shapes.txt/shape_id
  block: str | None = None     # trips.txt/block_id
  headsign: str | None = None  # trips.txt/trip_headsign
  name: str | None = None      # trips.txt/trip_short_name

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, Trip):
      raise TypeError(f'invalid Trip type comparison {self!r} versus {other!r}')
    return self.id < other.id  # we will sort only by ID for now!!


class ExpectedTripsCSVRowType(TypedDict):
  """trips.txt"""
  trip_id: str
  route_id: str
  service_id: int
  direction_id: bool
  shape_id: str | None
  trip_headsign: str | None
  block_id: str | None
  trip_short_name: str | None


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
  # Extended types, from https://ipeagit.github.io/gtfstools/reference/filter_by_route_type.html
  # 100-199 : detailed rail
  RAILWAY_SERVICE = 100       # N/A
  HIGH_SPEED_RAIL = 101       # TGV, ICE, Eurostar
  LONG_DISTANCE_RAIL = 102    # InterCity / EuroCity
  INTER_REGIONAL_RAIL = 103   # InterRegio, Cross-Country
  CAR_TRANSPORT_RAIL = 104
  SLEEPER_RAIL = 105          # Night trains / sleeper cars
  REGIONAL_RAIL = 106         # TER, Regionalzug
  TOURIST_RAILWAY = 107       # Heritage / tourist lines
  RAIL_SHUTTLE_WITHIN_COMPLEX = 108  # Airport shuttles, etc.
  SUBURBAN_RAIL = 109         # S-Bahn, RER
  REPLACEMENT_RAIL = 110      # Rail replacement (planned)
  SPECIAL_RAIL = 111
  LORRY_TRANSPORT_RAIL = 112
  ALL_RAIL = 113              # *All* rail services
  CROSS_COUNTRY_RAIL = 114
  VEHICLE_TRANSPORT_RAIL = 115
  RACK_AND_PINION_RAIL = 116  # Mountain cog railways
  ADDITIONAL_RAIL = 117
  # 200-299 : coach (inter-urban bus)
  COACH_SERVICE = 200
  INTERNATIONAL_COACH = 201  # Eurolines, Touring
  NATIONAL_COACH = 202       # National Express
  SHUTTLE_COACH = 203
  REGIONAL_COACH = 204
  SPECIAL_COACH = 205
  SIGHTSEEING_COACH = 206
  TOURIST_COACH = 207
  COMMUTER_COACH = 208
  ALL_COACH = 209
  # 400-499 : urban rail
  URBAN_RAILWAY = 400
  METRO = 401        # Métro de Paris
  UNDERGROUND = 402  # London Underground, U-Bahn
  URBAN_RAILWAY_SPECIAL = 403
  ALL_URBAN_RAILWAY = 404
  MONORAIL_URBAN = 405
  # 700-799 : detailed bus
  BUS_SERVICE_GENERAL = 700
  REGIONAL_BUS = 701
  EXPRESS_BUS = 702
  STOPPING_BUS = 703
  LOCAL_BUS = 704
  NIGHT_BUS = 705
  POST_BUS = 706
  SPECIAL_NEEDS_BUS = 707
  MOBILITY_BUS = 708
  MOBILITY_BUS_DISABLED = 709
  SIGHTSEEING_BUS = 710
  SHUTTLE_BUS = 711
  SCHOOL_BUS = 712
  SCHOOL_AND_PUBLIC_BUS = 713
  RAIL_REPLACEMENT_BUS = 714
  DEMAND_RESPONSE_BUS = 715
  ALL_BUS = 716
  # 800-899 : trolleybus
  TROLLEYBUS_SERVICE = 800
  # 900-999 : tram / light rail variants
  TRAM_SERVICE = 900
  CITY_TRAM = 901
  LOCAL_TRAM = 902
  REGIONAL_TRAM = 903
  SIGHTSEEING_TRAM = 904
  SHUTTLE_TRAM = 905
  ALL_TRAM = 906
  # 1000 : water
  WATER_TRANSPORT = 1000
  # 1100 : air
  AIR_SERVICE = 1100
  # 1200 : ferry (kept separate from 1000 in some feeds)
  FERRY_SERVICE_EXT = 1200
  # 1300-1399 : aerial lifts
  AERIAL_LIFT_SERVICE = 1300  # Telefèric de Montjuïc, etc.
  TELECABIN_SERVICE = 1301
  CABLE_CAR_SERVICE = 1302
  ELEVATOR_SERVICE = 1303
  CHAIR_LIFT_SERVICE = 1304
  DRAG_LIFT_SERVICE = 1305
  SMALL_TELECABIN_SERVICE = 1306
  ALL_TELECABIN = 1307
  # 1400 : funicular
  FUNICULAR_SERVICE = 1400  # Rigiblick (Zürich)
  # 1500-1599 : taxi
  TAXI_SERVICE = 1500
  COMMUNAL_TAXI = 1501      # Marshrutka, dolmuş
  WATER_TAXI = 1502
  RAIL_TAXI = 1503
  BIKE_TAXI = 1504
  LICENSED_TAXI = 1505
  PRIVATE_HIRE_VEHICLE = 1506
  ALL_TAXI = 1507
  # 1700-1799 : miscellaneous
  MISCELLANEOUS_SERVICE = 1700
  HORSE_DRAWN_CARRIAGE = 1702


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class Route:
  """Route: group of trips that are displayed to riders as a single service."""
  id: str                # (PK) routes.txt/route_id    (required)
  agency: int            # routes.txt/agency_id        (required) -> agency.txt/agency_id
  short_name: str        # routes.txt/route_short_name (required)
  long_name: str         # routes.txt/route_long_name  (required)
  route_type: RouteType  # routes.txt/route_type       (required)
  trips: dict[str, Trip]          # {trips.txt/trip_id: Trip}
  description: str | None = None  # routes.txt/route_desc
  url: str | None = None          # routes.txt/route_url
  color: str | None = None        # routes.txt/route_color: encoded as a six-digit hexadecimal number (https://htmlcolorcodes.com)
  text_color: str | None = None   # routes.txt/route_text_color: encoded as a six-digit hexadecimal number


class ExpectedRoutesCSVRowType(TypedDict):
  """routes.txt"""
  route_id: str
  agency_id: int
  route_short_name: str
  route_long_name: str
  route_type: int
  route_desc: str | None
  route_url: str | None
  route_color: str | None
  route_text_color: str | None


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class Agency:
  """Transit agency."""
  id: int    # (PK) agency.txt/agency_id (required)
  name: str  # agency.txt/agency_name    (required)
  url: str   # agency.txt/agency_url     (required)
  zone: zoneinfo.ZoneInfo   # agency.txt/agency_timezone: TZ timezone from the https://www.iana.org/time-zones (required)
  routes: dict[str, Route]  # {routes.txt/route_id: Route}


class ExpectedAgencyCSVRowType(TypedDict):
  """agency.txt"""
  agency_id: int
  agency_name: str
  agency_url: str
  agency_timezone: str


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class CalendarService:
  """Service dates specified using a weekly schedule & start/end dates. Includes the exceptions."""
  id: int  # (PK) calendar.txt/service_id (required)
  week: tuple[bool, bool, bool, bool, bool, bool, bool]  # calendar.txt/monday...sunday (required)
  days: base.DaysRange                   # calendar.txt/start_date+end_date             (required)
  exceptions: dict[datetime.date, bool]  # {calendar_dates.txt/date: has_service?}
  # where `has_service` comes from calendar_dates.txt/exception_type


class ExpectedCalendarCSVRowType(TypedDict):
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


class ExpectedCalendarDatesCSVRowType(TypedDict):
  """calendar_dates.txt"""
  service_id: int
  date: str
  exception_type: str  # cannot be bool: field is '1'==added service;'2'==removed service


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class ShapePoint:
  """Point in a shape, a place in the real world."""
  id: str            # (PK) shapes.txt/shape_id          (required) -> shapes.txt/shape_id
  seq: int           # (PK) shapes.txt/shape_pt_sequence (required)
  point: base.Point  # shapes.txt/shape_pt_lat+shape_pt_lon - WGS84 latitude & longitude
  distance: float    # shapes.txt/shape_dist_traveled    (required)

  def __post_init__(self) -> None:
    if self.distance < 0.0:
      raise base.Error(f'invalid distance: {self}')

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, ShapePoint):
      raise TypeError(f'invalid ShapePoint type comparison {self!r} versus {other!r}')
    return self.seq < other.seq  # we will sort only by ID for now!!


class ExpectedShapesCSVRowType(TypedDict):
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
  files: dict[str, dict[str, FileMetadata | None]]  # {provider: {url: FileMetadata}}


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
class GTFSData:
  """GTFS data."""
  tm: float             # timestamp of last DB save
  files: OfficialFiles  # the available GTFS files
  agencies: dict[int, Agency]           # {agency.txt/agency_id, Agency}
  calendar: dict[int, CalendarService]  # {calendar.txt/service_id, CalendarService}
  shapes: dict[str, Shape]              # {shapes.txt/shape_id, Shape}
  stops: dict[str, BaseStop]            # {stops.txt/stop_id, BaseStop}


####################################################################################################
# DERIVED DATA MODEL: Derived from GTFS data, used to do higher-level logic
####################################################################################################


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class TrackStop:
  """A track stop."""
  stop: str                    # stop_times.txt/stop_id (required) -> stops.txt/stop_id
  name: str                    # stops.txt/stop_name    (required)
  # even though the name is redundant, if we don't add it here it becomes hard to sort (for example)
  headsign: str | None = None  # stop_times.txt/stop_headsign
  pickup: StopPointType = StopPointType.REGULAR   # stop_times.txt/pickup_type
  dropoff: StopPointType = StopPointType.REGULAR  # stop_times.txt/drop_off_type

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, TrackStop):
      raise TypeError(f'invalid TrackStop type comparison {self!r} versus {other!r}')
    return self.name < other.name


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Schedule:
  """A track scheduled (timed) route. A track + timetable, basically. Sortable."""
  direction: bool             # trips.txt/direction_id (required)
  stops: tuple[TrackStop]     # (tuple so it is hashable!)
  times: tuple[ScheduleStop]  # (tuple so it is hashable!)

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, Schedule):
      raise TypeError(f'invalid Schedule type comparison {self!r} versus {other!r}')
    if self.direction != other.direction:
      return self.direction < other.direction
    if self.stops[0] != other.stops[0]:
      return self.stops[0] < other.stops[0]
    if self.stops[-1] != other.stops[-1]:
      return self.stops[-1] < other.stops[-1]
    return self.times[0] < other.times[0]


# useful

DART_DIRECTION: Callable[[Trip | Schedule], str] = (
    lambda t: f'{base.LIGHT_BLUE}S{base.NULL}' if t.direction else f'{base.LIGHT_RED}N{base.NULL}')

NULL_STOP = Stop(
    id='', seq=0, stop='', agency=0, route='',
    scheduled=ScheduleStop(times=base.DayRange(
        arrival=base.DayTime(time=0), departure=base.DayTime(time=0))),
    pickup=StopPointType.NOT_AVAILABLE, dropoff=StopPointType.NOT_AVAILABLE)
