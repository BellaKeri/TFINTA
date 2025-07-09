#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=too-many-instance-attributes
"""Irish Rail Realtime data model.

See: https://api.irishrail.ie/realtime/
"""

import dataclasses
import datetime
import enum
import functools
# import pdb
from typing import Any, Callable, TypedDict

from . import tfinta_base as base

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = base.__version__


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
  location: base.Point | None = None
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


class TrainStatus(enum.Enum):
  """Train status."""
  TERMINATED = 0
  NOT_YET_RUNNING = 1
  RUNNING = 2


TRAIN_STATUS_STR_MAP: dict[str, TrainStatus] = {
    'T': TrainStatus.TERMINATED,
    'R': TrainStatus.RUNNING,
    'N': TrainStatus.NOT_YET_RUNNING,
}

TRAIN_STATUS_STR: dict[TrainStatus, str] = {
    TrainStatus.TERMINATED: f'{base.YELLOW}\u2717{base.NULL}',    # ✗
    TrainStatus.NOT_YET_RUNNING: f'{base.RED}\u25A0{base.NULL}',  # ■
    TrainStatus.RUNNING: f'{base.GREEN}\u25BA{base.NULL}',        # ►
}


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class RunningTrain(RealtimeRPCData):
  """Realtime: Running Train."""
  code: str
  status: TrainStatus
  day: datetime.date
  direction: str
  message: str
  position: base.Point | None

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, RunningTrain):
      raise TypeError(f'invalid RunningTrain type comparison {self!r} versus {other!r}')
    if self.status != other.status:
      return self.status.value > other.status.value  # note the reversal
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
  LOCO = 4  # loco-hauled services


TRAIN_TYPE_STR_MAP: dict[str, TrainType] = {
    'DMU': TrainType.DMU,
    'DART': TrainType.DART,
    'DART10': TrainType.DART,
    'ICR': TrainType.ICR,
    'TRAIN': TrainType.LOCO,
}


class LocationType(enum.Enum):
  """Location type."""
  STOP = 0
  ORIGIN = 1
  DESTINATION = 2
  TIMING_POINT = 3
  CREW_RELIEF_OR_CURRENT = 4


LOCATION_TYPE_STR_MAP: dict[str, LocationType] = {
    'S': LocationType.STOP,
    'O': LocationType.ORIGIN,
    'D': LocationType.DESTINATION,
    'T': LocationType.TIMING_POINT,
    'C': LocationType.CREW_RELIEF_OR_CURRENT,
}

LOCATION_TYPE_STR: dict[LocationType, str] = {
    LocationType.ORIGIN: f'{base.GREEN}ORIGIN{base.NULL}',
    LocationType.DESTINATION: f'{base.GREEN}DESTINATION{base.NULL}',
    LocationType.STOP: f'{base.GREEN}\u25A0{base.NULL}',                          # ■
    LocationType.TIMING_POINT: f'{base.RED}\u23F1{base.NULL}',                    # ⏱
    LocationType.CREW_RELIEF_OR_CURRENT: f'{base.GREEN}\u25A0\u25A0{base.NULL}',  # ■■
}


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class StationLineQueryData(RealtimeRPCData):
  """Realtime: Board/Station/Query info."""
  tm_server: datetime.datetime
  tm_query: base.DayTime
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
  destination_code: str
  destination_name: str
  trip: base.DayRange
  direction: str
  due_in: base.DayTime
  late: int
  location_type: LocationType
  status: str | None
  scheduled: base.DayRange
  expected: base.DayRange
  train_type: TrainType = TrainType.UNKNOWN
  last_location: str | None = None

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, StationLine):
      raise TypeError(f'invalid StationLine type comparison {self!r} versus {other!r}')
    if self.due_in != other.due_in:
      return self.due_in < other.due_in
    if self.expected != other.expected:
      return self.expected < other.expected
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
  scheduled: base.DayRange
  expected: base.DayRange
  actual: base.DayRange

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
  stations: dict[str, Station]                  # {station_code: Station}
  running_tm: float | None
  running_trains: dict[str, RunningTrain]       # {train_code: RunningTrain}
  station_boards: dict[str, tuple[              # {station_code: (tm, query_data, list[lines])}
      float, StationLineQueryData, list[StationLine]]]
  trains: dict[str, dict[datetime.date, tuple[  # {train_code: {day: (tm, query, {seq: train_stop})}}
      float, TrainStopQueryData, dict[int, TrainStop]]]]


PRETTY_AUTO: Callable[[bool], str] = lambda b: f'{base.GREEN}\u2699{base.NULL}' if b else ''  # ⚙
