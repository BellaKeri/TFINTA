#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
# pyright: reportPrivateUsage=false
"""dart.py unittest."""

import datetime
# import pdb
import sys
from typing import Generator
from unittest import mock

import pytest

from src.tfinta import dart
from src.tfinta import gtfs
# from src.tfinta import gtfs_data_model as dm

from . import gtfs_data


__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 2)


@pytest.fixture
def gtfs_object() -> Generator[gtfs.GTFS, None, None]:
  """A GTFS object with all gtfs_data.ZIP_DB_1 data loaded."""
  # create object with all the disk features disabled
  db: gtfs.GTFS
  with (mock.patch('src.tfinta.gtfs.time.time', autospec=True) as time,
        mock.patch('src.tfinta.gtfs.os.path.isdir', autospec=True) as is_dir,
        mock.patch('src.tfinta.gtfs.os.mkdir', autospec=True),
        mock.patch('src.tfinta.gtfs.os.path.exists', autospec=True) as exists,
        mock.patch('balparda_baselib.base.BinSerialize', autospec=True),
        mock.patch('balparda_baselib.base.BinDeSerialize', autospec=True)):
    time.return_value = gtfs_data.ZIP_DB_1_TM
    is_dir.return_value = False
    exists.return_value = False
    db = gtfs.GTFS('db/path')
  # monkey-patch the data into the object
  db._db = gtfs_data.ZIP_DB_1
  yield db


def test_DART(gtfs_object: gtfs.GTFS) -> None:  # pylint: disable=redefined-outer-name
  """Test."""
  with pytest.raises(gtfs.Error):
    dart.DART(None)  # type: ignore
  db = dart.DART(gtfs_object)
  assert db.Services() == {83, 84}
  assert db.ServicesForDay(datetime.date(2025, 8, 4)) == {84}
  assert db.ServicesForDay(datetime.date(2025, 6, 22)) == {83}
  assert db.ServicesForDay(datetime.date(2025, 6, 23)) == set()
  assert db._dart_trips == gtfs_data.DART_TRIPS_ZIP_1
  with pytest.raises(gtfs.Error):
    list(db.PrettyDaySchedule(None))  # type: ignore
  assert '\n'.join(db.PrettyDaySchedule(datetime.date(2025, 8, 4))) == (
      gtfs_data.TRIPS_SCHEDULE_2025_08_04)
  with pytest.raises(gtfs.Error):
    list(db.PrettyStationSchedule(' \t', datetime.date(2025, 8, 4)))  # type: ignore
  assert '\n'.join(db.PrettyStationSchedule('8350IR0123', datetime.date(2025, 8, 4))) == (
      gtfs_data.STATION_SCHEDULE_2025_08_04)


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_load(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  assert dart.main(['read']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_called_once_with(
      'Iarnród Éireann / Irish Rail',
      'https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip',
      freshness=10, allow_unknown_file=True, allow_unknown_field=False,
      force_replace=False, override=None)
  mock_dart.assert_not_called()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_print_trips(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj, dart_obj = mock.MagicMock(), mock.MagicMock()
  mock_gtfs.return_value = db_obj
  mock_dart.return_value = dart_obj
  dart_obj.PrettyDaySchedule.return_value = ['foo', 'bar']
  assert dart.main(['print', 'trips', '-d', '20250804']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  mock_dart.assert_called_once_with(db_obj)
  dart_obj.PrettyDaySchedule.assert_called_once_with(datetime.date(2025, 8, 4))
  dart_obj.PrettyStationSchedule.assert_not_called()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_print_station(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj, dart_obj = mock.MagicMock(), mock.MagicMock()
  mock_gtfs.return_value = db_obj
  mock_dart.return_value = dart_obj
  db_obj.StopIDFromNameFragmentOrID.return_value = 'bray'
  dart_obj.PrettyStationSchedule.return_value = ['foo', 'bar']
  assert dart.main(['print', 'station', '-s', 'daly', '-d', '20250804']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  db_obj.StopIDFromNameFragmentOrID.assert_called_once_with('daly')
  mock_dart.assert_called_once_with(db_obj)
  dart_obj.PrettyStationSchedule.assert_called_once_with('bray', datetime.date(2025, 8, 4))
  dart_obj.PrettyDaySchedule.assert_not_called()


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
