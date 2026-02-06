# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""realtime.py unittest."""

from __future__ import annotations

import datetime
import os.path
import urllib.error
from collections import abc
from typing import Self
from unittest import mock
from xml.dom import minidom  # noqa: S408

import pytest
import typeguard
from click import testing as click_testing
from src.tfinta import realtime
from src.tfinta import realtime_data_model as dm
from src.tfinta import tfinta_base as base
from transcrypto.utils import logging as tc_logging
from typer import testing as typer_testing

from . import realtime_data, util

_REALTIME_DIR: str = os.path.join(util.DATA_DIR, 'realtime')  # noqa: PTH118

TEST_XMLS: dict[str, str] = {
  'stations': os.path.join(_REALTIME_DIR, 'getAllStations.xml'),  # noqa: PTH118
  'running': os.path.join(_REALTIME_DIR, 'getCurrentTrains.xml'),  # noqa: PTH118
  'station': os.path.join(_REALTIME_DIR, 'getStationDataByCode.xml'),  # noqa: PTH118
  'train': os.path.join(_REALTIME_DIR, 'getTrainMovements.xml'),  # noqa: PTH118
}


@pytest.fixture(autouse=True)
def reset_cli_logging_singletons() -> None:
  """Reset global console/logging state between tests.

  The CLI callback initializes a global Rich console singleton via InitLogging().
  Tests invoke the CLI multiple times across test cases, so we must reset that
  singleton to keep tests isolated.
  """
  tc_logging.ResetConsole()


class _FakeDate(datetime.date):
  """Fake datetime.date so we can monkeypatch.setattr(datetime, 'date', FakeDate)."""

  @classmethod
  def today(cls) -> Self:
    """Test date.

    Returns:
      Test date.

    """
    return cls(2025, 6, 29)


@pytest.mark.parametrize(
  ('call_names', 'call_obj', 'expected_obj', 'expected_output'),
  [
    (
      [
        ('stations', {}),
      ],
      realtime.RealtimeRail.PrettyPrintStations,
      realtime_data.STATIONS_OBJ,
      realtime_data.STATIONS_TABLE,
    ),
    (
      [
        ('running', {}),
      ],
      realtime.RealtimeRail.PrettyPrintRunning,
      realtime_data.RUNNING_OBJ,
      realtime_data.RUNNING_TABLE,
    ),
    (
      [
        ('station', {'station_code': 'MHIDE'}),
        ('stations', {}),
      ],
      realtime.RealtimeRail.PrettyPrintStation,
      realtime_data.STATION_OBJ,
      realtime_data.STATION_TABLE,
    ),
    (
      [
        ('train', {'train_code': 'E108', 'day': datetime.date(2025, 6, 29)}),
        ('stations', {}),
      ],
      realtime.RealtimeRail.PrettyPrintTrain,
      realtime_data.TRAIN_OBJ,
      realtime_data.TRAIN_TABLE,
    ),
  ],  # pyright: ignore[reportUnknownArgumentType]
)
@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_RealtimeRail_StationsCall(
  mock_open: mock.MagicMock,
  mock_time: mock.MagicMock,
  call_names: list[tuple[str, realtime._PossibleRPCArgs]],
  call_obj: abc.Callable[..., abc.Generator[str, None, None]],
  expected_obj: dm.LatestData,
  expected_output: util.ExpectedPrettyPrint,
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """Test."""
  monkeypatch.setattr(realtime.datetime, 'date', _FakeDate)  # type: ignore
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.side_effect = [util.FakeHTTPFile(TEST_XMLS[c]) for c, _ in call_names]
  # call
  rt = realtime.RealtimeRail()
  with typeguard.suppress_type_checks():
    util.AssertPrettyPrint(expected_output, call_obj(rt, **call_names[0][1]))
  # check data
  assert rt._latest == expected_obj
  assert len(mock_open.call_args_list) == len(call_names)
  for i, (c, p) in enumerate(call_names):
    assert mock_open.call_args_list[i] == mock.call(realtime._RPC_CALLS[c](p), timeout=10.0)


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_main_print_stations(mock_realtime: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_realtime.return_value = db_obj
  db_obj.PrettyPrintStations.return_value = ['foo', 'bar']
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    realtime.app, ['print', 'stations']
  )
  assert result.exit_code == 0
  mock_realtime.assert_called_once_with()
  db_obj.PrettyPrintStations.assert_called_once_with()


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_main_print_running(mock_realtime: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_realtime.return_value = db_obj
  db_obj.PrettyPrintRunning.return_value = ['foo', 'bar']
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    realtime.app, ['print', 'running']
  )
  assert result.exit_code == 0
  mock_realtime.assert_called_once_with()
  db_obj.PrettyPrintRunning.assert_called_once_with()


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_main_print_station(mock_realtime: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_realtime.return_value = db_obj
  db_obj.StationCodeFromNameFragmentOrCode.return_value = 'MHIDE'
  db_obj.PrettyPrintStation.return_value = ['foo', 'bar']
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    realtime.app, ['print', 'station', 'malahide']
  )
  assert result.exit_code == 0
  mock_realtime.assert_called_once_with()
  db_obj.StationCodeFromNameFragmentOrCode.assert_called_once_with('malahide')
  db_obj.PrettyPrintStation.assert_called_once_with(station_code='MHIDE')


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_main_print_train(mock_realtime: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_realtime.return_value = db_obj
  db_obj.PrettyPrintTrain.return_value = ['foo', 'bar']
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    realtime.app, ['print', 'train', 'E108', '20250701']
  )
  assert result.exit_code == 0
  mock_realtime.assert_called_once_with()
  db_obj.PrettyPrintTrain.assert_called_once_with(train_code='E108', day=datetime.date(2025, 7, 1))


def test_main_version() -> None:
  """Test --version flag."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(realtime.app, ['--version'])
  assert result.exit_code == 0


def test_main_markdown() -> None:
  """Test markdown command."""
  with mock.patch('transcrypto.utils.logging.InitLogging') as mock_init_logging:
    mock_console = mock.MagicMock()
    mock_init_logging.return_value = (mock_console, 0, False)
    result: click_testing.Result = typer_testing.CliRunner().invoke(realtime.app, ['markdown'])
    assert result.exit_code == 0
    mock_console.print.assert_called_once()


# _LoadXMLFromURL tests


@mock.patch('src.tfinta.realtime.time.sleep', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_LoadXMLFromURL_http_4xx(mock_open: mock.MagicMock, _sleep: mock.MagicMock) -> None:  # noqa: PT019
  """Test _LoadXMLFromURL raises immediately on 4xx errors."""
  mock_open.side_effect = urllib.error.HTTPError(
    'http://test',
    404,
    'Not Found',
    {},  # pyright: ignore[reportArgumentType]
    None,
  )
  with pytest.raises(realtime.Error, match='HTTP error'):
    realtime._LoadXMLFromURL('http://test')


@mock.patch('src.tfinta.realtime.time.sleep', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_LoadXMLFromURL_http_5xx_retries(
  mock_open: mock.MagicMock, mock_sleep: mock.MagicMock
) -> None:
  """Test _LoadXMLFromURL retries on 5xx errors then raises."""
  mock_open.side_effect = urllib.error.HTTPError(
    'http://test',
    500,
    'Server Error',
    {},  # pyright: ignore[reportArgumentType]
    None,
  )
  with pytest.raises(realtime.Error, match='Too many retries'):
    realtime._LoadXMLFromURL('http://test')
  assert mock_open.call_count == realtime._N_RETRIES
  assert mock_sleep.call_count == realtime._N_RETRIES - 1


@mock.patch('src.tfinta.realtime.time.sleep', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_LoadXMLFromURL_timeout_retries(mock_open: mock.MagicMock, _sleep: mock.MagicMock) -> None:  # noqa: PT019
  """Test _LoadXMLFromURL retries on TimeoutError then raises."""
  mock_open.side_effect = TimeoutError('Connection timed out')
  with pytest.raises(realtime.Error, match='Too many retries'):
    realtime._LoadXMLFromURL('http://test')
  assert mock_open.call_count == realtime._N_RETRIES


@mock.patch('src.tfinta.realtime.time.sleep', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_LoadXMLFromURL_retry_then_success(
  mock_open: mock.MagicMock,
  _sleep: mock.MagicMock,  # noqa: PT019
) -> None:
  """Test _LoadXMLFromURL succeeds after retries."""
  xml_data = b'<root><data>test</data></root>'
  mock_open.side_effect = [
    urllib.error.HTTPError('http://test', 500, 'Error', {}, None),  # type: ignore
    util.FakeHTTPStream(xml_data),  # success
  ]
  result: minidom.Document = realtime._LoadXMLFromURL('http://test')
  assert result is not None and mock_open.call_count == 2


@mock.patch('src.tfinta.realtime.time.sleep', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_LoadXMLFromURL_urlerror_retries(mock_open: mock.MagicMock, _sleep: mock.MagicMock) -> None:  # noqa: PT019
  """Test _LoadXMLFromURL retries on URLError."""
  mock_open.side_effect = urllib.error.URLError('Network unreachable')
  with pytest.raises(realtime.Error, match='Too many retries'):
    realtime._LoadXMLFromURL('http://test')
  assert mock_open.call_count == realtime._N_RETRIES


# RealtimeRail error path tests


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_StationCodeFromNameFragmentOrCode_errors(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test StationCodeFromNameFragmentOrCode error branches."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  # not found
  with pytest.raises(realtime.Error, match='not found'):
    rt.StationCodeFromNameFragmentOrCode('zzzzz_nonexistent')
  # already a valid code
  assert rt.StationCodeFromNameFragmentOrCode('MHIDE') == 'MHIDE'


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_StationsCall_empty(mock_open: mock.MagicMock, mock_time: mock.MagicMock) -> None:
  """Test StationsCall with empty result."""
  mock_time.return_value = realtime_data.RT_TIME
  empty_xml = (
    b'<ArrayOfObjStation xmlns="http://api.irishrail.ie/realtime/" '
    b'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true" />'
  )
  mock_open.return_value = util.FakeHTTPStream(empty_xml)
  rt = realtime.RealtimeRail()
  assert rt.StationsCall() == []


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_RunningTrainsCall_empty(mock_open: mock.MagicMock, mock_time: mock.MagicMock) -> None:
  """Test RunningTrainsCall with empty result."""
  mock_time.return_value = realtime_data.RT_TIME
  empty_xml = b'<ArrayOfObjTrainPositions xmlns="http://api.irishrail.ie/realtime/" />'
  mock_open.return_value = util.FakeHTTPStream(empty_xml)
  rt = realtime.RealtimeRail()
  assert rt.RunningTrainsCall() == []


def test_StationBoardCall_empty_code() -> None:
  """Test StationBoardCall with empty station code."""
  rt = realtime.RealtimeRail()
  with pytest.raises(realtime.Error, match='empty station code'):
    rt.StationBoardCall(' \t')


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_StationBoardCall_empty_result(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test StationBoardCall with empty result returns (None, [])."""
  mock_time.return_value = realtime_data.RT_TIME
  empty_xml = b'<ArrayOfObjStationData xmlns="http://api.irishrail.ie/realtime/" />'
  mock_open.return_value = util.FakeHTTPStream(empty_xml)
  rt = realtime.RealtimeRail()
  query, lines = rt.StationBoardCall('MHIDE')
  assert query is None and lines == []


def test_TrainDataCall_empty_code() -> None:
  """Test TrainDataCall with empty train code."""
  rt = realtime.RealtimeRail()
  with pytest.raises(realtime.Error, match='empty train code'):
    rt.TrainDataCall(' \t', datetime.date(2025, 6, 29))


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_TrainDataCall_empty_result(mock_open: mock.MagicMock, mock_time: mock.MagicMock) -> None:
  """Test TrainDataCall with empty result returns (None, [])."""
  mock_time.return_value = realtime_data.RT_TIME
  empty_xml = b'<ArrayOfObjTrainMovements xmlns="http://api.irishrail.ie/realtime/" />'
  mock_open.return_value = util.FakeHTTPStream(empty_xml)
  rt = realtime.RealtimeRail()
  query, stops = rt.TrainDataCall('E108', datetime.date(2025, 6, 29))
  assert query is None
  assert stops == []


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_HandleStationXMLRow_invalid_id(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test _HandleStationXMLRow with invalid StationId."""
  mock_time.return_value = realtime_data.RT_TIME
  xml_data = (
    b'<ArrayOfObjStation xmlns="http://api.irishrail.ie/realtime/">'
    b'<objStation>'
    b'<StationId>0</StationId>'
    b'<StationCode>TEST</StationCode>'
    b'<StationDesc>Test</StationDesc>'
    b'<StationLatitude>0.0</StationLatitude>'
    b'<StationLongitude>0.0</StationLongitude>'
    b'<StationAlias></StationAlias>'
    b'</objStation>'
    b'</ArrayOfObjStation>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  rt = realtime.RealtimeRail()
  with pytest.raises(realtime.RowError, match='invalid StationId'):
    rt.StationsCall()


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_HandleRunningTrainXMLRow_invalid_status(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test _HandleRunningTrainXMLRow with invalid TrainStatus."""
  mock_time.return_value = realtime_data.RT_TIME
  xml_data = (
    b'<ArrayOfObjTrainPositions xmlns="http://api.irishrail.ie/realtime/">'
    b'<objTrainPositions>'
    b'<TrainCode>E108</TrainCode>'
    b'<TrainStatus>X</TrainStatus>'
    b'<TrainDate>29 Jun 2025</TrainDate>'
    b'<Direction>Northbound</Direction>'
    b'<TrainLatitude>53.0</TrainLatitude>'
    b'<TrainLongitude>-6.0</TrainLongitude>'
    b'<PublicMessage>Test</PublicMessage>'
    b'</objTrainPositions>'
    b'</ArrayOfObjTrainPositions>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  rt = realtime.RealtimeRail()
  with pytest.raises(realtime.Error, match='invalid TrainStatus'):
    rt.RunningTrainsCall()


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_HandleStationLineXMLRow_station_mismatch(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test _HandleStationLineXMLRow with station code mismatch."""
  mock_time.return_value = realtime_data.RT_TIME
  # Load stations first
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  # Now call station board with mismatched station code in XML
  xml_data = (
    b'<ArrayOfObjStationData xmlns="http://api.irishrail.ie/realtime/">'
    b'<objStationData>'
    b'<Servertime>2025-06-29T09:14:27.863</Servertime>'
    b'<Traincode>E108</Traincode>'
    b'<Stationfullname>Malahide</Stationfullname>'
    b'<Stationcode>WRONG</Stationcode>'
    b'<Querytime>09:14:27</Querytime>'
    b'<Traindate>29 Jun 2025</Traindate>'
    b'<Origin>Malahide</Origin>'
    b'<Destination>Greystones</Destination>'
    b'<Origintime>09:00</Origintime>'
    b'<Destinationtime>10:00</Destinationtime>'
    b'<Status>En Route</Status>'
    b'<Lastlocation>Departed Malahide</Lastlocation>'
    b'<Duein>5</Duein>'
    b'<Late>0</Late>'
    b'<Exparrival>09:10</Exparrival>'
    b'<Expdepart>09:12</Expdepart>'
    b'<Scharrival>09:10</Scharrival>'
    b'<Schdepart>09:12</Schdepart>'
    b'<Direction>Southbound</Direction>'
    b'<Traintype>DART</Traintype>'
    b'<Locationtype>S</Locationtype>'
    b'</objStationData>'
    b'</ArrayOfObjStationData>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  with pytest.raises(realtime.Error, match='station mismatch'):
    rt.StationBoardCall('MHIDE')


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_HandleStationLineXMLRow_invalid_locationtype(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test _HandleStationLineXMLRow with invalid Locationtype."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  xml_data = (
    b'<ArrayOfObjStationData xmlns="http://api.irishrail.ie/realtime/">'
    b'<objStationData>'
    b'<Servertime>2025-06-29T09:14:27.863</Servertime>'
    b'<Traincode>E108</Traincode>'
    b'<Stationfullname>Malahide</Stationfullname>'
    b'<Stationcode>MHIDE</Stationcode>'
    b'<Querytime>09:14:27</Querytime>'
    b'<Traindate>29 Jun 2025</Traindate>'
    b'<Origin>Malahide</Origin>'
    b'<Destination>Greystones</Destination>'
    b'<Origintime>09:00</Origintime>'
    b'<Destinationtime>10:00</Destinationtime>'
    b'<Status>En Route</Status>'
    b'<Lastlocation>Departed Malahide</Lastlocation>'
    b'<Duein>5</Duein>'
    b'<Late>0</Late>'
    b'<Exparrival>09:10</Exparrival>'
    b'<Expdepart>09:12</Expdepart>'
    b'<Scharrival>09:10</Scharrival>'
    b'<Schdepart>09:12</Schdepart>'
    b'<Direction>Southbound</Direction>'
    b'<Traintype>DART</Traintype>'
    b'<Locationtype>Z</Locationtype>'
    b'</objStationData>'
    b'</ArrayOfObjStationData>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  with pytest.raises(realtime.Error, match='invalid Locationtype'):
    rt.StationBoardCall('MHIDE')


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_HandleStationLineXMLRow_unknown_origin_dest(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test _HandleStationLineXMLRow with unknown origin/destination station names."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  xml_data = (
    b'<ArrayOfObjStationData xmlns="http://api.irishrail.ie/realtime/">'
    b'<objStationData>'
    b'<Servertime>2025-06-29T09:14:27.863</Servertime>'
    b'<Traincode>E108</Traincode>'
    b'<Stationfullname>Malahide</Stationfullname>'
    b'<Stationcode>MHIDE</Stationcode>'
    b'<Querytime>09:14:27</Querytime>'
    b'<Traindate>29 Jun 2025</Traindate>'
    b'<Origin>ZZZZUNKNOWN_STATION</Origin>'  # cspell: disable-line
    b'<Destination>ZZZZUNKNOWN_STATION_2</Destination>'  # cspell: disable-line
    b'<Origintime>09:00</Origintime>'
    b'<Destinationtime>10:00</Destinationtime>'
    b'<Status>En Route</Status>'
    b'<Lastlocation>Departed Malahide</Lastlocation>'
    b'<Duein>5</Duein>'
    b'<Late>0</Late>'
    b'<Exparrival>09:10</Exparrival>'
    b'<Expdepart>09:12</Expdepart>'
    b'<Scharrival>09:10</Scharrival>'
    b'<Schdepart>09:12</Schdepart>'
    b'<Direction>Southbound</Direction>'
    b'<Traintype>DART</Traintype>'
    b'<Locationtype>S</Locationtype>'
    b'</objStationData>'
    b'</ArrayOfObjStationData>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  query, lines = rt.StationBoardCall('MHIDE')
  assert query is not None
  assert len(lines) == 1
  assert lines[0].origin_code == '???'
  assert lines[0].destination_code == '???'


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_HandleTrainStationXMLRow_invalid_order(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test _HandleTrainStationXMLRow with invalid LocationOrder."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  xml_data = (
    b'<ArrayOfObjTrainMovements xmlns="http://api.irishrail.ie/realtime/">'
    b'<objTrainMovements>'
    b'<TrainCode>E108</TrainCode>'
    b'<TrainDate>29 Jun 2025</TrainDate>'
    b'<LocationCode>MHIDE</LocationCode>'
    b'<LocationFullName>Malahide</LocationFullName>'
    b'<LocationOrder>0</LocationOrder>'
    b'<LocationType>O</LocationType>'
    b'<TrainOrigin>Malahide</TrainOrigin>'
    b'<TrainDestination>Greystones</TrainDestination>'
    b'<ScheduledArrival>00:00:00</ScheduledArrival>'
    b'<ScheduledDeparture>09:00:00</ScheduledDeparture>'
    b'<ExpectedArrival>00:00:00</ExpectedArrival>'
    b'<ExpectedDeparture>09:00:00</ExpectedDeparture>'
    b'<Arrival></Arrival>'
    b'<Departure></Departure>'
    b'<AutoArrival></AutoArrival>'
    b'<AutoDepart></AutoDepart>'
    b'<StopType>-</StopType>'
    b'</objTrainMovements>'
    b'</ArrayOfObjTrainMovements>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  with pytest.raises(realtime.Error, match='invalid row'):
    rt.TrainDataCall('E108', datetime.date(2025, 6, 29))


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_HandleTrainStationXMLRow_invalid_location_stop_type(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test _HandleTrainStationXMLRow with invalid LocationType/StopType."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  xml_data = (
    b'<ArrayOfObjTrainMovements xmlns="http://api.irishrail.ie/realtime/">'
    b'<objTrainMovements>'
    b'<TrainCode>E108</TrainCode>'
    b'<TrainDate>29 Jun 2025</TrainDate>'
    b'<LocationCode>MHIDE</LocationCode>'
    b'<LocationFullName>Malahide</LocationFullName>'
    b'<LocationOrder>1</LocationOrder>'
    b'<LocationType>Z</LocationType>'
    b'<TrainOrigin>Malahide</TrainOrigin>'
    b'<TrainDestination>Greystones</TrainDestination>'
    b'<ScheduledArrival>00:00:00</ScheduledArrival>'
    b'<ScheduledDeparture>09:00:00</ScheduledDeparture>'
    b'<ExpectedArrival>00:00:00</ExpectedArrival>'
    b'<ExpectedDeparture>09:00:00</ExpectedDeparture>'
    b'<Arrival></Arrival>'
    b'<Departure></Departure>'
    b'<AutoArrival></AutoArrival>'
    b'<AutoDepart></AutoDepart>'
    b'<StopType>-</StopType>'
    b'</objTrainMovements>'
    b'</ArrayOfObjTrainMovements>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  with pytest.raises(realtime.Error, match='invalid LocationType'):
    rt.TrainDataCall('E108', datetime.date(2025, 6, 29))


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_HandleTrainStationXMLRow_unknown_origin_dest(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test _HandleTrainStationXMLRow with unknown origin/destination."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  xml_data = (
    b'<ArrayOfObjTrainMovements xmlns="http://api.irishrail.ie/realtime/">'
    b'<objTrainMovements>'
    b'<TrainCode>E108</TrainCode>'
    b'<TrainDate>29 Jun 2025</TrainDate>'
    b'<LocationCode>MHIDE</LocationCode>'
    b'<LocationFullName>Malahide</LocationFullName>'
    b'<LocationOrder>1</LocationOrder>'
    b'<LocationType>O</LocationType>'
    b'<TrainOrigin>UNKNOWN_ORIGIN_XYZ</TrainOrigin>'
    b'<TrainDestination>UNKNOWN_DEST_XYZ</TrainDestination>'
    b'<ScheduledArrival>00:00:00</ScheduledArrival>'
    b'<ScheduledDeparture>09:00:00</ScheduledDeparture>'
    b'<ExpectedArrival>00:00:00</ExpectedArrival>'
    b'<ExpectedDeparture>09:00:00</ExpectedDeparture>'
    b'<Arrival></Arrival>'
    b'<Departure></Departure>'
    b'<AutoArrival></AutoArrival>'
    b'<AutoDepart></AutoDepart>'
    b'<StopType>-</StopType>'
    b'</objTrainMovements>'
    b'</ArrayOfObjTrainMovements>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  query, stops = rt.TrainDataCall('E108', datetime.date(2025, 6, 29))
  assert query is not None
  assert stops[0].query.origin_code == '???' and stops[0].query.destination_code == '???'


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_StationBoardCall_query_mismatch(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test StationBoardCall with mismatched query data across rows."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  # Two rows with different Stationfullname (query data mismatch)
  xml_data = (
    b'<ArrayOfObjStationData xmlns="http://api.irishrail.ie/realtime/">'
    b'<objStationData>'
    b'<Servertime>2025-06-29T09:14:27.863</Servertime>'
    b'<Traincode>E108</Traincode>'
    b'<Stationfullname>StationA</Stationfullname>'
    b'<Stationcode>MHIDE</Stationcode>'
    b'<Querytime>09:14:27</Querytime>'
    b'<Traindate>29 Jun 2025</Traindate>'
    b'<Origin>Malahide</Origin>'
    b'<Destination>Greystones</Destination>'
    b'<Origintime>09:00</Origintime>'
    b'<Destinationtime>10:00</Destinationtime>'
    b'<Status>En Route</Status>'
    b'<Lastlocation>Departed</Lastlocation>'
    b'<Duein>5</Duein>'
    b'<Late>0</Late>'
    b'<Exparrival>09:10</Exparrival>'
    b'<Expdepart>09:12</Expdepart>'
    b'<Scharrival>09:10</Scharrival>'
    b'<Schdepart>09:12</Schdepart>'
    b'<Direction>Southbound</Direction>'
    b'<Traintype>DART</Traintype>'
    b'<Locationtype>S</Locationtype>'
    b'</objStationData>'
    b'<objStationData>'
    b'<Servertime>2025-06-29T09:14:27.863</Servertime>'
    b'<Traincode>E109</Traincode>'
    b'<Stationfullname>StationB</Stationfullname>'
    b'<Stationcode>MHIDE</Stationcode>'
    b'<Querytime>09:14:27</Querytime>'
    b'<Traindate>29 Jun 2025</Traindate>'
    b'<Origin>Malahide</Origin>'
    b'<Destination>Greystones</Destination>'
    b'<Origintime>09:00</Origintime>'
    b'<Destinationtime>10:00</Destinationtime>'
    b'<Status>En Route</Status>'
    b'<Lastlocation>Departed</Lastlocation>'
    b'<Duein>10</Duein>'
    b'<Late>0</Late>'
    b'<Exparrival>09:15</Exparrival>'
    b'<Expdepart>09:17</Expdepart>'
    b'<Scharrival>09:15</Scharrival>'
    b'<Schdepart>09:17</Schdepart>'
    b'<Direction>Southbound</Direction>'
    b'<Traintype>DART</Traintype>'
    b'<Locationtype>S</Locationtype>'
    b'</objStationData>'
    b'</ArrayOfObjStationData>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  with pytest.raises(realtime.Error, match='field should match'):
    rt.StationBoardCall('MHIDE')


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_TrainDataCall_query_mismatch(mock_open: mock.MagicMock, mock_time: mock.MagicMock) -> None:
  """Test TrainDataCall with mismatched query data across rows."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  xml_data = (
    b'<ArrayOfObjTrainMovements xmlns="http://api.irishrail.ie/realtime/">'
    b'<objTrainMovements>'
    b'<TrainCode>E108</TrainCode>'
    b'<TrainDate>29 Jun 2025</TrainDate>'
    b'<LocationCode>MHIDE</LocationCode>'
    b'<LocationFullName>Malahide</LocationFullName>'
    b'<LocationOrder>1</LocationOrder>'
    b'<LocationType>O</LocationType>'
    b'<TrainOrigin>Malahide</TrainOrigin>'
    b'<TrainDestination>Greystones</TrainDestination>'
    b'<ScheduledArrival>00:00:00</ScheduledArrival>'
    b'<ScheduledDeparture>09:00:00</ScheduledDeparture>'
    b'<ExpectedArrival>00:00:00</ExpectedArrival>'
    b'<ExpectedDeparture>09:00:00</ExpectedDeparture>'
    b'<Arrival></Arrival>'
    b'<Departure></Departure>'
    b'<AutoArrival></AutoArrival>'
    b'<AutoDepart></AutoDepart>'
    b'<StopType>-</StopType>'
    b'</objTrainMovements>'
    b'<objTrainMovements>'
    b'<TrainCode>E108</TrainCode>'
    b'<TrainDate>29 Jun 2025</TrainDate>'
    b'<LocationCode>CENTJ</LocationCode>'
    b'<LocationFullName>Central Junction</LocationFullName>'
    b'<LocationOrder>2</LocationOrder>'
    b'<LocationType>S</LocationType>'
    b'<TrainOrigin>DIFFERENT_ORIGIN</TrainOrigin>'
    b'<TrainDestination>Greystones</TrainDestination>'
    b'<ScheduledArrival>09:10:00</ScheduledArrival>'
    b'<ScheduledDeparture>09:12:00</ScheduledDeparture>'
    b'<ExpectedArrival>09:10:00</ExpectedArrival>'
    b'<ExpectedDeparture>09:12:00</ExpectedDeparture>'
    b'<Arrival></Arrival>'
    b'<Departure></Departure>'
    b'<AutoArrival></AutoArrival>'
    b'<AutoDepart></AutoDepart>'
    b'<StopType>-</StopType>'
    b'</objTrainMovements>'
    b'</ArrayOfObjTrainMovements>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  with pytest.raises(realtime.Error, match='field should match'):
    rt.TrainDataCall('E108', datetime.date(2025, 6, 29))


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_TrainDataCall_missing_stop_sequence(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test TrainDataCall with non-contiguous stop sequence numbers."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  rt.StationsCall()
  # Two stops with order 1 and 3 (missing 2)
  xml_data = (
    b'<ArrayOfObjTrainMovements xmlns="http://api.irishrail.ie/realtime/">'
    b'<objTrainMovements>'
    b'<TrainCode>E108</TrainCode>'
    b'<TrainDate>29 Jun 2025</TrainDate>'
    b'<LocationCode>MHIDE</LocationCode>'
    b'<LocationFullName>Malahide</LocationFullName>'
    b'<LocationOrder>1</LocationOrder>'
    b'<LocationType>O</LocationType>'
    b'<TrainOrigin>Malahide</TrainOrigin>'
    b'<TrainDestination>Greystones</TrainDestination>'
    b'<ScheduledArrival>00:00:00</ScheduledArrival>'
    b'<ScheduledDeparture>09:00:00</ScheduledDeparture>'
    b'<ExpectedArrival>00:00:00</ExpectedArrival>'
    b'<ExpectedDeparture>09:00:00</ExpectedDeparture>'
    b'<Arrival></Arrival>'
    b'<Departure></Departure>'
    b'<AutoArrival></AutoArrival>'
    b'<AutoDepart></AutoDepart>'
    b'<StopType>-</StopType>'
    b'</objTrainMovements>'
    b'<objTrainMovements>'
    b'<TrainCode>E108</TrainCode>'
    b'<TrainDate>29 Jun 2025</TrainDate>'
    b'<LocationCode>CENTJ</LocationCode>'
    b'<LocationFullName>Central Junction</LocationFullName>'
    b'<LocationOrder>3</LocationOrder>'
    b'<LocationType>D</LocationType>'
    b'<TrainOrigin>Malahide</TrainOrigin>'
    b'<TrainDestination>Greystones</TrainDestination>'
    b'<ScheduledArrival>09:30:00</ScheduledArrival>'
    b'<ScheduledDeparture>00:00:00</ScheduledDeparture>'
    b'<ExpectedArrival>09:30:00</ExpectedArrival>'
    b'<ExpectedDeparture>00:00:00</ExpectedDeparture>'
    b'<Arrival></Arrival>'
    b'<Departure></Departure>'
    b'<AutoArrival></AutoArrival>'
    b'<AutoDepart></AutoDepart>'
    b'<StopType>-</StopType>'
    b'</objTrainMovements>'
    b'</ArrayOfObjTrainMovements>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  with pytest.raises(realtime.Error, match='missing stop'):
    rt.TrainDataCall('E108', datetime.date(2025, 6, 29))


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_CallRPC_repeated_elements(mock_open: mock.MagicMock, mock_time: mock.MagicMock) -> None:
  """Test _CallRPC with repeated XML elements in a row."""
  mock_time.return_value = realtime_data.RT_TIME
  xml_data = (
    b'<ArrayOfObjStation xmlns="http://api.irishrail.ie/realtime/">'
    b'<objStation>'
    b'<StationId>1</StationId>'
    b'<StationId>2</StationId>'
    b'<StationCode>TEST</StationCode>'
    b'<StationDesc>Test</StationDesc>'
    b'<StationLatitude>0.0</StationLatitude>'
    b'<StationLongitude>0.0</StationLongitude>'
    b'<StationAlias></StationAlias>'
    b'</objStation>'
    b'</ArrayOfObjStation>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  rt = realtime.RealtimeRail()
  with pytest.raises(realtime.ParseError, match='repeated elements'):
    rt.StationsCall()


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_CallRPC_empty_required_field(mock_open: mock.MagicMock, mock_time: mock.MagicMock) -> None:
  """Test _CallRPC with empty required field."""
  mock_time.return_value = realtime_data.RT_TIME
  xml_data = (
    b'<ArrayOfObjStation xmlns="http://api.irishrail.ie/realtime/">'
    b'<objStation>'
    b'<StationId></StationId>'
    b'<StationCode>TEST</StationCode>'
    b'<StationDesc>Test</StationDesc>'
    b'<StationLatitude>0.0</StationLatitude>'
    b'<StationLongitude>0.0</StationLongitude>'
    b'<StationAlias></StationAlias>'
    b'</objStation>'
    b'</ArrayOfObjStation>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  rt = realtime.RealtimeRail()
  with pytest.raises(realtime.ParseError, match='empty required field'):
    rt.StationsCall()


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_CallRPC_invalid_int_value(mock_open: mock.MagicMock, mock_time: mock.MagicMock) -> None:
  """Test _CallRPC with invalid int value."""
  mock_time.return_value = realtime_data.RT_TIME
  xml_data = (
    b'<ArrayOfObjStation xmlns="http://api.irishrail.ie/realtime/">'
    b'<objStation>'
    b'<StationId>NOT_AN_INT</StationId>'
    b'<StationCode>TEST</StationCode>'
    b'<StationDesc>Test</StationDesc>'
    b'<StationLatitude>0.0</StationLatitude>'
    b'<StationLongitude>0.0</StationLongitude>'
    b'<StationAlias></StationAlias>'
    b'</objStation>'
    b'</ArrayOfObjStation>'
  )
  mock_open.return_value = util.FakeHTTPStream(xml_data)
  rt = realtime.RealtimeRail()
  with pytest.raises(realtime.ParseError, match='invalid int/float value'):
    rt.StationsCall()


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_PrettyPrintStation_lazy_stations(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test PrettyPrintStation lazy loads stations when not yet loaded."""
  mock_time.return_value = realtime_data.RT_TIME
  rt = realtime.RealtimeRail()
  # Directly populate station_boards with the expected data (from realtime_data.py)
  rt._latest.station_boards['MHIDE'] = realtime_data.STATION_OBJ.station_boards['MHIDE']
  # Clear stations to force lazy load in PrettyPrintStation
  rt._latest.stations = {}
  rt._latest.stations_tm = None
  mock_open.side_effect = [util.FakeHTTPFile(TEST_XMLS['stations'])]
  # This should trigger the lazy load of stations (line 814)
  output = list(rt.PrettyPrintStation(station_code='MHIDE'))
  assert len(output) > 0


# realtime_data_model.py comparison tests


def test_StationLineQueryData_lt() -> None:
  """Test StationLineQueryData __lt__ branches."""
  q1 = dm.StationLineQueryData(
    tm_server=datetime.datetime(2025, 1, 1, 0, 0, 0),  # noqa: DTZ001
    tm_query=base.DayTime(time=0),
    station_name='Alpha',
    station_code='A',
    day=datetime.date(2025, 1, 1),
  )
  q2 = dm.StationLineQueryData(
    tm_server=datetime.datetime(2025, 1, 1, 0, 0, 0),  # noqa: DTZ001
    tm_query=base.DayTime(time=0),
    station_name='Beta',
    station_code='B',
    day=datetime.date(2025, 1, 1),
  )
  # different station_name
  assert q1 < q2
  # same station_name, different tm_server
  q3 = dm.StationLineQueryData(
    tm_server=datetime.datetime(2025, 1, 1, 0, 0, 0),  # noqa: DTZ001
    tm_query=base.DayTime(time=0),
    station_name='Alpha',
    station_code='A',
    day=datetime.date(2025, 1, 1),
  )
  q4 = dm.StationLineQueryData(
    tm_server=datetime.datetime(2025, 1, 2, 0, 0, 0),  # noqa: DTZ001
    tm_query=base.DayTime(time=0),
    station_name='Alpha',
    station_code='A',
    day=datetime.date(2025, 1, 1),
  )
  assert q3 < q4


def test_StationLine_lt() -> None:
  """Test StationLine __lt__ branches."""
  query = dm.StationLineQueryData(
    tm_server=datetime.datetime(2025, 1, 1, 0, 0, 0),  # noqa: DTZ001
    tm_query=base.DayTime(time=0),
    station_name='Test',
    station_code='T',
    day=datetime.date(2025, 1, 1),
  )
  trip = base.DayRange(arrival=base.DayTime(time=100), departure=base.DayTime(time=200))
  base_kwargs: dict[str, object] = {
    'query': query,
    'train_code': 'E1',
    'origin_code': 'A',
    'origin_name': 'A',
    'destination_code': 'B',
    'destination_name': 'Beta',
    'trip': trip,
    'direction': 'S',
    'late': 0,
    'location_type': dm.LocationType.STOP,
    'status': None,
    'scheduled': base.DayRange(arrival=base.DayTime(time=0), departure=base.DayTime(time=0)),
    'expected': base.DayRange(arrival=base.DayTime(time=0), departure=base.DayTime(time=0)),
  }
  # Different due_in
  l1 = dm.StationLine(due_in=base.DayTime(time=5), **base_kwargs)  # type: ignore
  l2 = dm.StationLine(due_in=base.DayTime(time=10), **base_kwargs)  # type: ignore
  assert l1 < l2
  # Same due_in, different expected
  kw_same_due = {**base_kwargs, 'due_in': base.DayTime(time=5)}
  exp1 = base.DayRange(arrival=base.DayTime(time=100), departure=base.DayTime(time=200))
  exp2 = base.DayRange(arrival=base.DayTime(time=300), departure=base.DayTime(time=400))
  l3 = dm.StationLine(expected=exp1, **{k: v for k, v in kw_same_due.items() if k != 'expected'})  # type: ignore
  l4 = dm.StationLine(expected=exp2, **{k: v for k, v in kw_same_due.items() if k != 'expected'})  # type: ignore
  assert l3 < l4
  # Same due_in, same expected, different destination_name
  kw_same_all = {**base_kwargs, 'due_in': base.DayTime(time=5)}
  l5 = dm.StationLine(**{**kw_same_all, 'destination_name': 'Alpha'})  # type: ignore
  l6 = dm.StationLine(**{**kw_same_all, 'destination_name': 'Zeta'})  # type: ignore
  assert l5 < l6


def test_TrainStopQueryData_lt() -> None:
  """Test TrainStopQueryData __lt__ branches."""
  # different origin_name
  q1 = dm.TrainStopQueryData(
    train_code='E1',
    day=datetime.date(2025, 1, 1),
    origin_code='A',
    origin_name='Alpha',
    destination_code='B',
    destination_name='Beta',
  )
  q2 = dm.TrainStopQueryData(
    train_code='E1',
    day=datetime.date(2025, 1, 1),
    origin_code='A',
    origin_name='Zeta',
    destination_code='B',
    destination_name='Beta',
  )
  assert q1 < q2
  # same origin_name, different destination_name
  q3 = dm.TrainStopQueryData(
    train_code='E1',
    day=datetime.date(2025, 1, 1),
    origin_code='A',
    origin_name='Alpha',
    destination_code='B',
    destination_name='Alpha',
  )
  q4 = dm.TrainStopQueryData(
    train_code='E1',
    day=datetime.date(2025, 1, 1),
    origin_code='A',
    origin_name='Alpha',
    destination_code='B',
    destination_name='Zeta',
  )
  assert q3 < q4
  # same origin_name, same destination_name, different train_code
  q5 = dm.TrainStopQueryData(
    train_code='A1',
    day=datetime.date(2025, 1, 1),
    origin_code='A',
    origin_name='Alpha',
    destination_code='B',
    destination_name='Beta',
  )
  q6 = dm.TrainStopQueryData(
    train_code='Z1',
    day=datetime.date(2025, 1, 1),
    origin_code='A',
    origin_name='Alpha',
    destination_code='B',
    destination_name='Beta',
  )
  assert q5 < q6


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_StationCodeFromNameFragmentOrCode_ambiguous(
  mock_open: mock.MagicMock, mock_time: mock.MagicMock
) -> None:
  """Test StationCodeFromNameFragmentOrCode with ambiguous match."""
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  rt = realtime.RealtimeRail()
  # 'Malahide' is a station name. If we search for a fragment in lowercase
  # that matches multiple stations, it should raise ambiguous error.
  # 'la' appears in both 'Malahide' and 'Claremorris' etc.
  # We need to pre-populate stations with multiple matches.
  rt._latest.stations = {
    'AAA': dm.Station(id=1, code='AAA', description='Dublin Alpha', alias=None),
    'BBB': dm.Station(id=2, code='BBB', description='Dublin Beta', alias=None),
  }
  with pytest.raises(realtime.Error, match='ambiguous'):
    rt.StationCodeFromNameFragmentOrCode('dublin')


@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_CallRPC_invalid_bool_value(mock_open: mock.MagicMock, mock_time: mock.MagicMock) -> None:
  """Test _CallRPC with invalid boolean value in XML."""
  mock_time.return_value = realtime_data.RT_TIME
  # Create XML with an invalid bool value for 'Locationfullname' which is actually string,
  # We need to find a field that is typed as `bool` in the stations schema.
  # Looking at the handler definition, stations handler uses 'StationId' (int),
  # 'StationAlias' (str|None), 'StationDesc' (str), etc. No bool fields in stations.
  # Let me check which RPC has bool fields...
  # running_trains has Direction (str), but let me check the TypedDicts.
  # Actually, stop_times has 'timepoint' as bool. But that's GTFS, not realtime.
  # Realtime station_board uses 'Stationfullname' (str), 'Traincode' (str) etc.
  # Let me just monkey-patch the field type to make a field be bool.
  rt = realtime.RealtimeRail()
  # Directly modify the row_types for 'stations' to include a bool field
  _, _, _, row_types, _ = rt._file_handlers['stations']
  # Change 'StationDesc' from (str, True) to (bool, True) temporarily
  original: tuple[type, bool] = row_types['StationDesc']
  row_types['StationDesc'] = (bool, True)
  mock_open.return_value = util.FakeHTTPFile(TEST_XMLS['stations'])
  with pytest.raises(realtime.ParseError, match='invalid bool value'):
    rt.StationsCall()
  row_types['StationDesc'] = original


def test_main_realtime_invalid_date() -> None:
  """Test Main callback with invalid _TODAY_INT for realtime."""
  original: int = realtime._TODAY_INT
  try:
    realtime._TODAY_INT = 19000101
    # Call Main directly (not via CliRunner) so coverage tracks the line.
    # CLIErrorGuard catches the Error internally.
    mock_ctx = mock.MagicMock()
    mock_ctx.obj = None
    realtime.Main(ctx=mock_ctx, version=False, verbose=0, color=None)
    # CLIErrorGuard catches the Error, so we get here. But ctx.obj is not set.
  finally:
    realtime._TODAY_INT = original


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_Markdown_realtime_body(_rt: mock.MagicMock) -> None:  # noqa: PT019
  """Test realtime Markdown by directly calling it to cover body line."""
  mock_ctx = mock.MagicMock()
  mock_ctx.obj = realtime.RealtimeConfig(
    console=mock.MagicMock(),
    verbose=0,
    color=True,
  )
  realtime.Markdown(ctx=mock_ctx)
  mock_ctx.obj.console.print.assert_called_once()
