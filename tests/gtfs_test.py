# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""gtfs.py unittest."""

from __future__ import annotations

import datetime
import os.path
import pathlib
from unittest import mock

import pytest
import typeguard
from src.tfinta import gtfs
from src.tfinta import gtfs_data_model as dm
from typer import testing as typer_testing

from . import gtfs_data, util

# mock test files
_OPERATOR_CSV_PATH: str = os.path.join(util.DATA_DIR, 'GTFS Operator Files - 20250621.csv')
# the zip directory has a very reduced version of the real data in 202506
_ZIP_DIR_1: str = os.path.join(util.DATA_DIR, 'zip_1')


@mock.patch('src.tfinta.gtfs.time.time', autospec=True)
@mock.patch('src.tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_load_and_parse_from_net(
  deserialize: mock.MagicMock,
  serialize: mock.MagicMock,
  urlopen: mock.MagicMock,
  time: mock.MagicMock,
) -> None:
  """Test."""
  # empty path should raise
  with pytest.raises(gtfs.Error):
    gtfs.GTFS(' \t')  # some extra spaces...
  # mock
  db: gtfs.GTFS
  time.return_value = gtfs_data.ZIP_DB_1_TM
  mock_path = mock.MagicMock()
  mock_path.is_dir.return_value = False
  mock_path.exists.return_value = False
  with mock.patch('src.tfinta.gtfs.pathlib.Path', autospec=True) as path_mock:
    path_mock.return_value = mock_path
    # create database
    db = gtfs.GTFS('\tdb/path ')  # some extra spaces...
    # check creation path
    assert path_mock.call_args_list[0] == mock.call('db/path')
    mock_path.is_dir.assert_called_once()
    mock_path.mkdir.assert_called_once()
    assert path_mock.call_args_list[2] == mock.call('db/path/transit.db')
    mock_path.exists.assert_called_once()
  # load the GTFS data into database: do it BEFORE we mock open()!
  cache_file = mock.mock_open()
  fake_csv = util.FakeHTTPFile(_OPERATOR_CSV_PATH)
  zip_bytes: bytes = gtfs_data.ZipDirBytes(pathlib.Path(_ZIP_DIR_1))
  fake_zip = util.FakeHTTPStream(zip_bytes)
  mock_path_2 = mock.MagicMock()
  mock_path_2.exists.return_value = False
  with mock.patch('src.tfinta.gtfs.pathlib.Path') as path_mock_2:
    path_mock_2.return_value = mock_path_2
    urlopen.side_effect = [fake_csv, fake_zip]
    with typeguard.suppress_type_checks():
      db.LoadData(
        dm.IRISH_RAIL_OPERATOR,
        dm.IRISH_RAIL_LINK,
        allow_unknown_file=True,
        allow_unknown_field=True,
      )
    # Check that the cache path was checked for existence and written
    cache_path_call = mock.call(
      'db/path/https__www.transportforireland.ie_transitData_Data_GTFS_Irish_Rail.zip'
    )
    assert cache_path_call in path_mock_2.call_args_list
    mock_path_2.exists.assert_called()
    mock_path_2.write_bytes.assert_called_once_with(zip_bytes)
    assert urlopen.call_args_list == [
      mock.call('https://www.transportforireland.ie/transitData/Data/GTFS%20Operator%20Files.csv'),
      mock.call('https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip'),
    ]
  # check calls
  deserialize.assert_not_called()
  assert serialize.call_args_list == [mock.call(db._db, file_path='db/path/transit.db')] * 2
  # check DB data
  assert db._db == gtfs_data.ZIP_DB_1
  # check other methods and corner cases for the loaded data
  assert db.FindRoute('none') is None
  assert db.FindTrip('none') == (None, None, None)
  assert db.StopName('none') == (None, None, None)
  assert db.StopName('8250IR0022') == ('0', 'Shankill', None)
  with pytest.raises(gtfs.Error):
    db.StopNameTranslator('none')
  with pytest.raises(gtfs.Error, match='empty station'):
    db.StopIDFromNameFragmentOrID(' \t')
  with pytest.raises(gtfs.Error, match=r'Killiney.*Shankill'):
    db.StopIDFromNameFragmentOrID('kill')
  with pytest.raises(gtfs.Error, match='No matches'):
    db.StopIDFromNameFragmentOrID('invalid')
  assert db.StopIDFromNameFragmentOrID('8350IR0122') == '8350IR0122'
  assert db.StopIDFromNameFragmentOrID('grey') == '8350IR0122'
  assert db.StopIDFromNameFragmentOrID('ceannt') == '8460IR0044'
  assert db.StopNameTranslator('8250IR0022') == 'Shankill'
  assert db.ServicesForDay(datetime.date(2025, 8, 4)) == {84}
  assert db.ServicesForDay(datetime.date(2025, 6, 2)) == set()
  assert db.ServicesForDay(datetime.date(2025, 6, 22)) == {83}
  assert db.ServicesForDay(datetime.date(2025, 6, 23)) == {87}
  assert db.ServicesForDay(datetime.date(2028, 7, 1)) == set()
  assert db.FindAgencyRoute('invalid', dm.RouteType.RAIL, 'none') == (None, None)
  agency, route = db.FindAgencyRoute(dm.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, 'none')
  assert agency and agency.id == 7778017
  assert route is None
  agency, route = db.FindAgencyRoute(
    dm.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, dm.DART_SHORT_NAME, long_name=dm.DART_LONG_NAME
  )
  assert agency and agency.id == 7778017
  agency, route = db.FindAgencyRoute(dm.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, dm.DART_SHORT_NAME)
  assert agency and agency.id == 7778017
  assert route and route.id == '4452_86289'
  # assert '\n'.join(db.PrettyPrintBasics()) == gtfs_data.BASICS
  # with pytest.raises(gtfs.Error):
  #   list(db.PrettyPrintCalendar(filter_to={544356456}))

  # assert '\n'.join(db.PrettyPrintCalendar()) == gtfs_data.CALENDARS
  util.AssertPrettyPrint(gtfs_data.CALENDARS_TABLE, db.PrettyPrintCalendar())

  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintStops(filter_to={'none'}))
  assert '\n'.join(db.PrettyPrintStops()) == gtfs_data.STOPS
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintShape(shape_id='none'))
  assert '\n'.join(db.PrettyPrintShape(shape_id='4669_658')) == gtfs_data.SHAPE_4669_658
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintTrip(trip_id='none'))
  assert '\n'.join(db.PrettyPrintTrip(trip_id='4452_2655')) == gtfs_data.TRIP_4452_2655
  assert '\n'.join(db.PrettyPrintAllDatabase()) == gtfs_data.ALL_TRIPS
  # check corner cases for handlers
  # feed_info.txt
  loc = gtfs._TableLocation(
    operator='Iarnród Éireann / Irish Rail',
    link='https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip',
    file_name='baz.txt',
  )
  info_row = dm.ExpectedFeedInfoCSVRowType(
    # this is the same data in the DB so it will clash
    feed_publisher_name='National Transport Authority',
    feed_publisher_url='https://www.nationaltransport.ie/',
    feed_lang='en',
    feed_start_date='20250530',
    feed_end_date='20240530',  # changed to be invalid
    feed_version='826FB35E-D58B-4FAB-92EC-C5D5CB697E68',
    feed_contact_email=None,
  )
  with pytest.raises(gtfs.RowError, match='1 row'):
    db._HandleFeedInfoRow(loc, 1, info_row)
  with pytest.raises(gtfs.base.Error, match='invalid dates'):
    db._HandleFeedInfoRow(loc, 0, info_row)
  info_row['feed_end_date'] = '20260530'  # the original
  with pytest.raises(gtfs.ParseIdenticalVersionError):
    db._HandleFeedInfoRow(loc, 0, info_row)
  # agency.txt - no raise to test
  # calendar.txt
  with pytest.raises(gtfs.base.Error, match='invalid dates'):
    db._HandleCalendarRow(
      loc,
      1,
      dm.ExpectedCalendarCSVRowType(
        service_id=2,
        monday=True,
        tuesday=True,
        wednesday=True,
        thursday=True,
        friday=True,
        saturday=True,
        sunday=True,
        start_date='20250530',
        end_date='20240530',
      ),
    )
  # calendar_dates.txt - no raise to test
  # routes.txt - no raise to test
  # shapes.txt
  shape = dm.ExpectedShapesCSVRowType(
    shape_id='foo',
    shape_pt_sequence=2,
    shape_pt_lat=10.0,
    shape_pt_lon=10.0,
    shape_dist_traveled=-4.0,
  )
  with pytest.raises(gtfs.base.Error, match='invalid distance'):
    db._HandleShapesRow(loc, 1, shape)
  # trips.txt
  with pytest.raises(gtfs.RowError, match='agency in row was not found'):
    db._HandleTripsRow(
      loc,
      1,
      dm.ExpectedTripsCSVRowType(
        trip_id='foo',
        route_id='bar',
        service_id=10,
        direction_id=True,
        shape_id=None,
        trip_headsign=None,
        block_id=None,
        trip_short_name=None,
      ),
    )
  # stops.txt
  stop = dm.ExpectedStopsCSVRowType(
    stop_id='foo',
    parent_station='bar',  # parent station is invalid
    stop_code='baz',
    stop_name='STOP!',
    stop_lat=10.0,
    stop_lon=10.0,
    zone_id=None,
    stop_desc=None,
    stop_url=None,
    location_type=None,
  )
  with pytest.raises(gtfs.RowError, match='parent_station in row was not found'):
    db._HandleStopsRow(loc, 1, stop)
  # stop_times.txt
  stop_time = dm.ExpectedStopTimesCSVRowType(
    trip_id='4669_10288',
    stop_sequence=10,
    stop_id='8360IR0003',
    arrival_time='10:00:00',
    departure_time='09:00:00',  # departure before arrival!
    timepoint=True,
    stop_headsign=None,
    pickup_type=None,
    drop_off_type=None,
    dropoff_type=None,
  )
  with pytest.raises(gtfs.base.Error, match='arrival <= departure'):
    db._HandleStopTimesRow(loc, 1, stop_time)
  stop_time['departure_time'] = '10:00:10'  # valid
  stop_time['stop_id'] = 'foo'  # invalid
  with pytest.raises(gtfs.RowError, match='stop_id in row was not found'):
    db._HandleStopTimesRow(loc, 1, stop_time)
  stop_time['stop_id'] = '8360IR0003'  # valid
  stop_time['trip_id'] = 'bar'  # invalid
  with pytest.raises(gtfs.RowError, match='trip_id in row was not found'):
    db._HandleStopTimesRow(loc, 1, stop_time)


@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_load_existing(deserialize: mock.MagicMock, serialize: mock.MagicMock) -> None:
  """Test."""
  # mock
  deserialize.return_value = dm.GTFSData(
    tm=0.0, files=dm.OfficialFiles(tm=0.0, files={}), agencies={}, calendar={}, shapes={}, stops={}
  )
  with (
    mock.patch('src.tfinta.gtfs.os.path.isdir', autospec=True) as is_dir,
    mock.patch('src.tfinta.gtfs.os.mkdir', autospec=True) as mk_dir,
    mock.patch('src.tfinta.gtfs.os.path.exists', autospec=True) as exists,
  ):
    is_dir.return_value = True
    exists.return_value = True
    # create database
    gtfs.GTFS(' db/path\t')  # some extra spaces...
    # check creation path
    is_dir.assert_called_once_with('db/path')
    mk_dir.assert_not_called()
    exists.assert_called_once_with('db/path/transit.db')
  deserialize.assert_called_once_with(file_path='db/path/transit.db', compress=True)
  serialize.assert_not_called()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_load(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  with typeguard.suppress_type_checks():
    result = typer_testing.CliRunner().invoke(gtfs.app, ['read'])
  assert result.exit_code == 0
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
  db_obj.PrettyPrintTrip.assert_not_called()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_print_basics(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  db_obj.PrettyPrintBasics.return_value = ['foo', 'bar']
  with typeguard.suppress_type_checks():
    result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'basics'])
  assert result.exit_code == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  db_obj.PrettyPrintBasics.assert_called_once_with()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_print_calendar(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  db_obj.PrettyPrintCalendar.return_value = ['foo', 'bar']
  with typeguard.suppress_type_checks():
    result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'calendars'])
  assert result.exit_code == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  db_obj.PrettyPrintCalendar.assert_called_once_with()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_print_stops(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  db_obj.PrettyPrintStops.return_value = ['foo', 'bar']
  with typeguard.suppress_type_checks():
    result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'stops'])
  assert result.exit_code == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  db_obj.PrettyPrintStops.assert_called_once_with()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_print_shape(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  db_obj.PrettyPrintShape.return_value = ['foo', 'bar']
  with typeguard.suppress_type_checks():
    result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'shape', '-i', '4669_658'])
  assert result.exit_code == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  db_obj.PrettyPrintShape.assert_called_once_with(shape_id='4669_658')


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_print_trip(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  db_obj.PrettyPrintTrip.return_value = ['foo', 'bar']
  with typeguard.suppress_type_checks():
    result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'trip', '-i', 'tid'])
  assert result.exit_code == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  db_obj.PrettyPrintTrip.assert_called_once_with(trip_id='tid')


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_print_all(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  db_obj.PrettyPrintTrip.return_value = ['foo', 'bar']
  with typeguard.suppress_type_checks():
    result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'all'])
  assert result.exit_code == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  db_obj.PrettyPrintAllDatabase.assert_called_once_with()
