# SPDX-FileCopyrightText: 2026 BellaKeri (BellaKeri@github.com) & D. Balparda <balparda@github.com>
# SPDX-License-Identifier: Apache-2.0
"""dart.py unittest."""

from __future__ import annotations

import datetime

# import pdb
import sys
from unittest import mock

import pytest
import typeguard
from src.tfinta import dart, gtfs

# from src.tfinta import gtfs_data_model as dm
from . import gtfs_data

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = dart.__version__  # tests inherit version from module


@pytest.fixture
def gtfs_object() -> gtfs.GTFS:
  """A GTFS object with all gtfs_data.ZIP_DB_1 data loaded."""
  # create object with all the disk features disabled
  db: gtfs.GTFS
  with (
    mock.patch('src.tfinta.gtfs.time.time', autospec=True) as time,
    mock.patch('src.tfinta.gtfs.os.path.isdir', autospec=True) as is_dir,
    mock.patch('src.tfinta.gtfs.os.mkdir', autospec=True),
    mock.patch('src.tfinta.gtfs.os.path.exists', autospec=True) as exists,
    mock.patch('src.tfinta.tfinta_base.BinSerialize', autospec=True),
    mock.patch('src.tfinta.tfinta_base.BinDeSerialize', autospec=True),
  ):
    time.return_value = gtfs_data.ZIP_DB_1_TM
    is_dir.return_value = False
    exists.return_value = False
    db = gtfs.GTFS('db/path')
  # monkey-patch the data into the object
  db._db = gtfs_data.ZIP_DB_1
  return db


def test_DART(gtfs_object: gtfs.GTFS) -> None:  # pylint: disable=redefined-outer-name
  """Test."""
  with typeguard.suppress_type_checks():
    with pytest.raises(gtfs.Error):
      dart.DART(None)  # type: ignore
    db = dart.DART(gtfs_object)
  assert db.Services() == {83, 84}
  assert db.ServicesForDay(datetime.date(2025, 8, 4)) == {84}
  assert db.ServicesForDay(datetime.date(2025, 6, 22)) == {83}
  assert db.ServicesForDay(datetime.date(2025, 6, 23)) == set()
  print(db._dart_trips)
  assert db._dart_trips == gtfs_data.DART_TRIPS_ZIP_1
  with pytest.raises(gtfs.Error), typeguard.suppress_type_checks():
    list(db.PrettyDaySchedule(day=None))  # type: ignore
  assert (
    gtfs.base.STRIP_ANSI('\n'.join(db.PrettyDaySchedule(day=datetime.date(2025, 8, 4))))
    == gtfs_data.TRIPS_SCHEDULE_2025_08_04
  )
  with pytest.raises(gtfs.Error):
    list(db.PrettyStationSchedule(stop_id=' \t', day=datetime.date(2025, 8, 4)))
  assert (
    gtfs.base.STRIP_ANSI(
      '\n'.join(db.PrettyStationSchedule(stop_id='8350IR0123', day=datetime.date(2025, 8, 4)))
    )
    == gtfs_data.STATION_SCHEDULE_2025_08_04
  )
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintTrip(trip_name=' \t'))
  assert (
    gtfs.base.STRIP_ANSI('\n'.join(db.PrettyPrintTrip(trip_name='E818'))) == gtfs_data.TRIP_E818
  )
  assert gtfs.base.STRIP_ANSI('\n'.join(db.PrettyPrintAllDatabase())) == gtfs_data.ALL_DATA


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
    freshness=10,
    allow_unknown_file=True,
    allow_unknown_field=False,
    force_replace=False,
    override=None,
  )
  mock_dart.assert_not_called()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_print_calendars(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj, dart_obj = mock.MagicMock(), mock.MagicMock()
  mock_gtfs.return_value = db_obj
  mock_dart.return_value = dart_obj
  dart_obj.PrettyPrintCalendar.return_value = ['foo', 'bar']
  assert dart.main(['print', 'calendars']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  mock_dart.assert_called_once_with(db_obj)
  dart_obj.PrettyPrintCalendar.assert_called_once_with()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_print_stops(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj, dart_obj = mock.MagicMock(), mock.MagicMock()
  mock_gtfs.return_value = db_obj
  mock_dart.return_value = dart_obj
  dart_obj.PrettyPrintStops.return_value = ['foo', 'bar']
  assert dart.main(['print', 'stops']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  mock_dart.assert_called_once_with(db_obj)
  dart_obj.PrettyPrintStops.assert_called_once_with()


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
  dart_obj.PrettyDaySchedule.assert_called_once_with(day=datetime.date(2025, 8, 4))


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
  dart_obj.PrettyStationSchedule.assert_called_once_with(
    stop_id='bray', day=datetime.date(2025, 8, 4)
  )


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_print_trip(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj, dart_obj = mock.MagicMock(), mock.MagicMock()
  mock_gtfs.return_value = db_obj
  mock_dart.return_value = dart_obj
  dart_obj.PrettyStationSchedule.return_value = ['foo', 'bar']
  assert dart.main(['print', 'trip', '-c', 'E108']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  mock_dart.assert_called_once_with(db_obj)
  dart_obj.PrettyPrintTrip.assert_called_once_with(trip_name='E108')


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_print_all(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj, dart_obj = mock.MagicMock(), mock.MagicMock()
  mock_gtfs.return_value = db_obj
  mock_dart.return_value = dart_obj
  dart_obj.PrettyStationSchedule.return_value = ['foo', 'bar']
  assert dart.main(['print', 'all']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  mock_dart.assert_called_once_with(db_obj)
  dart_obj.PrettyPrintAllDatabase.assert_called_once_with()


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
