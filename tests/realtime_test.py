#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
# pyright: reportPrivateUsage=false
"""realtime.py unittest."""

import datetime
import os.path
# import pdb
import sys
from typing import Callable, Generator, Self
from unittest import mock

import pytest

from src.tfinta import tfinta_base as base
from src.tfinta import realtime
from src.tfinta import realtime_data_model as dm

from . import realtime_data
from . import util

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = realtime.__version__  # tests inherit version from module


_REALTIME_DIR: str = os.path.join(util.DATA_DIR, 'realtime')

TEST_XMLS: dict[str, str] = {
    'stations': os.path.join(_REALTIME_DIR, 'getAllStations.xml'),
    'running': os.path.join(_REALTIME_DIR, 'getCurrentTrains.xml'),
    'station': os.path.join(_REALTIME_DIR, 'getStationDataByCode.xml'),
    'train': os.path.join(_REALTIME_DIR, 'getTrainMovements.xml'),
}


class _FakeDate(datetime.date):
  """Fake datetime.date so we can monkeypatch.setattr(datetime, 'date', FakeDate)."""

  @classmethod
  def today(cls) -> Self:
    """Test date."""
    return cls(2025, 6, 29)


@pytest.mark.parametrize('call_names, call_obj, expected_obj, expected_str', [
    (  # type:ignore
        [
            ('stations', {}),
        ],
        realtime.RealtimeRail.PrettyPrintStations,
        realtime_data.STATIONS_OBJ, realtime_data.STATIONS_STR,
    ),
    (
        [
            ('running', {}),
        ],
        realtime.RealtimeRail.PrettyPrintRunning,
        realtime_data.RUNNING_OBJ, realtime_data.RUNNING_STR,
    ),
    (
        [
            ('station', {'station_code': 'MHIDE'}),
            ('stations', {}),
        ],
        realtime.RealtimeRail.PrettyPrintStation,
        realtime_data.STATION_OBJ, realtime_data.STATION_STR,
    ),
    (
        [
            ('train', {'train_code': 'E108', 'day': datetime.date(2025, 6, 29)}),
            ('stations', {}),
        ],
        realtime.RealtimeRail.PrettyPrintTrain,
        realtime_data.TRAIN_OBJ, realtime_data.TRAIN_STR,
    ),
])
@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_RealtimeRail_StationsCall(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    mock_open: mock.MagicMock, mock_time: mock.MagicMock,
    call_names: list[tuple[str, realtime._PossibleRPCArgs]],
    call_obj: Callable[..., Generator[str, None, None]],
    expected_obj: dm.LatestData, expected_str: str,
    monkeypatch: pytest.MonkeyPatch) -> None:
  """Test."""
  monkeypatch.setattr(realtime.datetime, 'date', _FakeDate)
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.side_effect = [util.FakeHTTPFile(TEST_XMLS[c]) for c, _ in call_names]
  # call
  rt = realtime.RealtimeRail()
  return_str: str = '\n'.join(call_obj(rt, **call_names[0][1]))
  # check data
  assert rt._latest == expected_obj
  assert base.STRIP_ANSI(return_str) == expected_str
  assert mock_open.call_args_list == [
      mock.call(realtime.RealtimeRail._RPC_CALLS[c](**p), timeout=10.0) for c, p in call_names]


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_main_print_stations(mock_realtime: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_realtime.return_value = db_obj
  db_obj.PrettyPrintStations.return_value = ['foo', 'bar']
  assert realtime.main(['print', 'stations']) == 0
  mock_realtime.assert_called_once_with()
  db_obj.PrettyPrintStations.assert_called_once_with()


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_main_print_running(mock_realtime: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_realtime.return_value = db_obj
  db_obj.PrettyPrintRunning.return_value = ['foo', 'bar']
  assert realtime.main(['print', 'running']) == 0
  mock_realtime.assert_called_once_with()
  db_obj.PrettyPrintRunning.assert_called_once_with()


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_main_print_station(mock_realtime: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_realtime.return_value = db_obj
  db_obj.StationCodeFromNameFragmentOrCode.return_value = 'MHIDE'
  db_obj.PrettyPrintStation.return_value = ['foo', 'bar']
  assert realtime.main(['print', 'station', '-c', 'malahide']) == 0
  mock_realtime.assert_called_once_with()
  db_obj.StationCodeFromNameFragmentOrCode.assert_called_once_with('malahide')
  db_obj.PrettyPrintStation.assert_called_once_with(station_code='MHIDE')


@mock.patch('src.tfinta.realtime.RealtimeRail', autospec=True)
def test_main_print_train(mock_realtime: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_realtime.return_value = db_obj
  db_obj.PrettyPrintTrain.return_value = ['foo', 'bar']
  assert realtime.main(['print', 'train', '-c', 'E108', '-d', '20250701']) == 0
  mock_realtime.assert_called_once_with()
  db_obj.PrettyPrintTrain.assert_called_once_with(train_code='E108', day=datetime.date(2025, 7, 1))


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
