# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Irish Rail Realtime.

See: https://api.irishrail.ie/realtime/
"""

from __future__ import annotations

import copy
import dataclasses
import datetime
import functools
import html
import logging
import time
import types
import urllib.error
import urllib.request
import xml.dom.minidom  # noqa: S408
from collections import abc
from typing import Any, cast, get_args, get_type_hints

import click
import typer
from rich import console as rich_console
from rich import table as rich_table
from transcrypto.cli import clibase
from transcrypto.utils import config as app_config
from transcrypto.utils import human, stats, timer
from transcrypto.utils import logging as tc_logging

from . import __version__
from . import gtfs_data_model as gdm
from . import realtime_data_model as dm
from . import tfinta_base as base


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class RealtimeConfig(clibase.CLIConfig):
  """CLI global context, storing the configuration."""


# globals
_TFI_REALTIME_URL = 'https://api.irishrail.ie/realtime/realtime.asmx'
_N_RETRIES = 5
_DEFAULT_TIMEOUT = 10.0

# cache sizes (in entries)
_SMALL_CACHE = 1 << 10  # 1024

# useful aliases
type _PossibleRPCArgs = dict[str, str | datetime.date]
type _RealtimeRowHandler[T: gdm.ExpectedRowData] = abc.Callable[
  [_PossibleRPCArgs, T], dm.RealtimeRPCData
]

# defaults
_TODAY: datetime.date = datetime.datetime.now(tz=datetime.UTC).date()
_TODAY_INT = int(_TODAY.strftime('%Y%m%d'))
_MIN_DATE = 20000101
_MAX_DATE = 21991231


_RPC_CALLS: dict[str, abc.Callable[[_PossibleRPCArgs], str]] = {
  'stations': lambda _: f'{_TFI_REALTIME_URL}/getAllStationsXML',
  'running': lambda _: f'{_TFI_REALTIME_URL}/getCurrentTrainsXML',
  'station': lambda station_data: (
    f'{_TFI_REALTIME_URL}/getStationDataByCodeXML?StationCode={
      str(station_data["station_code"]).strip()
    }'
  ),
  'train': lambda train_data: (
    f'{_TFI_REALTIME_URL}/getTrainMovementsXML?TrainId={str(train_data["train_code"]).strip()}'
    f'&TrainDate={cast("datetime.date", train_data["day"]).strftime("%d%%20%b%%20%Y").lower()}'
  ),
}


class Error(base.Error):
  """Realtime exception."""


class ParseError(Error):
  """Exception parsing a XML RPC file."""


class RowError(ParseError):
  """Exception parsing a XML RPC row."""


def _LoadXMLFromURL(url: str, /, timeout: float = _DEFAULT_TIMEOUT) -> xml.dom.minidom.Document:
  """Get URL data.

  Args:
      url (str): URL to load
      timeout (float): timeout in seconds

  Returns:
      xml.dom.minidom.Document: parsed XML document

  Raises:
      Error: error loading URL

  """
  # get URL, do backoff and retries
  errors: list[str] = []
  backoff = 1.0
  for attempt in range(1, _N_RETRIES + 1):
    try:
      with urllib.request.urlopen(url, timeout=timeout) as url_data:  # noqa: S310
        data = url_data.read()
      # XML errors will bubble up
      logging.info('Loaded %s from %s', human.HumanizedBytes(len(data)), url)
      return xml.dom.minidom.parseString(data)  # noqa: S318
    except urllib.error.HTTPError as err:
      if 500 <= err.code < 600:  # 5xx → retry, 4xx → fail immediately  # noqa: PLR2004
        errors.append(f'HTTP {err.code} {err.reason}')
        logging.warning('attempt #%d: %r', attempt, err)
      else:
        raise Error(f'HTTP error loading {url!r}') from err
    except (TimeoutError, urllib.error.URLError) as err:  # network glitch or timeout
      errors.append(str(err))
      logging.warning('attempt #%d: %r', attempt, err)
    # if we get here, we'll retry (if attempts remain)
    if attempt < _N_RETRIES:
      time.sleep(backoff)
      backoff *= 2  # exponential backoff
  # all retries exhausted
  raise Error(f'Too many retries ({_N_RETRIES}) loading {url!r}: {"; ".join(errors)}')


class RealtimeRail:
  """Irish Rail Realtime."""

  def __init__(self) -> None:
    """Construct.

    Raises:
        Error: error initializing realtime object

    """
    self._latest = dm.LatestData(
      stations={},
      running_trains={},
      station_boards={},
      trains={},
      stations_tm=None,
      running_tm=None,
    )
    # create file handlers structure
    self._file_handlers: dict[
      str,
      tuple[
        _RealtimeRowHandler[Any],
        type,
        str,
        dict[str, tuple[type, bool]],
        set[str],
      ],
    ] = {
      # {realtime_type: (handler, TypedDict_row_definition, xml_row_tag_name,
      #                  {field: (type, required?)}, {required1, required2, ...})}
      'stations': (
        self._HandleStationXMLRow,
        dm.ExpectedStationXMLRowType,
        'objStation',
        {},
        set(),
      ),
      'running': (
        self._HandleRunningTrainXMLRow,
        dm.ExpectedRunningTrainXMLRowType,
        'objTrainPositions',
        {},
        set(),
      ),
      'station': (
        self._HandleStationLineXMLRow,
        dm.ExpectedStationLineXMLRowType,
        'objStationData',
        {},
        set(),
      ),
      'train': (
        self._HandleTrainStationXMLRow,
        dm.ExpectedTrainStopXMLRowType,
        'objTrainMovements',
        {},
        set(),
      ),
    }
    # fill in types, derived from the _Expected*CSVRowType TypedDicts
    for rpc_name, handlers in self._file_handlers.items():
      _, expected, _, fields, required = handlers
      for field, type_descriptor in get_type_hints(expected).items():
        if type_descriptor in {str, int, float, bool}:
          # no optional, so field is required
          required.add(field)
          fields[field] = (type_descriptor, True)
        else:
          # it is optional and something else, so find out which
          field_args = get_args(type_descriptor)
          if len(field_args) != 2:  # noqa: PLR2004  # pragma: no cover
            raise Error(f'incorrect type len {rpc_name}/{field}: {field_args!r}')
          field_type = field_args[0] if field_args[1] == types.NoneType else field_args[1]
          if field_type not in {str, int, float, bool}:  # pragma: no cover
            raise Error(f'incorrect type {rpc_name}/{field}: {field_args!r}')
          fields[field] = (field_type, False)
    logging.info('Created realtime object')

  @functools.lru_cache(  # noqa: B019
    maxsize=_SMALL_CACHE
  )  # remember to update self._InvalidateCaches()
  def StationCodeFromNameFragmentOrCode(self, code: str, /) -> str:
    """If given a valid station code uses that, else searches for station (case-insensitive).

    Args:
        code (str): station code or fragment of station description/alias

    Returns:
        str: the station code

    Raises:
        Error: station code/description not found or ambiguous

    """
    # lazy fetch stations, if needed
    if self._latest.stations_tm is None or not self._latest.stations:
      self.StationsCall()
    # check if code is not a station code already
    code = code.strip()
    if (station_code := code.upper()) in self._latest.stations:
      return station_code
    # not a station code, so try to do a naïve case-insensitive search
    search_str: str = code.lower()
    matches: set[str] = {
      code
      for code, station in self._latest.stations.items()
      if (
        search_str in station.description.lower()
        or (station.alias and search_str in station.alias.lower())
      )
    }
    if not matches:
      raise Error(f'station code/description {code!r} not found')
    if len(matches) > 1:
      raise Error(f'station code/description {code!r} ambiguous, matches codes: {matches}')
    return matches.pop()

  def _InvalidateCaches(self) -> None:
    """Clear all caches."""
    for method in (
      # list cache methods here
      self.StationCodeFromNameFragmentOrCode,
    ):
      method.cache_clear()

  def _CallRPC(  # noqa: C901, PLR0912
    self, rpc_name: str, args: _PossibleRPCArgs, /
  ) -> tuple[float, list[dm.RealtimeRPCData]]:
    """Call RPC and send rows to parsers.

    Args:
        rpc_name (str): name of the RPC to call
        args (_PossibleRPCArgs): arguments for the RPC call

    Returns:
        tuple[float, list[dm.RealtimeRPCData]]: timestamp of data retrieval, list of parsed rows

    Raises:
        ParseError: error parsing XML data
        Error: error calling RPC

    """
    # get fields definition and compute URL
    row_handler, _, row_xml_tag, row_types, row_required = self._file_handlers[rpc_name]
    url: str = _RPC_CALLS[rpc_name](args)
    # call external URL
    tm_now: float = time.time()
    xml_obj: xml.dom.minidom.Document = _LoadXMLFromURL(url)
    # divide XML into rows and start parsing
    xml_elements = list(xml_obj.getElementsByTagName(row_xml_tag))
    parsed_rows: list[dm.RealtimeRPCData] = []
    xml_data: list[xml.dom.minidom.Element] = []
    row_count: int = 0
    if not xml_elements:
      return (tm_now, parsed_rows)
    for row_count, xml_row in enumerate(xml_elements):
      row_data: gdm.ExpectedRowData = {}
      for field_name, (field_type, field_required) in row_types.items():
        xml_data = list(xml_row.getElementsByTagName(field_name))
        if len(xml_data) != 1:
          raise ParseError(
            f'repeated elements: {rpc_name}/{args}/{row_count}/{field_name}: {xml_data}'
          )
        child = xml_data[0].firstChild
        if child is None or (field_value := child.nodeValue) is None or not field_value.strip():  # type: ignore[attr-defined]
          # field is empty
          if field_required:
            raise ParseError(
              f'empty required field {rpc_name}/{args}/{row_count}/{field_name}: {xml_data}'
            )
          row_data[field_name] = None
        # field has a value
        elif field_type is str:
          row_data[field_name] = field_value.strip()  # vanilla string
        elif field_type is bool:
          bool_value: str = field_value.strip()
          try:
            row_data[field_name] = base.BOOL_FIELD[bool_value]  # convert to bool '0'/'1'
          except KeyError as err:
            raise ParseError(
              f'invalid bool value {rpc_name}/{args}/{row_count}/{field_name}: {bool_value!r}'
            ) from err
        elif field_type in {int, float}:
          try:
            row_data[field_name] = field_type(field_value)  # convert int/float
          except ValueError as err:
            raise ParseError(
              f'invalid int/float value {rpc_name}/{args}/{row_count}/{field_name}: {field_value!r}'
            ) from err
        else:  # pragma: no cover
          raise Error(
            f'invalid field type {rpc_name}/{args}/{row_count}/{field_name}: {field_type!r}'
          )
      # row is parsed, check required fields
      if missing_fields := row_required - set(row_data):  # pragma: no cover
        raise ParseError(
          f'missing required fields {missing_fields}: {rpc_name}/{row_count}: {xml_data}'
        )
      # call handler
      parsed_rows.append(row_handler(args, row_data))
    # finished parsing all rows
    logging.info('Read %d rows from %s/%r', row_count, rpc_name, args)
    return (tm_now, parsed_rows)

  def StationsCall(self) -> list[dm.Station]:
    """Get all stations.

    Returns:
        list[dm.Station]: list of stations

    """
    # make call
    stations: list[dm.Station]
    self._InvalidateCaches()
    tm, stations = self._CallRPC('stations', {})  # type: ignore
    if not stations:
      return []
    # we have new data
    sorted_stations: list[dm.Station] = sorted(stations)
    for station in sorted_stations:
      self._latest.stations[station.code] = station  # insert in order
    self._latest.stations_tm = tm
    return sorted_stations  # no need for copy as we don't store this list

  def RunningTrainsCall(self) -> list[dm.RunningTrain]:
    """Get all running trains.

    Returns:
        list[dm.RunningTrain]: list of running trains

    """
    # make call
    running: list[dm.RunningTrain]
    tm, running = self._CallRPC('running', {})  # type: ignore
    if not running:
      return []
    # we have new data
    sorted_running: list[dm.RunningTrain] = sorted(running)
    self._latest.running_trains = {}  # start from clean slate
    for train in sorted_running:
      self._latest.running_trains[train.code] = train  # insert in order
    self._latest.running_tm = tm
    return sorted_running  # no need for copy as we don't store this list

  def StationBoardCall(
    self, station_code: str, /
  ) -> tuple[dm.StationLineQueryData | None, list[dm.StationLine]]:
    """Get a station board (all trains due to serve the named station in the next 90 minutes).

    Args:
        station_code (str): station code

    Returns:
        tuple[dm.StationLineQueryData | None, list[dm.StationLine]]: query data and list of
            station lines

    Raises:
        Error: invalid station code

    """
    # make call
    station_code = station_code.strip().upper()
    if not station_code:
      raise Error('empty station code')
    station_lines: list[dm.StationLine]
    tm, station_lines = self._CallRPC('station', {'station_code': station_code})  # type: ignore
    if not station_lines:
      return (None, [])
    # we have new data
    sample_query: dm.StationLineQueryData = copy.deepcopy(station_lines[0].query)  # make a new copy
    for line in station_lines[1:]:
      if sample_query != line.query:
        raise Error(
          f'field should match: {sample_query!r} versus {line.query!r} '
          f'@ running/{station_code} {line}'
        )
    station_lines.sort()
    self._latest.station_boards[station_code] = (tm, sample_query, station_lines)
    return (copy.deepcopy(sample_query), list(station_lines))  # make a new copy

  def TrainDataCall(
    self, train_code: str, day: datetime.date, /
  ) -> tuple[dm.TrainStopQueryData | None, list[dm.TrainStop]]:
    """Get train realtime.

    Args:
        train_code (str): train code
        day (datetime.date): day of the train

    Returns:
        tuple[dm.TrainStopQueryData | None, list[dm.TrainStop]]: query data and list of train stops

    Raises:
        Error: invalid train code

    """
    # make call
    train_code = train_code.strip().upper()
    if not train_code:
      raise Error('empty train code')
    train_stops: list[dm.TrainStop]
    tm, train_stops = self._CallRPC('train', {'train_code': train_code, 'day': day})  # type: ignore
    if not train_stops:
      return (None, [])
    # we have new data
    sample_query: dm.TrainStopQueryData = copy.deepcopy(train_stops[0].query)  # make a new copy
    for line in train_stops[1:]:
      if sample_query != line.query:
        raise Error(
          f'field should match: {sample_query!r} versus {line.query!r} '
          f'@ train/{train_code}/{day} {line}'
        )
    train_stops.sort()
    self._latest.trains.setdefault(train_code, {})[day] = (
      tm,
      sample_query,
      {s.station_order: s for s in train_stops},
    )
    if (stop_seqs := set(self._latest.trains[train_code][day][2])) != set(
      range(1, len(self._latest.trains[train_code][day][2]) + 1)
    ):
      raise Error(f'missing stop #: {sorted(stop_seqs)!r} @ train/{train_code}/{day}')
    return (copy.deepcopy(sample_query), train_stops)  # no need for new train_stops

  ##################################################################################################
  # REALTIME ROW HANDLERS
  ##################################################################################################

  # HANDLER TEMPLATE (copy and uncomment)
  # def _HandleXMLTABLENAMERow(
  #     self, params: _PossibleRPCArgs, row: dm.ExpectedXMLTABLENAMERowType, /) -> dm.DERIVED_TYPE:
  #   """Handler: XMLTABLENAME DESCRIPTION.
  #
  #   Args:
  #     params: dict with args for calling XML URL-calling method
  #     row: the row as a dict {field_name: Optional[field_data]}
  #
  #   Raises:
  #     RowError: error parsing this record
  #   """

  def _HandleStationXMLRow(  # noqa: PLR6301
    self, params: _PossibleRPCArgs, row: dm.ExpectedStationXMLRowType, /
  ) -> dm.Station:
    """Handle: Station.

    Args:
      params: dict with args for calling XML URL-calling method
      row: the row as a dict {field_name: Optional[field_data]}

    Returns:
      dm.Station: parsed station

    Raises:
      RowError: error parsing this record

    """
    if row['StationId'] < 1:
      raise RowError(f'invalid StationId {row["StationId"]} @ station/{params!r}')
    return dm.Station(
      id=row['StationId'],
      code=row['StationCode'].upper(),
      description=row['StationDesc'],
      location=(
        None
        if stats.IS_EQUAL(row['StationLatitude'], 0.0)
        and stats.IS_EQUAL(row['StationLongitude'], 0.0)
        else base.Point(latitude=row['StationLatitude'], longitude=row['StationLongitude'])
      ),
      alias=row['StationAlias'],
    )

  def _HandleRunningTrainXMLRow(  # noqa: PLR6301
    self, params: _PossibleRPCArgs, row: dm.ExpectedRunningTrainXMLRowType, /
  ) -> dm.RunningTrain:
    """Handle: RunningTrain.

    Args:
      params: dict with args for calling XML URL-calling method
      row: the row as a dict {field_name: Optional[field_data]}

    Returns:
      dm.RunningTrain: parsed running train

    Raises:
      Error: error parsing this record

    """
    day: datetime.date = base.DATE_OBJ_REALTIME(row['TrainDate'])
    try:
      train_status: dm.TrainStatus = dm.TRAIN_STATUS_STR_MAP[row['TrainStatus'].upper()]
    except KeyError as err:
      raise Error(f'invalid TrainStatus: {row!r} @ running/{params!r}') from err
    return dm.RunningTrain(
      code=row['TrainCode'].upper(),
      status=train_status,
      day=day,
      direction=row['Direction'],
      position=(
        None
        if stats.IS_EQUAL(row['TrainLatitude'], 0.0) and stats.IS_EQUAL(row['TrainLongitude'], 0.0)
        else base.Point(latitude=row['TrainLatitude'], longitude=row['TrainLongitude'])
      ),
      message=html.escape(row['PublicMessage'].replace('\\n', '\n')),
    )

  def _HandleStationLineXMLRow(
    self, params: _PossibleRPCArgs, row: dm.ExpectedStationLineXMLRowType, /
  ) -> dm.StationLine:
    """Handle: StationLine.

    Args:
      params: dict with args for calling XML URL-calling method
      row: the row as a dict {field_name: Optional[field_data]}

    Returns:
      dm.StationLine: parsed station line

    Raises:
      Error: error parsing this record

    """
    day: datetime.date = base.DATE_OBJ_REALTIME(row['Traindate'])
    station_code: str = row['Stationcode']
    if station_code != params['station_code']:
      raise Error(
        f'station mismatch: {params["station_code"]} versus {station_code} @ station/{params!r}'
      )
    origin_code: str = '???'
    try:
      origin_code = self.StationCodeFromNameFragmentOrCode(row['Origin'])
    except Error as err:
      logging.warning(err)
    destination_code: str = '???'
    try:
      destination_code = self.StationCodeFromNameFragmentOrCode(row['Destination'])
    except Error as err:
      logging.warning(err)
    try:
      loc_type: dm.LocationType = dm.LOCATION_TYPE_STR_MAP[row['Locationtype'].upper()]
      train_type: dm.TrainType = dm.TRAIN_TYPE_STR_MAP.get(
        row['Traintype'].upper(), dm.TrainType.UNKNOWN
      )
    except KeyError as err:
      raise Error(f'invalid Locationtype/Traintype: {row!r} @ station/{params!r}') from err
    return dm.StationLine(
      query=dm.StationLineQueryData(
        tm_server=timer.DatetimeFromISO(row['Servertime']),
        tm_query=base.DayTime.FromHMS(row['Querytime']),
        station_name=row['Stationfullname'],
        station_code=station_code,
        day=day,
      ),
      train_code=row['Traincode'].upper(),
      origin_code=origin_code,
      origin_name=row['Origin'],
      destination_code=destination_code,
      destination_name=row['Destination'],
      trip=base.DayRange(
        arrival=base.DayTime.FromHMS(row['Origintime'] + ':00'),  # note the inversion!
        departure=base.DayTime.FromHMS(row['Destinationtime'] + ':00'),
      ),
      status=row['Status'],
      train_type=train_type,
      last_location=row['Lastlocation'],
      due_in=base.DayTime(time=row['Duein'] * 60),  # convert minutes to seconds!!
      late=row['Late'],
      location_type=loc_type,
      scheduled=base.DayRange(
        arrival=(
          None if row['Scharrival'] == '00:00' else base.DayTime.FromHMS(row['Scharrival'] + ':00')
        ),
        departure=(
          None if row['Schdepart'] == '00:00' else base.DayTime.FromHMS(row['Schdepart'] + ':00')
        ),
        nullable=True,
      ),
      expected=base.DayRange(
        arrival=(
          None if row['Exparrival'] == '00:00' else base.DayTime.FromHMS(row['Exparrival'] + ':00')
        ),
        departure=(
          None if row['Expdepart'] == '00:00' else base.DayTime.FromHMS(row['Expdepart'] + ':00')
        ),
        nullable=True,
        strict=False,
      ),
      direction=row['Direction'],
    )

  def _HandleTrainStationXMLRow(
    self, params: _PossibleRPCArgs, row: dm.ExpectedTrainStopXMLRowType, /
  ) -> dm.TrainStop:
    """Handle: TrainStation.

    Args:
      params: dict with args for calling XML URL-calling method
      row: the row as a dict {field_name: Optional[field_data]}

    Returns:
      dm.TrainStop: parsed train stop

    Raises:
      Error: error parsing this record

    """
    if row['LocationOrder'] < 1 or row['TrainCode'] != params['train_code']:
      raise Error(f'invalid row: {row!r} @ train/{params!r}')
    day: datetime.date = base.DATE_OBJ_REALTIME(row['TrainDate'])
    origin_code: str = '???'
    try:
      origin_code = self.StationCodeFromNameFragmentOrCode(row['TrainOrigin'])
    except Error as err:
      logging.warning(err)
    destination_code: str = '???'
    try:
      destination_code = self.StationCodeFromNameFragmentOrCode(row['TrainDestination'])
    except Error as err:
      logging.warning(err)
    try:
      loc_type: dm.LocationType = dm.LOCATION_TYPE_STR_MAP[row['LocationType'].upper()]
      stop_type: dm.StopType = dm.STOP_TYPE_STR_MAP[row['StopType'].upper()]
    except KeyError as err:
      raise Error(f'invalid LocationType/StopType: {row!r} @ train/{params!r}') from err
    return dm.TrainStop(
      query=dm.TrainStopQueryData(
        train_code=row['TrainCode'],
        day=day,
        origin_code=origin_code,
        origin_name=row['TrainOrigin'],
        destination_code=destination_code,
        destination_name=row['TrainDestination'],
      ),
      station_code=row['LocationCode'],
      station_name=row['LocationFullName'],
      station_order=row['LocationOrder'],
      location_type=loc_type,
      scheduled=base.DayRange(
        arrival=(
          None
          if row['ScheduledArrival'] == '00:00:00'
          else base.DayTime.FromHMS(row['ScheduledArrival'])
        ),
        departure=(
          None
          if row['ScheduledDeparture'] == '00:00:00'
          else base.DayTime.FromHMS(row['ScheduledDeparture'])
        ),
        nullable=True,
      ),
      expected=base.DayRange(
        arrival=(
          None
          if row['ExpectedArrival'] == '00:00:00'
          else base.DayTime.FromHMS(row['ExpectedArrival'])
        ),
        departure=(
          None
          if row['ExpectedDeparture'] == '00:00:00'
          else base.DayTime.FromHMS(row['ExpectedDeparture'])
        ),
        nullable=True,
        strict=False,
      ),
      actual=base.DayRange(
        arrival=(
          None
          if row['Arrival'] is None or row['Arrival'] == '00:00:00'
          else base.DayTime.FromHMS(row['Arrival'])
        ),
        departure=(
          None
          if row['Departure'] is None or row['Departure'] == '00:00:00'
          else base.DayTime.FromHMS(row['Departure'])
        ),
        nullable=True,
      ),
      auto_arrival=False if row['AutoArrival'] is None else row['AutoArrival'],
      auto_depart=False if row['AutoDepart'] is None else row['AutoDepart'],
      stop_type=stop_type,
    )

  ##################################################################################################
  # REALTIME PRETTY PRINTS
  ##################################################################################################

  def PrettyPrintStations(self) -> abc.Generator[str | rich_table.Table, None, None]:
    """Generate a pretty version of all stations.

    Yields:
        str: lines of the pretty-printed data

    """
    if self._latest.stations_tm is None or not self._latest.stations:
      self.StationsCall()  # lazy load
    yield (
      f'[magenta]Irish Rail Stations @ [bold]'
      f'{base.STD_TIME_STRING(self._latest.stations_tm or 0)}[/]'
    )
    yield ''
    table = rich_table.Table(show_header=True, show_lines=True)
    table.add_column('[bold cyan]ID[/]')
    table.add_column('[bold cyan]Code[/]')
    table.add_column('[bold cyan]Name[/]')
    table.add_column('[bold cyan]Alias[/]')
    table.add_column('[bold cyan]Location °[/]')
    table.add_column('[bold cyan]Location[/]')
    for station in sorted(self._latest.stations.values()):
      lat, lon = (None, None) if station.location is None else station.location.ToDMS()
      table.add_row(
        f'[bold cyan]{station.id}[/]',
        f'[bold]{station.code}[/]',
        f'[bold yellow]{station.description}[/]',
        f'[bold]{station.alias or base.NULL_TEXT}[/]',
        (f'[bold yellow]{lat or base.NULL_TEXT}[/]\n[bold yellow]{lon or base.NULL_TEXT}[/]'),
        (
          f'[bold]{f"{station.location.latitude:0.7f}" if station.location else base.NULL_TEXT}'
          f'[/]\n'
          f'[bold]{f"{station.location.longitude:0.7f}" if station.location else base.NULL_TEXT}'
          f'[/]'
        ),
      )
    yield table

  def PrettyPrintRunning(self) -> abc.Generator[str | rich_table.Table, None, None]:
    """Generate a pretty version of running trains.

    Yields:
        str: lines of the pretty-printed data

    """
    if self._latest.running_tm is None or not self._latest.running_trains:
      self.RunningTrainsCall()  # lazy load
    yield (
      f'[magenta]Irish Rail Running Trains @ [bold]'
      f'{base.STD_TIME_STRING(self._latest.running_tm or 0)}[/]'
    )
    yield ''
    table = rich_table.Table(show_header=True, show_lines=True)
    table.add_column('[bold cyan]Train[/]')
    table.add_column('[bold cyan]Direction[/]')
    table.add_column('[bold cyan]Location °[/]')
    table.add_column('[bold cyan]Location[/]')
    table.add_column('[bold cyan]Message[/]')
    for train in sorted(self._latest.running_trains.values()):
      lat, lon = train.position.ToDMS() if train.position is not None else (None, None)
      train_message: str = (
        '\n'.join(train.message.splitlines()[1:])
        if train.message.startswith(train.code + '\n')
        else train.message
      )
      table.add_row(
        (f'[bold cyan]{train.code}[/]\n[bold]{dm.TRAIN_STATUS_STR[train.status]}[/]'),
        f'[bold]{base.LIMITED_TEXT(train.direction, 15)}[/]',
        (
          f'[bold{" yellow" if lat else ""}]{lat or base.NULL_TEXT}[/]\n'
          f'[bold{" yellow" if lon else ""}]{lon or base.NULL_TEXT}[/]'
        ),
        (
          f'[bold]{f"{train.position.latitude:0.7f}" if train.position else base.NULL_TEXT}'
          f'[/]\n'
          f'[bold]{f"{train.position.longitude:0.7f}" if train.position else base.NULL_TEXT}'
          f'[/]'
        ),
        '\n'.join(f'[bold]{base.LIMITED_TEXT(m, 50)}[/]' for m in train_message.split('\n')),
      )
    yield table

  def PrettyPrintStation(
    self, /, *, station_code: str
  ) -> abc.Generator[str | rich_table.Table, None, None]:
    """Generate a pretty version of station board.

    Args:
        station_code (str): station code

    Yields:
        str: lines of the pretty-printed data

    """
    station_code = station_code.upper()
    if station_code not in self._latest.station_boards:
      self.StationBoardCall(station_code)  # lazy load
    if self._latest.stations_tm is None or not self._latest.stations:
      self.StationsCall()  # lazy load
    tm, _, station_trains = self._latest.station_boards[station_code]
    yield (
      f'[magenta]Irish Rail Station [bold]'
      f'{self._latest.stations[station_code].description} '
      f'({station_code})[/][magenta] Board @ '
      f'[bold]{base.STD_TIME_STRING(tm)}[/]'
    )
    yield ''
    table = rich_table.Table(show_header=True, show_lines=True)
    table.add_column('[bold cyan]Train[/]')
    table.add_column('[bold cyan]Origin[/]')
    table.add_column('[bold cyan]Dest.[/]')
    table.add_column('[bold cyan]Due[/]')
    table.add_column('[bold cyan]Arrival[/]')
    table.add_column('[bold cyan]Depart.[/]')
    table.add_column('[bold cyan]Late[/]')
    table.add_column('[bold cyan]Status[/]')
    table.add_column('[bold cyan]Location[/]')
    for line in station_trains:
      direction_text: str = (
        '(N)'
        if line.direction.lower() == 'northbound'
        else (
          '(S)' if line.direction.lower() == 'southbound' else base.LIMITED_TEXT(line.direction, 15)
        )
      )
      table.add_row(
        f'[bold cyan]{line.train_code}[/]\n'
        f'[bold]{direction_text}[/]'
        + (f'\n[bold]{line.train_type.name}[/]' if line.train_type != dm.TrainType.UNKNOWN else ''),
        (
          f'[bold]{line.origin_code}[/]\n'
          f'[bold]{base.LIMITED_TEXT(line.origin_name, 15)}[/]\n'
          f'[bold]{line.trip.arrival.ToHMS() if line.trip.arrival else base.NULL_TEXT}'
          f'[/]'
        ),
        (
          f'[bold yellow]{line.destination_code}[/]\n'
          f'[bold yellow]{base.LIMITED_TEXT(line.destination_name, 15)}[/]\n'
          f'[bold]{line.trip.departure.ToHMS() if line.trip.departure else base.NULL_TEXT}'
          f'[/]'
        ),
        f'[bold]{(line.due_in.time // 60):+}[/]',
        f'[bold green]'
        f'{line.scheduled.arrival.ToHMS() if line.scheduled.arrival else base.NULL_TEXT}[/]'
        + (
          ''
          if not line.expected.arrival or line.expected.arrival == line.scheduled.arrival
          else f'\n[bold red]{line.expected.arrival.ToHMS()}[/]'
        ),
        f'[bold green]'
        f'{line.scheduled.departure.ToHMS() if line.scheduled.departure else base.NULL_TEXT}[/]'
        + (
          ''
          if not line.expected.departure or line.expected.departure == line.scheduled.departure
          else f'\n[bold red]{line.expected.departure.ToHMS()}[/]'
        ),
        '\n'
        if not line.late
        else f'\n[bold {"red" if line.late > 0 else "yellow"}]{line.late:+}[/]',
        (f'\n[bold]{base.LIMITED_TEXT(line.status, 15) if line.status else base.NULL_TEXT}[/]'),
        (
          f'\n[bold]'
          f'{base.LIMITED_TEXT(line.last_location, 15) if line.last_location else base.NULL_TEXT}'
          f'[/]'
        ),
      )
    yield table

  def PrettyPrintTrain(
    self, /, *, train_code: str, day: datetime.date
  ) -> abc.Generator[str | rich_table.Table, None, None]:
    """Generate a pretty version of single train data.

    Args:
        train_code (str): train code
        day (datetime.date): day of the train

    Yields:
        str: lines of the pretty-printed data

    """
    train_code = train_code.upper()
    if train_code not in self._latest.trains or day not in self._latest.trains[train_code]:
      self.TrainDataCall(train_code, day)
    tm, query, train_stops = self._latest.trains[train_code][day]
    yield (
      f'[magenta]Irish Rail Train [bold]{train_code}[/][magenta] @ '
      f'[bold]{base.STD_TIME_STRING(tm)}[/]'
    )
    yield ''
    yield f'Day:         [bold yellow]{base.PRETTY_DATE(query.day)}[/]'
    yield (f'Origin:      [bold yellow]{query.origin_name} ({query.origin_code})[/]')
    yield (f'Destination: [bold yellow]{query.destination_name} ({query.destination_code})[/]')
    yield ''
    table = rich_table.Table(show_header=True, show_lines=True)
    table.add_column('[bold cyan]#[/]')
    table.add_column('[bold cyan]Stop[/]')
    table.add_column('[bold cyan]Arr.(Expect)[/]')
    table.add_column('[bold cyan]A.(Actual)[/]')
    table.add_column('[bold cyan]Depart.(Expect)[/]')
    table.add_column('[bold cyan]D.(Actual)[/]')
    table.add_column('[bold cyan]Late(Min)[/]')
    for seq in range(1, len(train_stops) + 1):
      stop: dm.TrainStop = train_stops[seq]
      late: int | None = (
        None
        if stop.actual.arrival is None or stop.scheduled.arrival is None
        else stop.actual.arrival.time - stop.scheduled.arrival.time
      )
      stop_type: str = (
        '' if stop.stop_type == dm.StopType.UNKNOWN else f'\n[bold yellow]{stop.stop_type.name}[/]'
      )
      table.add_row(
        f'[bold cyan]{seq}[/]{stop_type}',
        (
          f'[bold yellow]{stop.station_code}[/]\n'
          f'[bold yellow]'
          f'{base.LIMITED_TEXT(stop.station_name, 15) if stop.station_name else "????"}[/]\n'
          f'[bold]{dm.LOCATION_TYPE_STR[stop.location_type]}[/]'
        ),
        (
          f'[bold green]'
          f'{stop.scheduled.arrival.ToHMS() if stop.scheduled.arrival else base.NULL_TEXT}[/]'
        )
        + (
          ''
          if not stop.expected.arrival or stop.expected.arrival == stop.scheduled.arrival
          else f'\n[bold red]{stop.expected.arrival.ToHMS()}[/]'
        )
        + (f'\n[bold]{dm.PRETTY_AUTO(True)}' if stop.auto_arrival else ''),
        (
          f'[bold yellow]'
          f'{stop.actual.arrival.ToHMS() if stop.actual.arrival else base.NULL_TEXT}[/]'
        ),
        (
          f'[bold green]'
          f'{stop.scheduled.departure.ToHMS() if stop.scheduled.departure else base.NULL_TEXT}[/]'
        )
        + (
          ''
          if not stop.expected.departure or stop.expected.departure == stop.scheduled.departure
          else f'\n[bold red]{stop.expected.departure.ToHMS()}[/]'
        )
        + (f'\n[bold]{dm.PRETTY_AUTO(True)}' if stop.auto_depart else ''),
        (
          f'[bold yellow]'
          f'{stop.actual.departure.ToHMS() if stop.actual.departure else base.NULL_TEXT}[/]'
        ),
        f'[bold]{
          base.NULL_TEXT
          if late is None
          else (f"[red]{late / 60.0:+0.2f}" if late > 0 else f"[green]{late / 60.0:+0.2f}")
        }[/]',
      )
    yield table


# CLI app setup, this is an important object and can be imported elsewhere and called
app = typer.Typer(
  add_completion=True,
  no_args_is_help=True,
  help='realtime: CLI for Irish Rail Realtime services.',  # keep in sync with Main().help
  epilog=(
    'Example:\n\n\n\n'
    '# --- Print realtime data ---\n\n'
    'poetry run realtime print stations\n\n'
    'poetry run realtime print running\n\n'
    'poetry run realtime print station LURGN\n\n'
    'poetry run realtime print train E108 20260201\n\n\n\n'
    '# --- Generate documentation ---\n\n'
    'poetry run realtime markdown > realtime.md\n\n'
  ),
)


def Run() -> None:  # pragma: no cover
  """Run the CLI."""
  app()


@app.callback(
  invoke_without_command=True,  # have only one; this is the "constructor"
  help='realtime: CLI for Irish Rail Realtime services.',  # keep message in sync with app.help
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
  # check a few things
  if not (_MIN_DATE < _TODAY_INT < _MAX_DATE):
    raise Error(f'invalid TODAY date {_TODAY_INT}: not in {_MIN_DATE}..{_MAX_DATE}')
  # create context with the arguments we received.
  ctx.obj = RealtimeConfig(
    console=console,
    verbose=verbose,
    color=color,
    appconfig=app_config.InitConfig(base.APP_NAME, base.CONFIG_FILE_NAME),
  )


print_app = typer.Typer(
  no_args_is_help=True,
  help='Print Realtime Data',
)
app.add_typer(print_app, name='print')


@print_app.command(
  'stations',
  help='Print All System Stations.',
  epilog=('Example:\n\n\n\n$ poetry run realtime print stations\n\n<<prints all stations>>'),
)
@clibase.CLIErrorGuard
def PrintStations(*, ctx: click.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: RealtimeConfig = ctx.obj
  realtime = RealtimeRail()
  for line in realtime.PrettyPrintStations():
    config.console.print(line)


@print_app.command(
  'running',
  help='Print Running Trains.',
  epilog=('Example:\n\n\n\n$ poetry run realtime print running\n\n<<prints all running trains>>'),
)
@clibase.CLIErrorGuard
def PrintRunning(*, ctx: click.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: RealtimeConfig = ctx.obj
  realtime = RealtimeRail()
  for line in realtime.PrettyPrintRunning():
    config.console.print(line)


@print_app.command(
  'station',
  help='Print Station Board.',
  epilog=(
    'Example:\n\n\n\n$ poetry run realtime print station LURGN\n\n<<prints Lurgan station board>>'
  ),
)
@clibase.CLIErrorGuard
def PrintStation(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: click.Context,
  code: str = typer.Argument(
    ...,
    help='Either a 5-letter station code (ex: "LURGN") or a search string that can '
    'be identified as a station (ex: "lurgan")',
  ),
) -> None:
  config: RealtimeConfig = ctx.obj
  realtime = RealtimeRail()
  for line in realtime.PrettyPrintStation(
    station_code=realtime.StationCodeFromNameFragmentOrCode(code)
  ):
    config.console.print(line)


@print_app.command(
  'train',
  help='Print Train Movements.',
  epilog=(
    'Example:\n\n\n\n'
    '$ poetry run realtime print train E108 20260201\n\n'
    '<<prints train E108 movements>>'
  ),
)
@clibase.CLIErrorGuard
def PrintTrain(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: click.Context,
  code: str = typer.Argument(..., help='Train code (ex: "E108")'),
  day: int = typer.Argument(
    _TODAY_INT,
    min=_MIN_DATE,
    max=_MAX_DATE,
    help='Day to consider in "YYYYMMDD" format (default: TODAY/NOW).',
  ),
) -> None:
  config: RealtimeConfig = ctx.obj
  realtime = RealtimeRail()
  for line in realtime.PrettyPrintTrain(train_code=code, day=base.DATE_OBJ_GTFS(str(day))):
    config.console.print(line)


@app.command(
  'markdown',
  help='Emit Markdown docs for the CLI (see README.md section "Creating a New Version").',
  epilog=('Example:\n\n\n\n$ poetry run realtime markdown > realtime.md\n\n<<saves CLI doc>>'),
)
@clibase.CLIErrorGuard
def Markdown(*, ctx: click.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: RealtimeConfig = ctx.obj
  config.console.print(clibase.GenerateTyperHelpMarkdown(app, prog_name='realtime'))
