# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""gtfs.py unittest."""

from __future__ import annotations

import datetime
import io
import pathlib
import zipfile as zf
import zoneinfo
from typing import LiteralString
from unittest import mock

import pytest
import typeguard
from click import testing as click_testing
from rich import table as rich_table
from transcrypto.utils import base as tc_base
from transcrypto.utils import config as app_config
from transcrypto.utils import logging as tc_logging
from typer import testing as typer_testing

from tfinta import gtfs
from tfinta import gtfs_data_model as dm
from tfinta import tfinta_base as base

from . import gtfs_data, util

# mock test files
_OPERATOR_CSV_PATH: pathlib.Path = util.DATA_DIR / 'GTFS Operator Files - 20250621.csv'
# the zip directory has a very reduced version of the real data in 202506
_ZIP_DIR_1: pathlib.Path = util.DATA_DIR / 'zip_1'


@pytest.fixture(autouse=True)
def reset_cli_logging_singletons() -> None:
  """Reset global console/logging state between tests.

  The CLI callback initializes a global Rich console singleton via InitLogging().
  Tests invoke the CLI multiple times across test cases, so we must reset that
  singleton to keep tests isolated.
  """
  tc_logging.ResetConsole()
  app_config.ResetConfig()


@pytest.fixture
def gtfs_object() -> gtfs.GTFS:
  """Return a GTFS object with all gtfs_data.ZIP_DB_1 data loaded.

  Returns:
    GTFS object with gtfs_data.ZIP_DB_1 data loaded.

  """
  db: gtfs.GTFS
  with (
    mock.patch('tfinta.gtfs.time.time', autospec=True) as time,
    mock.patch('transcrypto.core.key.Serialize', autospec=True),
    mock.patch('transcrypto.core.key.DeSerialize', autospec=True),
  ):
    time.return_value = gtfs_data.ZIP_DB_1_TM
    db = gtfs.GTFS(
      app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True)
    )
  db._db = gtfs_data.ZIP_DB_1
  return db


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_load_and_parse_from_net(  # noqa: PLR0915
  deserialize: mock.MagicMock,
  serialize: mock.MagicMock,
  urlopen: mock.MagicMock,
  time: mock.MagicMock,
) -> None:
  """Test."""
  # empty app_name should raise
  with pytest.raises(tc_base.Error):
    app_config.AppConfig(' \t', 'transit.db')  # empty app_name
  # mock
  db: gtfs.GTFS
  time.return_value = gtfs_data.ZIP_DB_1_TM
  mock_config: mock.MagicMock = util.MockAppConfig('\tdb/path ')  # some extra spaces...
  # Mock Serialize to track calls
  mock_config.Serialize.side_effect = lambda obj, **kwargs: serialize(  # pyright: ignore[reportUnknownLambdaType]
    obj, file_path=str(mock_config.path), **kwargs
  )
  db = gtfs.GTFS(mock_config)
  # load the GTFS data into database: do it BEFORE we mock open()!
  fake_csv = util.FakeHTTPFile(_OPERATOR_CSV_PATH)
  zip_bytes: bytes = gtfs_data.ZipDirBytes(pathlib.Path(_ZIP_DIR_1))
  fake_zip = util.FakeHTTPStream(zip_bytes)
  # Set up the mock cache path that will be created by dir / cache_file_name
  mock_cache_path: mock.MagicMock = mock.MagicMock()
  mock_cache_path.exists.return_value = False
  # Replace the lambda with a MagicMock so we can track calls
  mock_config.dir.__truediv__ = mock.MagicMock(return_value=mock_cache_path)
  urlopen.side_effect = [fake_csv, fake_zip]
  with typeguard.suppress_type_checks():
    db.LoadData(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
    )
  # Check that the cache path was checked for existence and written
  cache_file_name = 'https__www.transportforireland.ie_transitData_Data_GTFS_Irish_Rail.zip'
  mock_config.dir.__truediv__.assert_called_with(cache_file_name)
  mock_cache_path.exists.assert_called()
  mock_cache_path.write_bytes.assert_called_once_with(zip_bytes)
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
  util.AssertPrettyPrint(gtfs_data.BASICS_TABLE, db.PrettyPrintBasics())
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintCalendar(filter_to={544356456}))
  util.AssertPrettyPrint(gtfs_data.CALENDARS_TABLE, db.PrettyPrintCalendar())
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintStops(filter_to={'none'}))
  util.AssertPrettyPrint(gtfs_data.STOPS_TABLE, db.PrettyPrintStops())
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintShape(shape_id='none'))
  util.AssertPrettyPrint(gtfs_data.SHAPE_4669_658_TABLE, db.PrettyPrintShape(shape_id='4669_658'))
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintTrip(trip_id='none'))
  util.AssertPrettyPrint(gtfs_data.TRIP_4452_2655_TABLE, db.PrettyPrintTrip(trip_id='4452_2655'))
  util.AssertPrettyPrint(gtfs_data.ALL_TRIPS_TABLE, db.PrettyPrintAllDatabase())
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
  with pytest.raises(base.Error, match='invalid dates'):
    db._HandleFeedInfoRow(loc, 0, info_row)
  info_row['feed_end_date'] = '20260530'  # the original
  with pytest.raises(gtfs.ParseIdenticalVersionError):
    db._HandleFeedInfoRow(loc, 0, info_row)
  # agency.txt - no raise to test
  # calendar.txt
  with pytest.raises(base.Error, match='invalid dates'):
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
  with pytest.raises(base.Error, match='invalid distance'):
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
  with pytest.raises(base.Error, match='arrival <= departure'):
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
  mock_gtfs_data = dm.GTFSData(
    tm=0.0, files=dm.OfficialFiles(tm=0.0, files={}), agencies={}, calendar={}, shapes={}, stops={}
  )
  deserialize.return_value = mock_gtfs_data
  mock_config: mock.MagicMock = util.MockAppConfig(' db/path\t')  # some extra spaces...
  mock_config.path.exists.return_value = True
  # Mock the DeSerialize method to call the mocked key.DeSerialize
  mock_config.DeSerialize.return_value = mock_gtfs_data
  gtfs.GTFS(mock_config)
  # Verify DeSerialize was called on the config object
  mock_config.DeSerialize.assert_called_once()
  serialize.assert_not_called()


def test_main_load() -> None:
  """Test."""
  with mock.patch('tfinta.gtfs.GTFS', autospec=True) as mock_gtfs:
    db_obj = mock.MagicMock()
    mock_gtfs.return_value = db_obj
    result: click_testing.Result = typer_testing.CliRunner().invoke(gtfs.app, ['read'])
    assert result.exit_code == 0 and mock_gtfs.call_count == 1
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


def test_main_print_basics() -> None:
  """Test."""
  with (
    mock.patch('tfinta.gtfs.GTFS', autospec=True) as mock_gtfs,
    mock.patch('transcrypto.utils.logging.InitLogging') as mock_init_logging,
  ):
    mock_console = mock.MagicMock()
    mock_init_logging.return_value = (mock_console, 0, False)
    db_obj = mock.MagicMock()
    mock_gtfs.return_value = db_obj
    db_obj.PrettyPrintBasics.return_value = ['foo', 'bar']
    result: click_testing.Result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'basics'])
    assert result.exit_code == 0 and mock_gtfs.call_count == 1
    db_obj.LoadData.assert_not_called()
    db_obj.PrettyPrintBasics.assert_called_once_with()


def test_main_print_calendar() -> None:
  """Test."""
  with (
    mock.patch('tfinta.gtfs.GTFS', autospec=True) as mock_gtfs,
    mock.patch('transcrypto.utils.logging.InitLogging') as mock_init_logging,
  ):
    mock_console = mock.MagicMock()
    mock_init_logging.return_value = (mock_console, 0, False)
    db_obj = mock.MagicMock()
    mock_gtfs.return_value = db_obj
    db_obj.PrettyPrintCalendar.return_value = ['foo', 'bar']
    result: click_testing.Result = typer_testing.CliRunner().invoke(
      gtfs.app, ['print', 'calendars']
    )
    assert result.exit_code == 0 and mock_gtfs.call_count == 1
    db_obj.LoadData.assert_not_called()
    db_obj.PrettyPrintCalendar.assert_called_once_with()


def test_main_print_stops() -> None:
  """Test."""
  with (
    mock.patch('tfinta.gtfs.GTFS', autospec=True) as mock_gtfs,
    mock.patch('transcrypto.utils.logging.InitLogging') as mock_init_logging,
  ):
    mock_console = mock.MagicMock()
    mock_init_logging.return_value = (mock_console, 0, False)
    db_obj = mock.MagicMock()
    mock_gtfs.return_value = db_obj
    db_obj.PrettyPrintStops.return_value = ['foo', 'bar']
    result: click_testing.Result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'stops'])
    assert result.exit_code == 0 and mock_gtfs.call_count == 1
    db_obj.LoadData.assert_not_called()
    db_obj.PrettyPrintStops.assert_called_once_with()


def test_main_print_shape() -> None:
  """Test."""
  with (
    mock.patch('tfinta.gtfs.GTFS', autospec=True) as mock_gtfs,
    mock.patch('transcrypto.utils.logging.InitLogging') as mock_init_logging,
  ):
    mock_console = mock.MagicMock()
    mock_init_logging.return_value = (mock_console, 0, False)
    db_obj = mock.MagicMock()
    mock_gtfs.return_value = db_obj
    db_obj.PrettyPrintShape.return_value = ['foo', 'bar']
    result: click_testing.Result = typer_testing.CliRunner().invoke(
      gtfs.app, ['print', 'shape', '4669_658']
    )
    assert result.exit_code == 0 and mock_gtfs.call_count == 1
    db_obj.LoadData.assert_not_called()
    db_obj.PrettyPrintShape.assert_called_once_with(shape_id='4669_658')


def test_main_print_trip() -> None:
  """Test."""
  with (
    mock.patch('tfinta.gtfs.GTFS', autospec=True) as mock_gtfs,
    mock.patch('transcrypto.utils.logging.InitLogging') as mock_init_logging,
  ):
    mock_console = mock.MagicMock()
    mock_init_logging.return_value = (mock_console, 0, False)
    db_obj = mock.MagicMock()
    mock_gtfs.return_value = db_obj
    db_obj.PrettyPrintTrip.return_value = ['foo', 'bar']
    result: click_testing.Result = typer_testing.CliRunner().invoke(
      gtfs.app, ['print', 'trip', 'tid']
    )
    assert result.exit_code == 0 and mock_gtfs.call_count == 1
    db_obj.LoadData.assert_not_called()
    db_obj.PrettyPrintTrip.assert_called_once_with(trip_id='tid')


def test_main_print_all() -> None:
  """Test."""
  with mock.patch('tfinta.gtfs.GTFS', autospec=True) as mock_gtfs:
    db_obj = mock.MagicMock()
    mock_gtfs.return_value = db_obj
    db_obj.PrettyPrintTrip.return_value = ['foo', 'bar']
    result: click_testing.Result = typer_testing.CliRunner().invoke(gtfs.app, ['print', 'all'])
    assert result.exit_code == 0 and mock_gtfs.call_count == 1
    db_obj.LoadData.assert_not_called()
    db_obj.PrettyPrintAllDatabase.assert_called_once_with()


def test_main_version() -> None:
  """Test --version flag."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(gtfs.app, ['--version'])
  assert result.exit_code == 0


def test_main_markdown() -> None:
  """Test markdown command."""
  with (
    mock.patch('tfinta.gtfs.GTFS', autospec=True),
    mock.patch('transcrypto.utils.logging.InitLogging') as mock_init_logging,
  ):
    mock_console = mock.MagicMock()
    mock_init_logging.return_value = (mock_console, 0, False)
    result: click_testing.Result = typer_testing.CliRunner().invoke(gtfs.app, ['markdown'])
    assert result.exit_code == 0
    mock_console.print.assert_called_once()


# gtfs_data_model.py tests


def test_BaseStop_lt() -> None:
  """Test BaseStop __lt__."""
  s1 = dm.BaseStop(id='1', code='A', name='Alpha', point=base.Point(latitude=0, longitude=0))
  s2 = dm.BaseStop(id='2', code='B', name='Beta', point=base.Point(latitude=0, longitude=0))
  assert s1 < s2
  assert not s2 < s1


def test_ScheduleStop_lt_mixed_timepoint() -> None:
  """Test ScheduleStop raises TypeError on mixed timepoint comparison."""
  t = base.DayRange(arrival=base.DayTime(time=100), departure=base.DayTime(time=200))
  s1 = dm.ScheduleStop(times=t, timepoint=True)
  s2 = dm.ScheduleStop(times=t, timepoint=False)
  with pytest.raises(TypeError, match='invalid mixed timepoint'):
    _ = s1 < s2


def test_Trip_lt() -> None:
  """Test Trip __lt__."""
  t1 = dm.Trip(id='aaa', route='r1', agency=1, service=1, direction=True, stops={})
  t2 = dm.Trip(id='bbb', route='r1', agency=1, service=1, direction=True, stops={})
  assert t1 < t2 and not t2 < t1


def test_ShapePoint_lt() -> None:
  """Test ShapePoint __lt__."""
  sp1 = dm.ShapePoint(id='s1', seq=1, point=base.Point(latitude=0, longitude=0), distance=0.0)
  sp2 = dm.ShapePoint(id='s1', seq=2, point=base.Point(latitude=0, longitude=0), distance=1.0)
  assert sp1 < sp2 and not sp2 < sp1


def test_Schedule_lt() -> None:
  """Test Schedule __lt__ branches."""
  t10 = dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=100), departure=base.DayTime(time=200))
  )
  t20 = dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=300), departure=base.DayTime(time=400))
  )
  stop_a = dm.TrackStop(stop='a', name='Alpha')
  stop_b = dm.TrackStop(stop='b', name='Beta')
  stop_c = dm.TrackStop(stop='c', name='Charlie')
  # different direction
  sc1 = dm.Schedule(direction=False, stops=(stop_a, stop_b), times=(t10, t20))
  sc2 = dm.Schedule(direction=True, stops=(stop_a, stop_b), times=(t10, t20))
  assert sc1 < sc2
  # same direction, different first stop
  sc3 = dm.Schedule(direction=True, stops=(stop_a, stop_c), times=(t10, t20))
  sc4 = dm.Schedule(direction=True, stops=(stop_b, stop_c), times=(t10, t20))
  assert sc3 < sc4
  # same direction, same first stop, different last stop
  sc5 = dm.Schedule(direction=True, stops=(stop_a, stop_b), times=(t10, t20))
  sc6 = dm.Schedule(direction=True, stops=(stop_a, stop_c), times=(t10, t20))
  assert sc5 < sc6
  # same direction, same stops, different times
  t30 = dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=500), departure=base.DayTime(time=600))
  )
  sc7 = dm.Schedule(direction=True, stops=(stop_a, stop_b), times=(t10, t20))
  sc8 = dm.Schedule(direction=True, stops=(stop_a, stop_b), times=(t30, t20))
  assert sc7 < sc8


def test_PrettyPrintBasics_multiple_agencies(gtfs_object: gtfs.GTFS) -> None:
  """Test PrettyPrintBasics separator between agencies by adding a second agency."""
  db: gtfs.GTFS = gtfs_object
  # Add a second fake agency
  second_agency = dm.Agency(
    id=9999999,
    name='Test Agency',
    url='https://example.com',
    zone=zoneinfo.ZoneInfo('Europe/Dublin'),
    routes={},
  )
  db._db.agencies[9999999] = second_agency
  output: list[str | rich_table.Table] = list(db.PrettyPrintBasics())
  # The separator should appear between agencies
  assert (
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' in output
  )
  # Clean up
  del db._db.agencies[9999999]


def test_stop_times_old_dropoff_spelling(gtfs_object: gtfs.GTFS) -> None:
  """Test stop_times.txt handler with old 'dropoff_type' spelling."""
  db: gtfs.GTFS = gtfs_object
  loc = gtfs._TableLocation(
    operator='Iarnród Éireann / Irish Rail',
    link='https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip',
    file_name='stop_times.txt',
  )
  # Use existing valid data but with drop_off_type=None and dropoff_type=1
  stop_time = dm.ExpectedStopTimesCSVRowType(
    trip_id='4669_10288',
    stop_sequence=10,
    stop_id='8360IR0003',
    arrival_time='10:00:00',
    departure_time='10:00:10',
    timepoint=True,
    stop_headsign=None,
    pickup_type=None,
    drop_off_type=None,  # new spelling is None
    dropoff_type=1,  # old spelling has value
  )
  db._HandleStopTimesRow(loc, 1, stop_time)
  # Verify the stop was added with the old spelling value
  trip: dm.Trip = db._db.agencies[7778017].routes['4452_86269'].trips['4669_10288']
  assert trip.stops[10].dropoff == dm.StopPointType.NOT_AVAILABLE


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_load_csv_errors(
  _deserialize: mock.MagicMock,  # noqa: PT019
  _serialize: mock.MagicMock,  # noqa: PT019
  urlopen: mock.MagicMock,
  time_mock: mock.MagicMock,
) -> None:
  """Test _LoadCSVSources error branches."""
  time_mock.return_value = gtfs_data.ZIP_DB_1_TM
  db = gtfs.GTFS(app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True))
  # Test: row with != 2 columns
  bad_csv_1 = b'Operator,Link\nfoo,bar,baz\n'
  urlopen.return_value = util.FakeHTTPStream(bad_csv_1)
  with pytest.raises(gtfs.Error, match='Unexpected row'):
    db._LoadCSVSources()
  # Test: first row is wrong header
  bad_csv_2 = b'Wrong,Header\nfoo,bar\n'
  urlopen.return_value = util.FakeHTTPStream(bad_csv_2)
  with pytest.raises(gtfs.Error, match='Unexpected start'):
    db._LoadCSVSources()
  # Test: missing known operator
  bad_csv_3 = b'Operator,Link\nSome Other,http://example.com\n'
  urlopen.return_value = util.FakeHTTPStream(bad_csv_3)
  with pytest.raises(gtfs.Error, match='not in loaded CSV'):
    db._LoadCSVSources()


def test_GTFS_LoadGTFSSource_invalid(gtfs_object: gtfs.GTFS) -> None:
  """Test _LoadGTFSSource with invalid operator/URL."""
  db: gtfs.GTFS = gtfs_object
  with pytest.raises(gtfs.Error, match='invalid operator'):
    db._LoadGTFSSource('nonexistent', 'http://example.com')
  with pytest.raises(gtfs.Error, match='invalid URL'):
    db._LoadGTFSSource(dm.IRISH_RAIL_OPERATOR, 'http://nonexistent.com')


def test_GTFS_LoadGTFSSource_override_nonexistent(gtfs_object: gtfs.GTFS) -> None:
  """Test _LoadGTFSSource with nonexistent override file."""
  db: gtfs.GTFS = gtfs_object
  with (
    mock.patch('transcrypto.core.key.Serialize', autospec=True),
    pytest.raises(gtfs.Error, match='Override file does not exist'),
  ):
    db._LoadGTFSSource(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      override='/nonexistent/file.zip',
    )


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_LoadGTFSFile_unknown_file_raise(
  _deserialize: mock.MagicMock,  # noqa: PT019
  _serialize: mock.MagicMock,  # noqa: PT019
  _urlopen: mock.MagicMock,  # noqa: PT019
  time_mock: mock.MagicMock,
) -> None:
  """Test _LoadGTFSFile raises ParseImplementationError with allow_unknown_file=False."""
  time_mock.return_value = gtfs_data.ZIP_DB_1_TM
  db = gtfs.GTFS(app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True))
  loc = gtfs._TableLocation(
    operator='test',
    link='test',
    file_name='unknown.txt',
  )
  with pytest.raises(gtfs.ParseImplementationError, match='Unsupported'):
    db._LoadGTFSFile(loc, b'some data', allow_unknown_file=False, allow_unknown_field=False)


def test_GTFS_LoadGTFSFile_parse_errors(gtfs_object: gtfs.GTFS) -> None:
  """Test _LoadGTFSFile CSV field parsing error branches."""
  db: gtfs.GTFS = gtfs_object
  loc = gtfs._TableLocation(
    operator='Iarnród Éireann / Irish Rail',
    link='https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip',
    file_name='agency.txt',
  )
  # Test: empty required field
  csv_empty_required = b'agency_id,agency_name,agency_url,agency_timezone\n,foo,bar,baz\n'
  with pytest.raises(gtfs.ParseError, match='Empty required field'):
    db._LoadGTFSFile(loc, csv_empty_required, allow_unknown_file=False, allow_unknown_field=True)
  # Test: invalid bool value
  loc_cal = gtfs._TableLocation(
    operator='Iarnród Éireann / Irish Rail',
    link='https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip',
    file_name='calendar.txt',
  )
  csv_bad_bool = (
    b'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n'
    b'1,YES,1,1,1,1,0,0,20250101,20251231\n'
  )
  with pytest.raises(gtfs.ParseError, match='invalid bool value'):
    db._LoadGTFSFile(loc_cal, csv_bad_bool, allow_unknown_file=False, allow_unknown_field=True)
  # Test: invalid int value
  csv_bad_int = (
    b'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n'
    b'NOTANINT,1,1,1,1,1,0,0,20250101,20251231\n'  # cspell: disable-line
  )
  with pytest.raises(gtfs.ParseError, match='invalid int/float value'):
    db._LoadGTFSFile(loc_cal, csv_bad_int, allow_unknown_file=False, allow_unknown_field=True)
  # Test: missing required fields (row missing columns)
  csv_missing = b'agency_id,agency_name\n1,foo\n'
  with pytest.raises(gtfs.ParseError, match='Missing required fields'):
    db._LoadGTFSFile(loc, csv_missing, allow_unknown_file=False, allow_unknown_field=True)


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_LoadGTFSSource_missing_required_file(
  _deserialize: mock.MagicMock,  # noqa: PT019
  _serialize: mock.MagicMock,  # noqa: PT019
  urlopen: mock.MagicMock,
  time_mock: mock.MagicMock,
) -> None:
  """Test that missing required files in ZIP raises ParseError."""
  time_mock.return_value = gtfs_data.ZIP_DB_1_TM
  db = gtfs.GTFS(app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True))
  # Load CSV sources first so db.files is populated
  good_csv: bytes = (
    b'Operator,Link\n'
    + dm.IRISH_RAIL_OPERATOR.encode()
    + b','
    + dm.IRISH_RAIL_LINK.encode()
    + b'\n'
  )
  urlopen.return_value = util.FakeHTTPStream(good_csv)
  db._LoadCSVSources()
  # Create a ZIP with only agency.txt (missing feed_info.txt which is required)
  zip_buffer = io.BytesIO()
  with zf.ZipFile(zip_buffer, 'w') as z:
    z.writestr(
      'agency.txt',
      'agency_id,agency_name,agency_url,agency_timezone\n7778017,Test,http://x,Europe/Dublin\n',
    )
  zip_bytes: bytes = zip_buffer.getvalue()
  mock_path = mock.MagicMock()
  mock_path.exists.return_value = False
  with mock.patch('tfinta.gtfs.pathlib.Path') as path_mock_2, typeguard.suppress_type_checks():
    path_mock_2.return_value = mock_path
    urlopen.return_value = util.FakeHTTPStream(zip_bytes)
    with pytest.raises(gtfs.ParseError, match='Missing required files'):
      db._LoadGTFSSource(
        dm.IRISH_RAIL_OPERATOR,
        dm.IRISH_RAIL_LINK,
        allow_unknown_file=True,
        allow_unknown_field=True,
      )


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_LoadGTFSSource_identical_version_skip(
  _deserialize: mock.MagicMock,  # noqa: PT019
  _serialize: mock.MagicMock,  # noqa: PT019
  urlopen: mock.MagicMock,
  time_mock: mock.MagicMock,
) -> None:
  """Test ParseIdenticalVersionError with force_replace=False (skip) and True (continue)."""
  time_mock.return_value = gtfs_data.ZIP_DB_1_TM
  db = gtfs.GTFS(app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True))
  # Load CSV sources
  good_csv: bytes = (
    b'Operator,Link\n'
    + dm.IRISH_RAIL_OPERATOR.encode()
    + b','
    + dm.IRISH_RAIL_LINK.encode()
    + b'\n'
  )
  urlopen.return_value = util.FakeHTTPStream(good_csv)
  db._LoadCSVSources()
  # Load the test ZIP first time
  zip_bytes: bytes = gtfs_data.ZipDirBytes(pathlib.Path(_ZIP_DIR_1))
  mock_path: mock.MagicMock = mock.MagicMock()
  mock_path.exists.return_value = False
  with mock.patch('tfinta.gtfs.pathlib.Path') as path_mock_2, typeguard.suppress_type_checks():
    path_mock_2.return_value = mock_path
    urlopen.return_value = util.FakeHTTPStream(zip_bytes)
    db._LoadGTFSSource(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
    )
  # Load the same ZIP again with force_replace=False → skip path
  with mock.patch('tfinta.gtfs.pathlib.Path') as path_mock_3, typeguard.suppress_type_checks():
    path_mock_3.return_value = mock_path
    urlopen.return_value = util.FakeHTTPStream(zip_bytes)
    db._LoadGTFSSource(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
      force_replace=False,
    )
  # Load the same ZIP again with force_replace=True → continue path
  with mock.patch('tfinta.gtfs.pathlib.Path') as path_mock_4, typeguard.suppress_type_checks():
    path_mock_4.return_value = mock_path
    urlopen.return_value = util.FakeHTTPStream(zip_bytes)
    db._LoadGTFSSource(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
      force_replace=True,
    )


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_LoadData_override_and_freshness(
  _deserialize: mock.MagicMock,  # noqa: PT019
  _serialize: mock.MagicMock,  # noqa: PT019
  urlopen: mock.MagicMock,
  time_mock: mock.MagicMock,
) -> None:
  """Test LoadData with override path and freshness skip."""
  time_mock.return_value = gtfs_data.ZIP_DB_1_TM
  db = gtfs.GTFS(app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True))
  # Load CSV sources
  good_csv: bytes = (
    b'Operator,Link\n'
    + dm.IRISH_RAIL_OPERATOR.encode()
    + b','
    + dm.IRISH_RAIL_LINK.encode()
    + b'\n'
  )
  urlopen.return_value = util.FakeHTTPStream(good_csv)
  db._LoadCSVSources()
  # First pass: load the ZIP to populate file metadata
  zip_bytes: bytes = gtfs_data.ZipDirBytes(pathlib.Path(_ZIP_DIR_1))
  mock_path = mock.MagicMock()
  mock_path.exists.return_value = False
  with mock.patch('tfinta.gtfs.pathlib.Path') as path_mock_2, typeguard.suppress_type_checks():
    path_mock_2.return_value = mock_path
    urlopen.return_value = util.FakeHTTPStream(zip_bytes)
    db._LoadGTFSSource(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
    )
    # Now LoadData with freshness should skip (data is 0 days old)
    db.LoadData(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
      freshness=10,
    )


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_LoadGTFSSource_cache_file(
  _deserialize: mock.MagicMock,  # noqa: PT019
  _serialize: mock.MagicMock,  # noqa: PT019
  time_mock: mock.MagicMock,
) -> None:
  """Test _LoadGTFSSource loading from cache file and override file."""
  time_mock.return_value = gtfs_data.ZIP_DB_1_TM
  test_config = app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True)
  db = gtfs.GTFS(test_config)
  # Pre-populate files so operator/link validation passes
  db._db.files.files = {dm.IRISH_RAIL_OPERATOR: {dm.IRISH_RAIL_LINK: None}}
  db._db.files.tm = time_mock.return_value
  # Write the ZIP to a temp file for "override" test
  zip_bytes: bytes = gtfs_data.ZipDirBytes(pathlib.Path(_ZIP_DIR_1))
  override_path: pathlib.Path = test_config.dir / 'test.zip'
  override_path.write_bytes(zip_bytes)
  # Test override path
  with typeguard.suppress_type_checks():
    db._LoadGTFSSource(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
      override=str(override_path),
    )
  # Test cache file path: write to cache and load from it
  cache_name: LiteralString = dm.IRISH_RAIL_LINK.replace('://', '__').replace('/', '_')
  cache_path: pathlib.Path = test_config.dir / cache_name
  cache_path.write_bytes(zip_bytes)
  # Create a new GTFS instance with the same fixed_dir - no need to manually set dir
  db2 = gtfs.GTFS(test_config)
  db2._db.files.files = {dm.IRISH_RAIL_OPERATOR: {dm.IRISH_RAIL_LINK: None}}
  db2._db.files.tm = time_mock.return_value
  # Clear existing metadata so it doesn't skip
  db2._db.files.files[dm.IRISH_RAIL_OPERATOR][dm.IRISH_RAIL_LINK] = None
  with typeguard.suppress_type_checks():
    db2._LoadGTFSSource(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
      force_replace=False,
    )


def test_GTFS_ParsingSession_exception(gtfs_object: gtfs.GTFS) -> None:
  """Test _ParsingSession invalidates caches on exception.

  Raises:
    ValueError: test error

  """
  db: gtfs.GTFS = gtfs_object
  with (
    mock.patch('transcrypto.core.key.Serialize', autospec=True),
    pytest.raises(ValueError, match='test error'),
    db._ParsingSession(),
  ):
    raise ValueError('test error')


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_LoadData_with_override(
  _deserialize: mock.MagicMock,  # noqa: PT019
  _serialize: mock.MagicMock,  # noqa: PT019
  urlopen: mock.MagicMock,
  time_mock: mock.MagicMock,
) -> None:
  """Test LoadData with explicit override path (covers lines 420-421)."""
  time_mock.return_value = gtfs_data.ZIP_DB_1_TM
  # Use real AppConfig with fixed_dir
  test_config = app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True)
  db = gtfs.GTFS(test_config)
  # Populate CSV sources
  good_csv: bytes = (
    b'Operator,Link\n'
    + dm.IRISH_RAIL_OPERATOR.encode()
    + b','
    + dm.IRISH_RAIL_LINK.encode()
    + b'\n'
  )
  urlopen.return_value = util.FakeHTTPStream(good_csv)
  db._LoadCSVSources()
  # Write an override ZIP file to a real path
  zip_bytes: bytes = gtfs_data.ZipDirBytes(pathlib.Path(_ZIP_DIR_1))
  override_path: pathlib.Path = test_config.dir / 'override.zip'
  override_path.write_bytes(zip_bytes)
  # Call LoadData with override. The override path exists as a real file.
  with typeguard.suppress_type_checks():
    db.LoadData(
      dm.IRISH_RAIL_OPERATOR,
      dm.IRISH_RAIL_LINK,
      allow_unknown_file=True,
      allow_unknown_field=True,
      override=str(override_path),
    )


@mock.patch('tfinta.gtfs.time.time', autospec=True)
@mock.patch('tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('transcrypto.core.key.Serialize', autospec=True)
@mock.patch('transcrypto.core.key.DeSerialize', autospec=True)
def test_GTFS_LoadGTFSFile_unknown_field_not_allowed(
  _deserialize: mock.MagicMock,  # noqa: PT019
  _serialize: mock.MagicMock,  # noqa: PT019
  _urlopen: mock.MagicMock,  # noqa: PT019
  time_mock: mock.MagicMock,
) -> None:
  """Test _LoadGTFSFile raises on unknown field when allow_unknown_field=False."""
  time_mock.return_value = gtfs_data.ZIP_DB_1_TM
  db = gtfs.GTFS(app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True))
  # Create a minimal agency.txt CSV with an extra unknown column
  csv_data = (
    b'agency_id,agency_name,agency_url,agency_timezone,agency_lang,unknown_col\n'
    b'1,Test Agency,http://test.com,Europe/Dublin,en,extra_value\n'
  )
  loc = gtfs._TableLocation(
    operator='Test', link='http://test.com/test.zip', file_name='agency.txt'
  )
  with pytest.raises(gtfs.ParseImplementationError, match='Extra fields'):
    db._LoadGTFSFile(
      loc,
      csv_data,
      allow_unknown_field=False,
      allow_unknown_file=True,
    )


@mock.patch('tfinta.gtfs.GTFS', autospec=True)
def test_PrintAll_gtfs_body(mock_gtfs: mock.MagicMock) -> None:
  """Test gtfs PrintAll by directly calling it to cover body lines."""
  mock_db = mock.MagicMock()
  mock_db.PrettyPrintAllDatabase.return_value = iter(['gtfs_line'])
  mock_gtfs.return_value = mock_db
  mock_ctx = mock.MagicMock()
  mock_ctx.obj = gtfs.GTFSConfig(
    console=mock.MagicMock(),
    verbose=0,
    color=True,
    appconfig=app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True),
  )
  gtfs.PrintAll(ctx=mock_ctx)
  mock_db.PrettyPrintAllDatabase.assert_called_once()
  mock_ctx.obj.console.print.assert_called_once_with('gtfs_line')  # type: ignore[attr-defined]
