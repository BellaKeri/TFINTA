#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
"""Irish Rail Realtime.

See: https://api.irishrail.ie/realtime/
"""

import argparse
import copy
import datetime
import functools
import html
import logging
# import pdb
import socket
import sys
import time
import types
from typing import Callable, Generator
from typing import get_args as GetTypeArgs
from typing import get_type_hints as GetTypeHints
import urllib.error
import urllib.request
import xml.dom.minidom

import prettytable

from . import tfinta_base as base
from . import realtime_data_model as dm

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = base.__version__


# globals
_TFI_REALTIME_URL = 'https://api.irishrail.ie/realtime/realtime.asmx'
_N_RETRIES = 5
_DEFAULT_TIMEOUT = 10.0

# cache sizes (in entries)
_SMALL_CACHE = 1 << 10   # 1024

# useful aliases
_PossibleRPCArgs = dict[str, str | datetime.date]
_ExpectedRowData = dict[str, None | str | int | float | bool]
_RealtimeRowHandler = Callable[[_PossibleRPCArgs, _ExpectedRowData], dm.RealtimeRPCData]


class Error(base.Error):
  """Realtime exception."""


class ParseError(Error):
  """Exception parsing a XML RPC file."""


class RowError(ParseError):
  """Exception parsing a XML RPC row."""


class RealtimeRail:
  """Irish Rail Realtime."""

  _RPC_CALLS: dict[str, Callable[..., str]] = {
      'stations': lambda: f'{_TFI_REALTIME_URL}/getAllStationsXML',
      'running': lambda: f'{_TFI_REALTIME_URL}/getCurrentTrainsXML',
      'station': lambda station_code: (  # type:ignore
          f'{_TFI_REALTIME_URL}/getStationDataByCodeXML?StationCode={station_code.strip()}'),  # type:ignore
      'train': lambda train_code, day: (  # type:ignore
          f'{_TFI_REALTIME_URL}/getTrainMovementsXML?TrainId={train_code.strip()}'  # type:ignore
          f'&TrainDate={day.strftime("%d%%20%b%%20%Y").lower()}'),                  # type:ignore
  }

  def __init__(self) -> None:
    """Constructor."""
    self._latest = dm.LatestData(
        stations={}, running_trains={}, station_boards={}, trains={},
        stations_tm=None, running_tm=None)
    # create file handlers structure
    self._file_handlers: dict[str, tuple[_RealtimeRowHandler, type, str, dict[  # type: ignore
        str, tuple[type, bool]], set[str]]] = {
        # {realtime_type: (handler, TypedDict_row_definition, xml_row_tag_name,
        #                  {field: (type, required?)}, {required1, required2, ...})}
        'stations': (self._HandleStationXMLRow, dm.ExpectedStationXMLRowType,           # type: ignore
                     'objStation', {}, set()),
        'running': (self._HandleRunningTrainXMLRow, dm.ExpectedRunningTrainXMLRowType,  # type: ignore
                    'objTrainPositions', {}, set()),
        'station': (self._HandleStationLineXMLRow, dm.ExpectedStationLineXMLRowType,    # type: ignore
                    'objStationData', {}, set()),
        'train': (self._HandleTrainStationXMLRow, dm.ExpectedTrainStopXMLRowType,       # type: ignore
                  'objTrainMovements', {}, set()),
    }
    # fill in types, derived from the _Expected*CSVRowType TypedDicts
    for rpc_name, handlers in self._file_handlers.items():
      _, expected, _, fields, required = handlers
      for field, type_descriptor in GetTypeHints(expected).items():
        if type_descriptor in (str, int, float, bool):
          # no optional, so field is required
          required.add(field)
          fields[field] = (type_descriptor, True)
        else:
          # it is optional and something else, so find out which
          field_args = GetTypeArgs(type_descriptor)
          if len(field_args) != 2:
            raise Error(f'incorrect type len {rpc_name}/{field}: {field_args!r}')
          field_type = field_args[0] if field_args[1] == types.NoneType else field_args[1]
          if field_type not in (str, int, float, bool):
            raise Error(f'incorrect type {rpc_name}/{field}: {field_args!r}')
          fields[field] = (field_type, False)
    logging.info('Created realtime object')

  @functools.lru_cache(maxsize=_SMALL_CACHE)  # remember to update self._InvalidateCaches()
  def StationCodeFromNameFragmentOrCode(self, code: str, /) -> str:
    """If given a valid station code uses that, else searches for station (case-insensitive)."""
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
        code for code, station in self._latest.stations.items()
        if (search_str in station.description.lower() or
            (station.alias and search_str in station.alias.lower()))}
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

  def _LoadXMLFromURL(
      self, url: str, /, timeout: float = _DEFAULT_TIMEOUT) -> xml.dom.minidom.Document:
    """Get URL data."""
    # get URL, do backoff and retries
    errors: list[str] = []
    backoff = 1.0
    for attempt in range(1, _N_RETRIES + 1):
      try:
        with urllib.request.urlopen(url, timeout=timeout) as url_data:
          data = url_data.read()
        # XML errors will bubble up
        logging.info('Loaded %s from %s', base.HumanizedBytes(len(data)), url)
        return xml.dom.minidom.parseString(data)
      except urllib.error.HTTPError as err:
        if 500 <= err.code < 600:  # 5xx → retry, 4xx → fail immediately
          errors.append(f'HTTP {err.code} {err.reason}')
          logging.warning('attempt #%d: %r', attempt, err)
        else:
          raise Error(f'HTTP error loading {url!r}') from err
      except (urllib.error.URLError, socket.timeout) as err:  # network glitch or timeout
        errors.append(str(err))
        logging.warning('attempt #%d: %r', attempt, err)
      # if we get here, we'll retry (if attempts remain)
      if attempt < _N_RETRIES:
        time.sleep(backoff)
        backoff *= 2  # exponential backoff
    # all retries exhausted
    raise Error(f'Too many retries ({_N_RETRIES}) loading {url!r}: {"; ".join(errors)}')

  def _CallRPC(self, rpc_name: str, args: _PossibleRPCArgs, /) -> tuple[  # pylint: disable=too-many-locals,too-many-branches
      float, list[dm.RealtimeRPCData]]:
    """Call RPC and send rows to parsers."""
    # get fields definition and compute URL
    row_handler, _, row_xml_tag, row_types, row_required = self._file_handlers[rpc_name]
    url: str = RealtimeRail._RPC_CALLS[rpc_name](**args)
    # call external URL
    tm_now: float = time.time()
    xml_obj: xml.dom.minidom.Document = self._LoadXMLFromURL(url)
    # divide XML into rows and start parsing
    xml_elements = list(xml_obj.getElementsByTagName(row_xml_tag))
    parsed_rows: list[dm.RealtimeRPCData] = []
    xml_data: list[xml.dom.minidom.Element] = []
    row_count: int = 0
    if not xml_elements:
      return (tm_now, parsed_rows)
    for row_count, xml_row in enumerate(xml_elements):
      row_data: _ExpectedRowData = {}
      for field_name, (field_type, field_required) in row_types.items():
        xml_data = list(xml_row.getElementsByTagName(field_name))
        if len(xml_data) != 1:
          raise ParseError(
              f'repeated elements: {rpc_name}/{args}/{row_count}/{field_name}: {xml_data}')
        child = xml_data[0].firstChild
        if child is None or (field_value := child.nodeValue) is None or not field_value.strip():  # type:ignore
          # field is empty
          if field_required:
            raise ParseError(
                f'empty required field {rpc_name}/{args}/{row_count}/{field_name}: {xml_data}')
          row_data[field_name] = None
        else:
          # field has a value
          if field_type == str:
            row_data[field_name] = field_value.strip()  # vanilla string
          elif field_type == bool:
            bool_value: str = field_value.strip()
            try:
              row_data[field_name] = base.BOOL_FIELD[bool_value]  # convert to bool '0'/'1'
            except KeyError as err:
              raise ParseError(
                  f'invalid bool value {rpc_name}/{args}/{row_count}/{field_name}: '
                  f'{bool_value!r}') from err
          elif field_type in (int, float):
            try:
              row_data[field_name] = field_type(field_value)  # convert int/float
            except ValueError as err:
              raise ParseError(
                  f'invalid int/float value {rpc_name}/{args}/{row_count}/{field_name}: '
                  f'{field_value!r}') from err
          else:
            raise Error(
                f'invalid field type {rpc_name}/{args}/{row_count}/{field_name}: {field_type!r}')
      # row is parsed, check required fields
      if (missing_fields := row_required - set(row_data)):
        raise ParseError(
            f'missing required fields {missing_fields}: {rpc_name}/{row_count}: {xml_data}')
      # call handler
      parsed_rows.append(row_handler(args, row_data))
    # finished parsing all rows
    logging.info('Read %d rows from %s/%r', row_count, rpc_name, args)
    return (tm_now, parsed_rows)

  def StationsCall(self) -> list[dm.Station]:
    """Get all stations."""
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
    """Get all running trains."""
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
      self, station_code: str, /) -> tuple[dm.StationLineQueryData | None, list[dm.StationLine]]:
    """Get a station board (all trains due to serve the named station in the next 90 minutes)."""
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
            f'@ running/{station_code} {line}')
    station_lines.sort()
    self._latest.station_boards[station_code] = (tm, sample_query, station_lines)
    return (copy.deepcopy(sample_query), list(station_lines))  # make a new copy

  def TrainDataCall(self, train_code: str, day: datetime.date, /) -> tuple[
      dm.TrainStopQueryData | None, list[dm.TrainStop]]:
    """Get train realtime."""
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
            f'@ train/{train_code}/{day} {line}')
    train_stops.sort()
    self._latest.trains.setdefault(train_code, {})[day] = (
        tm, sample_query, {s.station_order: s for s in train_stops})
    if (stop_seqs := set(self._latest.trains[train_code][day][2])) != set(
        range(1, len(self._latest.trains[train_code][day][2]) + 1)):
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

  def _HandleStationXMLRow(
      self, params: _PossibleRPCArgs, row: dm.ExpectedStationXMLRowType, /) -> dm.Station:
    """Handler: Station.

    Args:
      params: dict with args for calling XML URL-calling method
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    if row['StationId'] < 1:
      raise RowError(f'invalid StationId {row["StationId"]} @ station/{params!r}')
    return dm.Station(
        id=row['StationId'],
        code=row['StationCode'].upper(),
        description=row['StationDesc'],
        location=(None if row['StationLatitude'] == 0.0 and row['StationLongitude'] == 0.0 else
                  base.Point(latitude=row['StationLatitude'], longitude=row['StationLongitude'])),
        alias=row['StationAlias'])

  def _HandleRunningTrainXMLRow(
      self, params: _PossibleRPCArgs,
      row: dm.ExpectedRunningTrainXMLRowType, /) -> dm.RunningTrain:
    """Handler: RunningTrain.

    Args:
      params: dict with args for calling XML URL-calling method
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
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
        position=(None if row['TrainLatitude'] == 0 and row['TrainLongitude'] == 0 else
                  base.Point(latitude=row['TrainLatitude'], longitude=row['TrainLongitude'])),
        message=html.escape(row['PublicMessage'].replace('\\n', '\n')))

  def _HandleStationLineXMLRow(
      self, params: _PossibleRPCArgs, row: dm.ExpectedStationLineXMLRowType, /) -> dm.StationLine:
    """Handler: StationLine.

    Args:
      params: dict with args for calling XML URL-calling method
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    day: datetime.date = base.DATE_OBJ_REALTIME(row['Traindate'])
    station_code: str = row['Stationcode']
    if station_code != params['station_code']:
      raise Error(
          f'station mismatch: {params["station_code"]} versus {station_code} @ station/{params!r}')
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
      train_type: dm.TrainType = dm.TRAIN_TYPE_STR_MAP.get(row['Traintype'].upper(), dm.TrainType.UNKNOWN)
    except KeyError as err:
      raise Error(f'invalid Locationtype/Traintype: {row!r} @ station/{params!r}') from err
    return dm.StationLine(
        query=dm.StationLineQueryData(
            tm_server=base.DATETIME_FROM_ISO(row['Servertime']),
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
            departure=base.DayTime.FromHMS(row['Destinationtime'] + ':00')),
        status=row['Status'],
        train_type=train_type,
        last_location=row['Lastlocation'],
        due_in=base.DayTime(time=row['Duein']),
        late=row['Late'],
        location_type=loc_type,
        scheduled=base.DayRange(
            arrival=(None if row['Scharrival'] == '00:00' else
                     base.DayTime.FromHMS(row['Scharrival'] + ':00')),
            departure=(None if row['Schdepart'] == '00:00' else
                       base.DayTime.FromHMS(row['Schdepart'] + ':00')),
            nullable=True),
        expected=base.DayRange(
            arrival=(None if row['Exparrival'] == '00:00' else
                     base.DayTime.FromHMS(row['Exparrival'] + ':00')),
            departure=(None if row['Expdepart'] == '00:00' else
                       base.DayTime.FromHMS(row['Expdepart'] + ':00')),
            nullable=True, strict=False),
        direction=row['Direction'])

  def _HandleTrainStationXMLRow(
      self, params: _PossibleRPCArgs,
      row: dm.ExpectedTrainStopXMLRowType, /) -> dm.TrainStop:
    """Handler: TrainStation.

    Args:
      params: dict with args for calling XML URL-calling method
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
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
            arrival=(None if row['ScheduledArrival'] == '00:00:00' else
                     base.DayTime.FromHMS(row['ScheduledArrival'])),
            departure=(None if row['ScheduledDeparture'] == '00:00:00' else
                       base.DayTime.FromHMS(row['ScheduledDeparture'])),
            nullable=True),
        expected=base.DayRange(
            arrival=(None if row['ExpectedArrival'] == '00:00:00' else
                     base.DayTime.FromHMS(row['ExpectedArrival'])),
            departure=(None if row['ExpectedDeparture'] == '00:00:00' else
                       base.DayTime.FromHMS(row['ExpectedDeparture'])),
            nullable=True, strict=False),
        actual=base.DayRange(
            arrival=(None if row['Arrival'] is None or row['Arrival'] == '00:00:00' else
                     base.DayTime.FromHMS(row['Arrival'])),
            departure=(None if row['Departure'] is None or row['Departure'] == '00:00:00' else
                       base.DayTime.FromHMS(row['Departure'])),
            nullable=True),
        auto_arrival=False if row['AutoArrival'] is None else row['AutoArrival'],
        auto_depart=False if row['AutoDepart'] is None else row['AutoDepart'],
        stop_type=stop_type)

  ##################################################################################################
  # REALTIME PRETTY PRINTS
  ##################################################################################################

  def PrettyPrintStations(self) -> Generator[str, None, None]:
    """Generate a pretty version of all stations."""
    if self._latest.stations_tm is None or not self._latest.stations:
      self.StationsCall()  # lazy load
    yield (f'{base.MAGENTA}Irish Rail Stations @ {base.BOLD}'
           f'{base.STD_TIME_STRING(self._latest.stations_tm)}{base.NULL}')  # type: ignore
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.BOLD}{base.CYAN}ID{base.NULL}',
         f'{base.BOLD}{base.CYAN}Code{base.NULL}',
         f'{base.BOLD}{base.CYAN}Name{base.NULL}',
         f'{base.BOLD}{base.CYAN}Alias{base.NULL}',
         f'{base.BOLD}{base.CYAN}Location °{base.NULL}',
         f'{base.BOLD}{base.CYAN}Location{base.NULL}'])
    for station in sorted(self._latest.stations.values()):
      lat, lon = (None, None) if station.location is None else station.location.ToDMS()
      table.add_row([
          f'{base.BOLD}{base.CYAN}{station.id}{base.NULL}',
          f'{base.BOLD}{station.code}{base.NULL}',
          f'{base.BOLD}{base.YELLOW}{station.description}{base.NULL}',
          f'{base.BOLD}{station.alias if station.alias else base.NULL_TEXT}{base.NULL}',
          f'{base.BOLD}{base.YELLOW}{lat if lat else base.NULL_TEXT}{base.NULL}\n'
          f'{base.BOLD}{base.YELLOW}{lon if lon else base.NULL_TEXT}{base.NULL}',
          f'{base.BOLD}{f"{station.location.latitude:0.7f}" if station.location else base.NULL_TEXT}'
          f'{base.NULL}\n'
          f'{base.BOLD}{f"{station.location.longitude:0.7f}" if station.location else base.NULL_TEXT}'
          f'{base.NULL}',
      ])
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # type:ignore

  def PrettyPrintRunning(self) -> Generator[str, None, None]:
    """Generate a pretty version of running trains."""
    if self._latest.running_tm is None or not self._latest.running_trains:
      self.RunningTrainsCall()  # lazy load
    yield (f'{base.MAGENTA}Irish Rail Running Trains @ {base.BOLD}'
           f'{base.STD_TIME_STRING(self._latest.running_tm)}{base.NULL}')  # type: ignore
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.BOLD}{base.CYAN}Train{base.NULL}',
         f'{base.BOLD}{base.CYAN}Direction{base.NULL}',
         f'{base.BOLD}{base.CYAN}Location °{base.NULL}',
         f'{base.BOLD}{base.CYAN}Location{base.NULL}',
         f'{base.BOLD}{base.CYAN}Message{base.NULL}'])
    for train in sorted(self._latest.running_trains.values()):
      lat, lon = train.position.ToDMS() if train.position is not None else (None, None)
      train_message: str = ('\n'.join(train.message.splitlines()[1:])
                            if train.message.startswith(train.code + '\n') else train.message)
      table.add_row([
          f'{base.BOLD}{base.CYAN}{train.code}{base.NULL}\n'
          f'{base.BOLD}{dm.TRAIN_STATUS_STR[train.status]}{base.NULL}',
          f'{base.BOLD}{base.LIMITED_TEXT(train.direction, 15)}{base.NULL}',
          f'{base.BOLD}{base.YELLOW if lat else ""}{lat if lat else base.NULL_TEXT}{base.NULL}\n'
          f'{base.BOLD}{base.YELLOW if lon else ""}{lon if lon else base.NULL_TEXT}{base.NULL}',
          f'{base.BOLD}{f"{train.position.latitude:0.7f}" if train.position else base.NULL_TEXT}'
          f'{base.NULL}\n'
          f'{base.BOLD}{f"{train.position.longitude:0.7f}" if train.position else base.NULL_TEXT}'
          f'{base.NULL}',
          '\n'.join(f'{base.BOLD}{base.LIMITED_TEXT(m, 50)}{base.NULL}'
                    for m in train_message.split('\n')),
      ])
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # type:ignore

  def PrettyPrintStation(self, /, *, station_code: str) -> Generator[str, None, None]:
    """Generate a pretty version of station board."""
    station_code = station_code.upper()
    if station_code not in self._latest.station_boards:
      self.StationBoardCall(station_code)  # lazy load
    if self._latest.stations_tm is None or not self._latest.stations:
      self.StationsCall()  # lazy load
    tm, _, station_trains = self._latest.station_boards[station_code]
    yield (f'{base.MAGENTA}Irish Rail Station {base.BOLD}'
           f'{self._latest.stations[station_code].description} '
           f'({station_code}){base.NULL}{base.MAGENTA} Board @ '
           f'{base.BOLD}{base.STD_TIME_STRING(tm)}{base.NULL}')
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.BOLD}{base.CYAN}Train{base.NULL}',
         f'{base.BOLD}{base.CYAN}Origin{base.NULL}',
         f'{base.BOLD}{base.CYAN}Dest.{base.NULL}',
         f'{base.BOLD}{base.CYAN}Due{base.NULL}',
         f'{base.BOLD}{base.CYAN}Arrival{base.NULL}',
         f'{base.BOLD}{base.CYAN}Depart.{base.NULL}',
         f'{base.BOLD}{base.CYAN}Late{base.NULL}',
         f'{base.BOLD}{base.CYAN}Status{base.NULL}',
         f'{base.BOLD}{base.CYAN}Location{base.NULL}'])
    for line in station_trains:
      direction_text: str = (
          '(N)' if line.direction.lower() == 'northbound' else (
              '(S)' if line.direction.lower() == 'southbound' else
              base.LIMITED_TEXT(line.direction, 15)))
      table.add_row([
          f'{base.BOLD}{base.CYAN}{line.train_code}{base.NULL}\n'
          f'{base.BOLD}{direction_text}{base.NULL}' +
          (f'\n{base.BOLD}{line.train_type.name}{base.NULL}'
           if line.train_type != dm.TrainType.UNKNOWN else ''),
          f'{base.BOLD}{line.origin_code}{base.NULL}\n'
          f'{base.BOLD}{base.LIMITED_TEXT(line.origin_name, 15)}{base.NULL}\n'
          f'{base.BOLD}{line.trip.arrival.ToHMS() if line.trip.arrival else base.NULL_TEXT}'
          f'{base.NULL}',
          f'{base.BOLD}{base.YELLOW}{line.destination_code}{base.NULL}\n'
          f'{base.BOLD}{base.YELLOW}{base.LIMITED_TEXT(line.destination_name, 15)}{base.NULL}\n'
          f'{base.BOLD}{line.trip.departure.ToHMS() if line.trip.departure else base.NULL_TEXT}'
          f'{base.NULL}',
          f'{base.BOLD}{line.due_in.time:+}{base.NULL}',
          f'{base.BOLD}{base.GREEN}'
          f'{line.scheduled.arrival.ToHMS() if line.scheduled.arrival else base.NULL_TEXT}{base.NULL}' +
          ('' if not line.expected.arrival or line.expected.arrival == line.scheduled.arrival else
           f'\n{base.BOLD}{base.RED}{line.expected.arrival.ToHMS()}{base.NULL}'),
          f'{base.BOLD}{base.GREEN}'
          f'{line.scheduled.departure.ToHMS() if line.scheduled.departure else base.NULL_TEXT}{base.NULL}' +
          ('' if not line.expected.departure or line.expected.departure == line.scheduled.departure else
           f'\n{base.BOLD}{base.RED}{line.expected.departure.ToHMS()}{base.NULL}'),
          '\n' if not line.late else
          f'\n{base.BOLD}{base.RED if line.late > 0 else base.YELLOW}{line.late:+}{base.NULL}',
          f'\n{base.BOLD}{base.LIMITED_TEXT(line.status, 15) if line.status else base.NULL_TEXT}'
          f'{base.NULL}',
          f'\n{base.BOLD}'
          f'{base.LIMITED_TEXT(line.last_location, 15) if line.last_location else base.NULL_TEXT}'
          f'{base.NULL}',
      ])
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # type:ignore

  def PrettyPrintTrain(
      self, /, *, train_code: str, day: datetime.date) -> Generator[str, None, None]:
    """Generate a pretty version of single train data."""
    train_code = train_code.upper()
    if train_code not in self._latest.trains or day not in self._latest.trains[train_code]:
      self.TrainDataCall(train_code, day)
    tm, query, train_stops = self._latest.trains[train_code][day]
    yield (f'{base.MAGENTA}Irish Rail Train {base.BOLD}{train_code}{base.NULL}{base.MAGENTA} @ '
           f'{base.BOLD}{base.STD_TIME_STRING(tm)}{base.NULL}')
    yield ''
    yield f'Day:         {base.BOLD}{base.YELLOW}{base.PRETTY_DATE(query.day)}{base.NULL}'
    yield (f'Origin:      {base.BOLD}{base.YELLOW}{query.origin_name} '
           f'({query.origin_code}){base.NULL}')
    yield (f'Destination: {base.BOLD}{base.YELLOW}{query.destination_name} '
           f'({query.destination_code}){base.NULL}')
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.BOLD}{base.CYAN}#{base.NULL}',
         f'{base.BOLD}{base.CYAN}Stop{base.NULL}',
         f'{base.BOLD}{base.CYAN}Arr.(Expect){base.NULL}',
         f'{base.BOLD}{base.CYAN}A.(Actual){base.NULL}',
         f'{base.BOLD}{base.CYAN}Depart.(Expect){base.NULL}',
         f'{base.BOLD}{base.CYAN}D.(Actual){base.NULL}',
         f'{base.BOLD}{base.CYAN}Late(Min){base.NULL}'])
    for seq in range(1, len(train_stops) + 1):
      stop: dm.TrainStop = train_stops[seq]
      late: int | None = (None if stop.actual.arrival is None or stop.scheduled.arrival is None else
                          stop.actual.arrival.time - stop.scheduled.arrival.time)
      stop_type: str = ('' if stop.stop_type == dm.StopType.UNKNOWN else
                        f'\n{base.BOLD}{base.YELLOW}{stop.stop_type.name}{base.NULL}')
      table.add_row([
          f'{base.BOLD}{base.CYAN}{seq}{base.NULL}{stop_type}',
          f'{base.BOLD}{base.YELLOW}{stop.station_code}{base.NULL}\n'
          f'{base.BOLD}{base.YELLOW}'
          f'{base.LIMITED_TEXT(stop.station_name, 15) if stop.station_name else "????"}{base.NULL}\n'
          f'{base.BOLD}{dm.LOCATION_TYPE_STR[stop.location_type]}{base.NULL}',
          f'{base.BOLD}{base.GREEN}'
          f'{stop.scheduled.arrival.ToHMS() if stop.scheduled.arrival else base.NULL_TEXT}{base.NULL}' +
          ('' if not stop.expected.arrival or stop.expected.arrival == stop.scheduled.arrival else
           f'\n{base.BOLD}{base.RED}{stop.expected.arrival.ToHMS()}{base.NULL}') +
          (f'\n{base.BOLD}{dm.PRETTY_AUTO(True)}' if stop.auto_arrival else ''),
          f'{base.BOLD}{base.YELLOW}'
          f'{stop.actual.arrival.ToHMS() if stop.actual.arrival else base.NULL_TEXT}{base.NULL}',
          f'{base.BOLD}{base.GREEN}'
          f'{stop.scheduled.departure.ToHMS() if stop.scheduled.departure else base.NULL_TEXT}{base.NULL}' +
          ('' if not stop.expected.departure or stop.expected.departure == stop.scheduled.departure else
           f'\n{base.BOLD}{base.RED}{stop.expected.departure.ToHMS()}{base.NULL}') +
          (f'\n{base.BOLD}{dm.PRETTY_AUTO(True)}' if stop.auto_depart else ''),
          f'{base.BOLD}{base.YELLOW}'
          f'{stop.actual.departure.ToHMS() if stop.actual.departure else base.NULL_TEXT}{base.NULL}',
          f'{base.BOLD}{base.NULL_TEXT if late is None else (f"{base.RED}{late / 60.0:+0.2f}" if late > 0 else f"{base.GREEN}{late / 60.0:+0.2f}")}{base.NULL}',
      ])
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # type:ignore


def main(argv: list[str] | None = None) -> int:  # pylint: disable=invalid-name,too-many-locals
  """Main entry point."""
  # parse the input arguments, add subparser for `command`
  parser: argparse.ArgumentParser = argparse.ArgumentParser()
  command_arg_subparsers = parser.add_subparsers(dest='command')
  # "print" command
  print_parser: argparse.ArgumentParser = command_arg_subparsers.add_parser(
      'print', help='Print RPC Call')
  print_arg_subparsers = print_parser.add_subparsers(dest='print_command')
  print_arg_subparsers.add_parser('stations', help='Print All System Stations')
  print_arg_subparsers.add_parser('running', help='Print Running Trains')
  station_parser = print_arg_subparsers.add_parser('station', help='Print Station Board')
  station_parser.add_argument(
      '-c', '--code', type=str, default='',
      help='Either a 5-letter station code (ex: "LURGN") or a search string that can '
      'be identified as a station (ex: "lurgan")')
  train_parser = print_arg_subparsers.add_parser('train', help='Print Train Movements')
  train_parser.add_argument('-c', '--code', type=str, default='', help='Train code (ex: "E108")')
  train_parser.add_argument(
      '-d', '--day', type=str, default='',
      help='day to consider in "YYYYMMDD" format (default: TODAY/NOW)')
  # ALL commands
  parser.add_argument(
      '-v', '--verbose', action='count', default=0,
      help='Increase verbosity (use -v, -vv, -vvv, -vvvv for ERR/WARN/INFO/DEBUG output)')
  args: argparse.Namespace = parser.parse_args(argv)
  levels: list[int] = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
  logging.basicConfig(level=levels[min(args.verbose, len(levels) - 1)], format=base.LOG_FORMAT)  # type:ignore
  command = args.command.lower().strip() if args.command else ''
  realtime = RealtimeRail()
  # look at main command
  match command:
    case 'print':
      # look at sub-command for print
      print_command = args.print_command.lower().strip() if args.print_command else ''
      print()
      match print_command:
        case 'stations':
          for line in realtime.PrettyPrintStations():
            print(line)
        case 'running':
          for line in realtime.PrettyPrintRunning():
            print(line)
        case 'station':
          for line in realtime.PrettyPrintStation(
              station_code=realtime.StationCodeFromNameFragmentOrCode(args.code)):
            print(line)
        case 'train':
          for line in realtime.PrettyPrintTrain(
              train_code=args.code,
              day=base.DATE_OBJ_GTFS(args.day) if args.day else datetime.date.today()):
            print(line)
        case _:
          raise NotImplementedError()
      print()
    case _:
      raise NotImplementedError()
  return 0


if __name__ == '__main__':
  sys.exit(main())
