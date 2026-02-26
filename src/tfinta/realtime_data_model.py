# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Irish Rail Realtime data model.

See: https://api.irishrail.ie/realtime/
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
import functools
from collections import abc
from typing import Literal, TypedDict

import pydantic

from . import tfinta_base as base

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
  code: str  # 5-letter uppercase code (ex: 'LURGN')
  description: str  # name (ex: 'Lurgan')
  location: base.Point | None = None
  alias: str | None = None

  def __lt__(self, other: Station) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (Any): Other object to compare against.

    Returns:
        bool: True if this Station is less than the other, False otherwise.

    """
    return self.description < other.description


class ExpectedStationXMLRowType(TypedDict):
  """getAllStationsXML/objStation."""

  StationId: int
  StationCode: str
  StationDesc: str
  StationLatitude: float
  StationLongitude: float
  StationAlias: str | None


class StationModel(pydantic.BaseModel):
  """A rail station."""

  id: int = pydantic.Field(description='Unique station ID, e.g. 140 for Bray')
  code: str = pydantic.Field(description='5-letter uppercase code, e.g. LURGN')
  description: str = pydantic.Field(description='Station name, e.g. Bray')
  location: base.PointModel | None = pydantic.Field(
    default=None, description='Geographical location of the station'
  )
  alias: str | None = pydantic.Field(
    default=None, description='Alternative name or alias for the station'
  )

  @classmethod
  def from_domain(cls, s: Station) -> StationModel:
    """Convert domain ``Station`` to Pydantic model.

    Returns:
      StationModel: converted model.

    """
    return cls(
      id=s.id,
      code=s.code,
      description=s.description,
      location=base.PointModel.from_domain(s.location),
      alias=s.alias,
    )


class StationsResponse(pydantic.BaseModel):
  """Response for the stations endpoint."""

  count: int = pydantic.Field(description='Number of stations returned')
  stations: list[StationModel] = pydantic.Field(description='List of stations')


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
  TrainStatus.TERMINATED: '[yellow]\u2717[/]',  # ✗
  TrainStatus.NOT_YET_RUNNING: '[red]\u25a0[/]',  # ■
  TrainStatus.RUNNING: '[green]\u25ba[/]',  # ►
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

  def __lt__(self, other: RunningTrain) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (Any): Other object to compare against.

    Returns:
        bool: True if this RunningTrain is less than the other, False otherwise.

    """
    if self.status != other.status:
      return self.status.value > other.status.value  # note the reversal
    return self.code < other.code


class ExpectedRunningTrainXMLRowType(TypedDict):
  """getCurrentTrainsXML/objTrainPositions."""

  TrainCode: str
  TrainStatus: str  # 'R'==running; 'N'==not yet running
  TrainDate: str
  Direction: str
  TrainLatitude: float
  TrainLongitude: float
  PublicMessage: str


# Type aliases for enum-as-string literals (appear as enum constraints in OpenAPI)
TrainStatusLiteral = Literal['TERMINATED', 'NOT_YET_RUNNING', 'RUNNING']
TrainTypeLiteral = Literal['UNKNOWN', 'DMU', 'DART', 'ICR', 'LOCO']
LocationTypeLiteral = Literal[
  'STOP',
  'ORIGIN',
  'DESTINATION',
  'TIMING_POINT',
  'CREW_RELIEF_OR_CURRENT',
]
StopTypeLiteral = Literal['UNKNOWN', 'CURRENT', 'NEXT']


class RunningTrainModel(pydantic.BaseModel):
  """A currently running train."""

  code: str = pydantic.Field(description='Train code, e.g. 22000 or DART10')
  status: TrainStatusLiteral = pydantic.Field(description='Train status.')
  day: datetime.date = pydantic.Field(description='Day of this train.')
  direction: str = pydantic.Field(description='Direction of the train.')
  message: str = pydantic.Field(description='Public message for the train.')
  position: base.PointModel | None = pydantic.Field(
    default=None, description='Geographical position of the train.'
  )

  @classmethod
  def from_domain(cls, t: RunningTrain) -> RunningTrainModel:
    """Convert domain ``RunningTrain`` to Pydantic model.

    Returns:
      RunningTrainModel: converted model.

    """
    return cls(
      code=t.code,
      status=t.status.name,  # type: ignore[arg-type]
      day=t.day,
      direction=t.direction,
      message=t.message,
      position=base.PointModel.from_domain(t.position),
    )


class RunningTrainsResponse(pydantic.BaseModel):
  """Response for the running-trains endpoint."""

  count: int = pydantic.Field(description='Number of running trains returned')
  trains: list[RunningTrainModel] = pydantic.Field(description='List of running trains')


class TrainType(enum.Enum):
  """Train type."""

  UNKNOWN = 0
  DMU = 1  # Diesel-multiple-unit commuter sets
  DART = 2  # DART (Dublin Area Rapid Transit) electric suburban, 'DART' or 'DART10' values
  ICR = 3  # 22000-class InterCity Railcars
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
  LocationType.ORIGIN: '[green]ORIGIN[/]',
  LocationType.DESTINATION: '[green]DESTINATION[/]',
  LocationType.STOP: '[green]\u25a0[/]',  # ■
  LocationType.TIMING_POINT: '[red]\u23f1[/]',  # ⏱
  LocationType.CREW_RELIEF_OR_CURRENT: '[green]\u25a0\u25a0[/]',  # ■■
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

  def __lt__(self, other: StationLineQueryData) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (Any): Other object to compare against.

    Returns:
        bool: True if this StationLineQueryData is less than the other, False otherwise.

    """
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

  def __lt__(self, other: StationLine) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (Any): Other object to compare against.

    Returns:
        bool: True if this StationLine is less than the other, False otherwise.

    """
    if self.due_in != other.due_in:
      return self.due_in < other.due_in
    if self.expected != other.expected:
      return self.expected < other.expected
    return self.destination_name < other.destination_name


class ExpectedStationLineXMLRowType(TypedDict):
  """getStationDataByCodeXML/objStationData."""

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
  Duein: int  # attention: this is in minutes, not seconds
  Late: int
  Exparrival: str
  Expdepart: str
  Scharrival: str
  Schdepart: str
  Direction: str
  Traintype: str
  Locationtype: str  # O=Origin, S=Stop, T=TimingPoint (non stopping location), D=Destination


class StationLineModel(pydantic.BaseModel):
  """A single line on a station departure/arrival board."""

  train_code: str = pydantic.Field(description='Train code, e.g. 22000 or DART10')
  origin_code: str = pydantic.Field(description='Origin station code.')
  origin_name: str = pydantic.Field(description='Origin station name.')
  destination_code: str = pydantic.Field(description='Destination station code.')
  destination_name: str = pydantic.Field(description='Destination station name.')
  trip: base.DayRangeModel | None = pydantic.Field(default=None, description='Trip information.')
  direction: str = pydantic.Field(description='Direction of the train.')
  due_in: base.DayTimeModel | None = pydantic.Field(
    default=None, description='Time until the train is due (in seconds inside DayTimeModel).'
  )
  late: int = pydantic.Field(description='Minutes the train is late.')
  location_type: LocationTypeLiteral = pydantic.Field(
    description='Type of this location in the journey.',
  )
  status: str | None = pydantic.Field(default=None, description='Current status of the train.')
  train_type: TrainTypeLiteral = pydantic.Field(description='Rolling stock type.')
  last_location: str | None = pydantic.Field(
    default=None, description='Last known location of the train.'
  )
  scheduled: base.DayRangeModel | None = pydantic.Field(
    default=None, description='Scheduled times for the train.'
  )
  expected: base.DayRangeModel | None = pydantic.Field(
    default=None, description='Expected times for the train.'
  )

  @classmethod
  def from_domain(cls, sl: StationLine) -> StationLineModel:
    """Convert domain ``StationLine`` to Pydantic model.

    Returns:
      StationLineModel: converted model.

    """
    return cls(
      train_code=sl.train_code,
      origin_code=sl.origin_code,
      origin_name=sl.origin_name,
      destination_code=sl.destination_code,
      destination_name=sl.destination_name,
      trip=base.DayRangeModel.from_domain(sl.trip),
      direction=sl.direction,
      due_in=base.DayTimeModel.from_domain(sl.due_in),
      late=sl.late,
      location_type=sl.location_type.name,  # type: ignore[arg-type]
      status=sl.status,
      train_type=sl.train_type.name,  # type: ignore[arg-type]
      last_location=sl.last_location,
      scheduled=base.DayRangeModel.from_domain(sl.scheduled),
      expected=base.DayRangeModel.from_domain(sl.expected),
    )


class StationBoardResponse(pydantic.BaseModel):
  """Response for the station-board endpoint."""

  count: int = pydantic.Field(description='Number of lines returned')
  lines: list[StationLineModel] = pydantic.Field(description='List of station board lines')


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

  def __lt__(self, other: TrainStopQueryData) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (Any): Other object to compare against.

    Returns:
        bool: True if this TrainStopQueryData is less than the other, False otherwise.

    """
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

  def __lt__(self, other: TrainStop) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (Any): Other object to compare against.

    Returns:
        bool: True if this TrainStop is less than the other, False otherwise.

    """
    return self.station_order < other.station_order


class ExpectedTrainStopXMLRowType(TypedDict):
  """getTrainMovementsXML/objTrainMovements."""

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


class TrainStopModel(pydantic.BaseModel):
  """A single stop in a train's journey."""

  station_code: str = pydantic.Field(description='Station code')
  station_name: str | None = pydantic.Field(default=None, description='Station name')
  station_order: int = pydantic.Field(description='Order of the station in the journey')
  location_type: LocationTypeLiteral = pydantic.Field(
    description='Type of this location in the journey.',
  )
  stop_type: StopTypeLiteral = pydantic.Field(description='Whether this is the current/next stop.')
  auto_arrival: bool = pydantic.Field(description='Whether the arrival is automatic')
  auto_depart: bool = pydantic.Field(description='Whether the departure is automatic')
  scheduled: base.DayRangeModel | None = pydantic.Field(
    default=None, description='Scheduled times for the train'
  )
  expected: base.DayRangeModel | None = pydantic.Field(
    default=None, description='Expected times for the train'
  )
  actual: base.DayRangeModel | None = pydantic.Field(
    default=None, description='Actual times for the train'
  )

  @classmethod
  def from_domain(cls, ts: TrainStop) -> TrainStopModel:
    """Convert domain ``TrainStop`` to Pydantic model.

    Returns:
      TrainStopModel: converted model.

    """
    return cls(
      station_code=ts.station_code,
      station_name=ts.station_name,
      station_order=ts.station_order,
      location_type=ts.location_type.name,  # type: ignore[arg-type]
      stop_type=ts.stop_type.name,  # type: ignore[arg-type]
      auto_arrival=ts.auto_arrival,
      auto_depart=ts.auto_depart,
      scheduled=base.DayRangeModel.from_domain(ts.scheduled),
      expected=base.DayRangeModel.from_domain(ts.expected),
      actual=base.DayRangeModel.from_domain(ts.actual),
    )


class TrainMovementsResponse(pydantic.BaseModel):
  """Response for the train-movements endpoint."""

  count: int = pydantic.Field(description='Number of stops returned')
  stops: list[TrainStopModel] = pydantic.Field(description='List of train stops')


@dataclasses.dataclass(kw_only=True, slots=True, frozen=False)
class LatestData:
  """Realtime: latest fetched data."""

  stations_tm: float | None
  stations: dict[str, Station]  # {station_code: Station}
  running_tm: float | None
  running_trains: dict[str, RunningTrain]  # {train_code: RunningTrain}
  station_boards: dict[
    str,
    tuple[  # {station_code: (tm, query_data, list[lines])}
      float, StationLineQueryData, list[StationLine]
    ],
  ]
  trains: dict[
    str,
    dict[
      datetime.date,
      tuple[  # {train_code: {day: (tm, query, {seq: train_stop})}}
        float, TrainStopQueryData, dict[int, TrainStop]
      ],
    ],
  ]


PRETTY_AUTO: abc.Callable[[bool], str] = lambda b: '[green]\u2699[/]' if b else ''  # ⚙
