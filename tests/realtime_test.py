# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""realtime.py unittest."""

from __future__ import annotations

import datetime
import os.path
from collections.abc import Callable, Generator
from typing import Self
from unittest import mock

import pytest
from click import testing as click_testing
from src.tfinta import realtime
from src.tfinta import realtime_data_model as dm
from transcrypto.utils import logging as tc_logging
from typer import testing as typer_testing

from . import realtime_data, util

_REALTIME_DIR: str = os.path.join(util.DATA_DIR, 'realtime')

TEST_XMLS: dict[str, str] = {
  'stations': os.path.join(_REALTIME_DIR, 'getAllStations.xml'),
  'running': os.path.join(_REALTIME_DIR, 'getCurrentTrains.xml'),
  'station': os.path.join(_REALTIME_DIR, 'getStationDataByCode.xml'),
  'train': os.path.join(_REALTIME_DIR, 'getTrainMovements.xml'),
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
    """Test date."""
    return cls(2025, 6, 29)


@pytest.mark.parametrize(
  'call_names, call_obj, expected_obj, expected_str',
  [
    (
      [
        ('stations', {}),
      ],
      realtime.RealtimeRail.PrettyPrintStations,
      realtime_data.STATIONS_OBJ,
      realtime_data.STATIONS_STR,
    ),
    (
      [
        ('running', {}),
      ],
      realtime.RealtimeRail.PrettyPrintRunning,
      realtime_data.RUNNING_OBJ,
      realtime_data.RUNNING_STR,
    ),
    (
      [
        ('station', {'station_code': 'MHIDE'}),
        ('stations', {}),
      ],
      realtime.RealtimeRail.PrettyPrintStation,
      realtime_data.STATION_OBJ,
      realtime_data.STATION_STR,
    ),
    (
      [
        ('train', {'train_code': 'E108', 'day': datetime.date(2025, 6, 29)}),
        ('stations', {}),
      ],
      realtime.RealtimeRail.PrettyPrintTrain,
      realtime_data.TRAIN_OBJ,
      realtime_data.TRAIN_STR,
    ),
  ],
)
@mock.patch('src.tfinta.realtime.time.time', autospec=True)
@mock.patch('src.tfinta.realtime.urllib.request.urlopen', autospec=True)
def test_RealtimeRail_StationsCall(
  mock_open: mock.MagicMock,
  mock_time: mock.MagicMock,
  call_names: list[tuple[str, realtime._PossibleRPCArgs]],
  call_obj: Callable[..., Generator[str, None, None]],
  expected_obj: dm.LatestData,
  expected_str: str,
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """Test."""
  monkeypatch.setattr(realtime.datetime, 'date', _FakeDate)
  mock_time.return_value = realtime_data.RT_TIME
  mock_open.side_effect = [util.FakeHTTPFile(TEST_XMLS[c]) for c, _ in call_names]
  # call
  rt = realtime.RealtimeRail()
  return_str: str = '\n'.join(call_obj(rt, **call_names[0][1]))
  # check data
  assert rt._latest == expected_obj
  assert return_str == expected_str
  assert mock_open.call_args_list == [
    mock.call(realtime._RPC_CALLS[c](**p), timeout=10.0) for c, p in call_names
  ]


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
    realtime.app, ['print', 'station', '-c', 'malahide']
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
    realtime.app, ['print', 'train', '-c', 'E108', '-d', '20250701']
  )
  assert result.exit_code == 0
  mock_realtime.assert_called_once_with()
  db_obj.PrettyPrintTrain.assert_called_once_with(train_code='E108', day=datetime.date(2025, 7, 1))
