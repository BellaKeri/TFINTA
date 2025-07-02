#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=too-many-instance-attributes
"""Irish Rail Realtime data model.

See: https://api.irishrail.ie/realtime/
"""

import collections
import dataclasses
import datetime
import enum
import functools
# import pdb
from typing import Any, Callable, TypedDict

from . import tfinta_base as base

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 4)  # v1.4 - 2025/06/28


####################################################################################################
# BASIC CONSTANTS
####################################################################################################


####################################################################################################
# BASIC REALTIME DATA MODEL: Used to parse and store realtime data
####################################################################################################


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class RealtimeRPCData:
  """Realtime data object."""


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Station(RealtimeRPCData):
  """Realtime: Station."""
  id: int
  code: str         # 5-letter uppercase code (ex: 'LURGN')
  description: str  # name (ex: 'Lurgan')
  location: base.Point
  alias: str | None = None

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, Station):
      raise TypeError(f'invalid Station type comparison {self!r} versus {other!r}')
    return self.description < other.description


class ExpectedStationXMLRowType(TypedDict):
  """getAllStationsXML/objStation"""
  StationId: int
  StationCode: str
  StationDesc: str
  StationLatitude: float
  StationLongitude: float
  StationAlias: str | None


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class RunningTrain(RealtimeRPCData):
  """Realtime: Running Train."""
  code: str
  is_running: bool
  day: datetime.date
  direction: str
  message: str
  position: base.Point | None

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, RunningTrain):
      raise TypeError(f'invalid RunningTrain type comparison {self!r} versus {other!r}')
    if self.is_running != other.is_running:
      return self.is_running > other.is_running  # note the reversal
    return self.code < other.code


class ExpectedRunningTrainXMLRowType(TypedDict):
  """getCurrentTrainsXML/objTrainPositions"""
  TrainCode: str
  TrainStatus: str  # 'R'==running; 'N'==not yet running
  TrainDate: str
  Direction: str
  TrainLatitude: float
  TrainLongitude: float
  PublicMessage: str


class TrainType(enum.Enum):
  """Train type."""
  UNKNOWN = 0
  DMU = 1   # Diesel-multiple-unit commuter sets
  DART = 2  # DART (Dublin Area Rapid Transit) electric suburban, 'DART' or 'DART10' values
  ICR = 3   # 22000-class InterCity Railcars


TRAIN_TYPE_STR_MAP: dict[str, TrainType] = {
    'DMU': TrainType.DMU,
    'DART': TrainType.DART,
    'DART10': TrainType.DART,
    'ICR': TrainType.ICR,
}


class LocationType(enum.Enum):
  """Location type."""
  STOP = 0
  ORIGIN = 1
  DESTINATION = 2
  TIMING_POINT = 3


LOCATION_TYPE_STR_MAP: dict[str, LocationType] = {
    'S': LocationType.STOP,
    'O': LocationType.ORIGIN,
    'D': LocationType.DESTINATION,
    'T': LocationType.TIMING_POINT,
}

LOCATION_TYPE_STR: dict[LocationType, str] = {
    LocationType.ORIGIN: f'{base.GREEN}ORIGIN{base.NULL}',
    LocationType.DESTINATION: f'{base.GREEN}DESTINATION{base.NULL}',
    LocationType.STOP: f'{base.GREEN}\u25A0{base.NULL}',  # ■
    LocationType.TIMING_POINT: f'{base.RED}\u23F1{base.NULL}'   # ⏱
}


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class StationLineQueryData(RealtimeRPCData):
  """Realtime: Board/Station/Query info."""
  tm_server: datetime.datetime
  tm_query: int
  station_name: str
  station_code: str
  day: datetime.date

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, StationLineQueryData):
      raise TypeError(f'invalid StationLineQueryData type comparison {self!r} versus {other!r}')
    if self.station_name != other.station_name:
      return self.station_name < other.station_name
    return self.tm_server < other.tm_server


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class StationLine(RealtimeRPCData):
  """Realtime: Station Board Line."""
  query: StationLineQueryData
  train_code: str
  origin_code: str
  origin_name: str
  origin_time: int
  destination_code: str
  destination_name: str
  destination_time: int
  direction: str
  due_in: int
  late: int
  location_type: LocationType
  status: str | None
  scheduled_arrival: int | None  # not having arrival==beginning of line
  scheduled_depart: int | None   # must have either arrival or departure
  expected_arrival: int | None   # same as above
  expected_depart: int | None
  train_type: TrainType = TrainType.UNKNOWN
  last_location: str | None = None

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, StationLine):
      raise TypeError(f'invalid StationLine type comparison {self!r} versus {other!r}')
    my_time: int | None = self.expected_arrival if self.expected_arrival else self.expected_depart
    other_time: int | None = (
        other.expected_arrival if other.expected_arrival else other.expected_depart)
    if my_time and other_time and my_time != other_time:
      return my_time < other_time
    return self.destination_name < other.destination_name


class ExpectedStationLineXMLRowType(TypedDict):
  """getStationDataByCodeXML/objStationData"""
  Servertime: str
  Traincode: str
  Stationfullname: str
  Stationcode: str
  Querytime: str
  Traindate: str
  Origin: str
  Destination: str
  Origintime: str
  Destinationtime: str
  Status: str | None
  Lastlocation: str | None
  Duein: int
  Late: int
  Exparrival: str
  Expdepart: str
  Scharrival: str
  Schdepart: str
  Direction: str
  Traintype: str
  Locationtype: str  # O=Origin, S=Stop, T=TimingPoint (non stopping location), D=Destination


class StopType(enum.Enum):
  """Stop type."""
  UNKNOWN = 0
  CURRENT = 1
  NEXT = 2


STOP_TYPE_STR_MAP: dict[str, StopType] = {
    'C': StopType.CURRENT,
    'N': StopType.NEXT,
    '-': StopType.UNKNOWN,
}


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class TrainStopQueryData(RealtimeRPCData):
  """Realtime: Train/Query info."""
  train_code: str
  day: datetime.date
  origin_code: str
  origin_name: str
  destination_code: str
  destination_name: str

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, TrainStopQueryData):
      raise TypeError(f'invalid TrainStopQueryData type comparison {self!r} versus {other!r}')
    if self.origin_name != other.origin_name:
      return self.origin_name < other.origin_name
    if self.destination_name != other.destination_name:
      return self.destination_name < other.destination_name
    return self.train_code < other.train_code


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class TrainStop(RealtimeRPCData):
  """Realtime: Train Station."""
  query: TrainStopQueryData
  auto_arrival: bool
  auto_depart: bool
  location_type: LocationType
  stop_type: StopType  # C=Current, N=Next
  station_order: int
  station_code: str
  station_name: str | None
  arrival: int | None
  departure: int | None
  scheduled_arrival: int | None
  scheduled_depart: int | None
  expected_arrival: int | None
  expected_depart: int | None

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, TrainStop):
      raise TypeError(f'invalid TrainStop type comparison {self!r} versus {other!r}')
    return self.station_order < other.station_order


class ExpectedTrainStopXMLRowType(TypedDict):
  """getTrainMovementsXML/objTrainMovements"""
  TrainCode: str
  TrainDate: str
  LocationCode: str
  LocationFullName: str | None
  LocationOrder: int
  LocationType: str  # O=Origin, S=Stop, T=TimingPoint (non stopping location), D =Destination
  TrainOrigin: str
  TrainDestination: str
  ScheduledArrival: str
  ScheduledDeparture: str
  ExpectedArrival: str
  ExpectedDeparture: str
  Arrival: str | None
  Departure: str | None
  AutoArrival: bool | None
  AutoDepart: bool | None
  StopType: str


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)
class LatestData:
  """Realtime: latest fetched data."""
  stations_tm: float | None
  stations: collections.OrderedDict[str, Station]  # {station_code: Station}
  running_tm: float | None
  running_trains: collections.OrderedDict[str, RunningTrain]  # {train_code: RunningTrain}
  station_boards: dict[str, tuple[  # {station_code: (tm, query_data, list[lines])}
      float, StationLineQueryData, list[StationLine]]]
  trains: dict[str, dict[datetime.date, tuple[  # {train_code: {day: (tm, query, {seq: train_stop})}}
      float, TrainStopQueryData, dict[int, TrainStop]]]]


# useful

PRETTY_RUNNING_STOPPED: Callable[[bool], str] = (
    lambda b: f'{base.GREEN}\u25BA{base.NULL}' if b else f'{base.RED}\u25A0{base.NULL}')  # ► / ■
PRETTY_AUTO: Callable[[bool], str] = lambda b: f'{base.GREEN}\u2699{base.NULL}' if b else ''  # ⚙
