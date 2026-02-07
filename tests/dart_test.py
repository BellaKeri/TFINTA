# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""dart.py unittest."""

from __future__ import annotations

import copy
import datetime
from collections import abc
from unittest import mock

import pytest
import typeguard
from click import testing as click_testing
from src.tfinta import dart, gtfs
from src.tfinta import tfinta_base as base
from transcrypto.utils import config as app_config
from transcrypto.utils import logging as tc_logging
from typer import testing as typer_testing

from tfinta import gtfs_data_model as dm

from . import gtfs_data, util


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
  # create object with all the disk features disabled
  db: gtfs.GTFS
  with (
    mock.patch('src.tfinta.gtfs.time.time', autospec=True) as time,
    mock.patch('transcrypto.core.key.Serialize', autospec=True),
    mock.patch('transcrypto.core.key.DeSerialize', autospec=True),
  ):
    time.return_value = gtfs_data.ZIP_DB_1_TM
    db = gtfs.GTFS(
      app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True)
    )
  # monkey-patch the data into the object
  db._db = gtfs_data.ZIP_DB_1
  return db


def test_DART(gtfs_object: gtfs.GTFS) -> None:
  """Test."""
  with typeguard.suppress_type_checks():
    with pytest.raises(gtfs.Error):
      dart.DART(None)  # pyright: ignore[reportArgumentType]
    db = dart.DART(gtfs_object)
  assert db.Services() == {83, 84}
  assert db.ServicesForDay(datetime.date(2025, 8, 4)) == {84}
  assert db.ServicesForDay(datetime.date(2025, 6, 22)) == {83}
  assert db.ServicesForDay(datetime.date(2025, 6, 23)) == set()
  assert db._dart_trips == gtfs_data.DART_TRIPS_ZIP_1
  with pytest.raises(gtfs.Error), typeguard.suppress_type_checks():
    list(db.PrettyDaySchedule(day=None))  # pyright: ignore[reportArgumentType]
  util.AssertPrettyPrint(
    gtfs_data.TRIPS_SCHEDULE_2025_08_04, db.PrettyDaySchedule(day=datetime.date(2025, 8, 4))
  )
  with pytest.raises(gtfs.Error):
    list(db.PrettyStationSchedule(stop_id=' \t', day=datetime.date(2025, 8, 4)))
  util.AssertPrettyPrint(
    gtfs_data.STATION_SCHEDULE_2025_08_04,
    db.PrettyStationSchedule(stop_id='8350IR0123', day=datetime.date(2025, 8, 4)),
  )
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintTrip(trip_name=' \t'))
  util.AssertPrettyPrint(gtfs_data.TRIP_E818, db.PrettyPrintTrip(trip_name='E818'))
  util.AssertPrettyPrint(gtfs_data.ALL_DATA, db.PrettyPrintAllDatabase())


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_load(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  result: click_testing.Result = typer_testing.CliRunner().invoke(dart.app, ['read'])
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
  mock_dart.assert_not_called()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_print_calendars(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj, dart_obj = mock.MagicMock(), mock.MagicMock()
  mock_gtfs.return_value = db_obj
  mock_dart.return_value = dart_obj
  dart_obj.PrettyPrintCalendar.return_value = ['foo', 'bar']
  result: click_testing.Result = typer_testing.CliRunner().invoke(dart.app, ['print', 'calendars'])
  assert result.exit_code == 0 and mock_gtfs.call_count == 1
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
  result: click_testing.Result = typer_testing.CliRunner().invoke(dart.app, ['print', 'stops'])
  assert result.exit_code == 0 and mock_gtfs.call_count == 1
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
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    dart.app, ['print', 'trips', '20250804']
  )
  assert result.exit_code == 0 and mock_gtfs.call_count == 1
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
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    dart.app, ['print', 'station', 'daly', '20250804']
  )
  assert result.exit_code == 0 and mock_gtfs.call_count == 1
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
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    dart.app, ['print', 'trip', 'E108']
  )
  assert result.exit_code == 0 and mock_gtfs.call_count == 1
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
  result: click_testing.Result = typer_testing.CliRunner().invoke(dart.app, ['print', 'all'])
  assert result.exit_code == 0 and mock_gtfs.call_count == 1
  db_obj.LoadData.assert_not_called()
  mock_dart.assert_called_once_with(db_obj)
  dart_obj.PrettyPrintAllDatabase.assert_called_once_with()


def test_main_version() -> None:
  """Test --version flag."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(dart.app, ['--version'])
  assert result.exit_code == 0


def test_main_invalid_date() -> None:
  """Test Main callback with invalid date."""
  original: int = dart._TODAY_INT
  try:
    dart._TODAY_INT = 19000101
    result: click_testing.Result = typer_testing.CliRunner().invoke(dart.app, ['print', 'all'])
    assert result.exit_code != 0
  finally:
    dart._TODAY_INT = original


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_main_markdown(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test markdown command."""
  db_obj, dart_obj = mock.MagicMock(), mock.MagicMock()
  mock_gtfs.return_value = db_obj
  mock_dart.return_value = dart_obj
  result: click_testing.Result = typer_testing.CliRunner().invoke(dart.app, ['markdown'])
  assert result.exit_code == 0


def test_DART_no_dart_route(gtfs_object: gtfs.GTFS) -> None:
  """Test DART construction raises when no DART route exists."""
  db: gtfs.GTFS = gtfs_object
  # Remove all routes from the Irish Rail agency
  agency: dm.Agency = db._db.agencies[7778017]
  original_routes: dict[str, dm.Route] = agency.routes
  agency.routes = {}
  with pytest.raises(gtfs.Error, match='DART route'):
    dart.DART(db)
  agency.routes = original_routes


def test_DART_empty_trip_name(gtfs_object: gtfs.GTFS) -> None:
  """Test DART construction raises when trip has empty name."""
  db: gtfs.GTFS = gtfs_object
  # Find a trip and set name to empty
  route: dm.Route = db._db.agencies[7778017].routes['4452_86289']
  trip: dm.Trip = next(iter(route.trips.values()))
  original_name: str | None = trip.name
  trip.name = ''
  with pytest.raises(dart.Error, match='empty trip name'):
    dart.DART(db)
  trip.name = original_name


def test_DART_trip_fewer_than_2_stops(gtfs_object: gtfs.GTFS) -> None:
  """Test DART construction raises when trip has fewer than 2 stops."""
  db: gtfs.GTFS = gtfs_object
  route: dm.Route = db._db.agencies[7778017].routes['4452_86289']
  trip: dm.Trip = next(iter(route.trips.values()))
  original_stops: dict[int, dm.Stop] = trip.stops
  # Keep only 1 stop
  trip.stops = {1: trip.stops[1]}
  with pytest.raises(dart.Error, match='fewer than 2 stops'):
    dart.DART(db)
  trip.stops = original_stops


def test_DART_WalkTrains_empty_filter(gtfs_object: gtfs.GTFS) -> None:
  """Test WalkTrains with empty filter_services yields nothing."""
  with typeguard.suppress_type_checks():
    db = dart.DART(gtfs_object)
  trains: list[tuple[dm.Schedule, str, list[tuple[int, dm.Schedule, dm.Trip]]]] = list(
    db.WalkTrains(filter_services=set())
  )
  assert trains == []


def test_DART_StationSchedule_duplicate(gtfs_object: gtfs.GTFS) -> None:
  """Test StationSchedule raises on duplicate stop/time."""
  with typeguard.suppress_type_checks():
    db = dart.DART(gtfs_object)
  # Mock WalkTrains to return two train groups that both stop at the target station
  # with the same destination and same schedule time, creating a duplicate key.
  target_stop = '8350IR0123'
  dest_stop = '8350IR0122'
  sched_stop = dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=76680), departure=base.DayTime(time=76680))
  )
  schedule1 = dm.Schedule(
    direction=False,
    stops=(
      dm.TrackStop(stop=target_stop, name='Bray (Daly)'),
      dm.TrackStop(stop=dest_stop, name='Greystones'),
    ),
    times=(sched_stop, sched_stop),
  )
  schedule2 = dm.Schedule(
    direction=False,
    stops=(
      dm.TrackStop(stop=target_stop, name='Bray (Daly)'),
      dm.TrackStop(stop=dest_stop, name='Greystones'),
    ),
    times=(sched_stop, sched_stop),
  )
  fake_trip: dm.Trip = next(iter(db._dart_trips.values()))[0][2]

  def fake_walk(
    filter_services: set[int] | None = None,  # noqa: ARG001
  ) -> abc.Generator[tuple[dm.Schedule, str, list[tuple[int, dm.Schedule, dm.Trip]]], None, None]:
    yield (schedule1, 'E818', [(83, schedule1, fake_trip)])
    yield (schedule2, 'E666', [(83, schedule2, fake_trip)])

  with (
    mock.patch.object(db, 'WalkTrains', side_effect=fake_walk),
    pytest.raises(dart.Error, match='Duplicate stop/time'),
  ):
    db.StationSchedule(target_stop, datetime.date(2025, 6, 22))


def test_DART_PrettyPrintTrip_inconsistent(gtfs_object: gtfs.GTFS) -> None:
  """Test PrettyPrintTrip raises on inconsistent route/agency/headsign."""
  db_obj: gtfs.GTFS = gtfs_object
  route: dm.Route = db_obj._db.agencies[7778017].routes['4452_86289']
  # Modify one trip in E818 to have a different route
  original_route: str = route.trips['4452_2662'].route
  route.trips['4452_2662'].route = 'different_route'
  with typeguard.suppress_type_checks():
    db = dart.DART(db_obj)
    with pytest.raises(dart.Error, match='should be consistent'):
      list(db.PrettyPrintTrip(trip_name='E818'))
  route.trips['4452_2662'].route = original_route


def test_DART_PrettyPrintTrip_alignment_error(gtfs_object: gtfs.GTFS) -> None:
  """Test PrettyPrintTrip raises when stop alignment fails."""
  with typeguard.suppress_type_checks():
    db = dart.DART(gtfs_object)
  # Modify _dart_trips directly: create a trip with stops that don't align
  # with the longest trip in the same group.
  # Get the longest trip for E666 and add a shorter trip with non-aligning stops.
  e666_trains: list[tuple[int, dm.Schedule, dm.Trip]] = db._dart_trips['E666']
  longest: tuple[int, dm.Schedule, dm.Trip] = max(e666_trains, key=lambda t: len(t[2].stops))
  longest_trip: dm.Trip = longest[2]
  # Create a short trip with fake stops that don't match first or last of longest
  short_trip: dm.Trip = copy.deepcopy(longest_trip)
  short_trip.stops = {
    1: dm.Stop(
      id='fake_id',
      seq=1,
      stop='FAKE_STOP_1',
      agency=7778017,
      route='4452_86289',
      scheduled=dm.ScheduleStop(
        times=base.DayRange(arrival=base.DayTime(time=76680), departure=base.DayTime(time=76680))
      ),
    ),
  }
  # Add this short trip to the E666 group
  db._dart_trips['E666'].append((83, e666_trains[0][1], short_trip))
  with pytest.raises(dart.Error, match='Could not find alignment'):
    list(db.PrettyPrintTrip(trip_name='E666'))


def test_DART_PrettyPrintTrip_FindTrip_not_found(gtfs_object: gtfs.GTFS) -> None:
  """Test PrettyPrintTrip raises when FindTrip returns None."""
  with typeguard.suppress_type_checks():
    db = dart.DART(gtfs_object)
  with (
    mock.patch.object(db._gtfs, 'FindTrip', return_value=(None, None, None)),
    pytest.raises(dart.Error, match='was not found'),
  ):
    list(db.PrettyPrintTrip(trip_name='E818'))


def test_DART_PrettyStationSchedule_time_backwards(gtfs_object: gtfs.GTFS) -> None:
  """Test PrettyStationSchedule raises when time moves backwards."""
  with typeguard.suppress_type_checks():
    db = dart.DART(gtfs_object)
  fake_schedule = dm.Schedule(
    direction=False,
    stops=(
      dm.TrackStop(stop='8350IR0122', name='Greystones'),
      dm.TrackStop(stop='8350IR0123', name='Bray (Daly)'),
    ),
    times=(
      dm.ScheduleStop(
        times=base.DayRange(arrival=base.DayTime(time=76680), departure=base.DayTime(time=76680))
      ),
      dm.ScheduleStop(
        times=base.DayRange(arrival=base.DayTime(time=77280), departure=base.DayTime(time=77460))
      ),
    ),
  )
  fake_trip: dm.Trip = next(iter(db._dart_trips.values()))[0][2]
  trips_in_train: list[tuple[int, dm.Schedule, dm.Trip]] = [(83, fake_schedule, fake_trip)]
  # DayRange.__lt__ sorts by departure first. Create two entries where:
  # Entry A has dep=100, arr=200 → sorted first (lower dep)
  # Entry B has dep=300, arr=50 → sorted second (higher dep)
  # After processing A: last_arrival=200
  # Processing B: arrival=50 < last_arrival=200 → time moved backwards!
  fake_station_data: dict[
    tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[tuple[int, dm.Schedule, dm.Trip]]]
  ] = {
    (
      '8350IR0122',
      dm.ScheduleStop(
        times=base.DayRange(
          arrival=base.DayTime(time=200),
          departure=base.DayTime(time=100),
          strict=False,
        )
      ),
    ): ('E818', fake_schedule, trips_in_train),
    (
      '8350IR0123',
      dm.ScheduleStop(
        times=base.DayRange(
          arrival=base.DayTime(time=50),
          departure=base.DayTime(time=300),
          strict=False,
        )
      ),
    ): ('E666', fake_schedule, trips_in_train),
  }
  with (
    mock.patch.object(db, 'StationSchedule', return_value=fake_station_data),
    pytest.raises(dart.Error, match='time moved backwards'),
  ):
    list(db.PrettyStationSchedule(stop_id='8350IR0123', day=datetime.date(2025, 8, 4)))


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_PrintAll_body(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test PrintAll by directly calling the function to cover body lines."""
  mock_dart_instance = mock.MagicMock()
  mock_dart_instance.PrettyPrintAllDatabase.return_value = iter(['test_line_1', 'test_line_2'])
  mock_dart.return_value = mock_dart_instance
  mock_gtfs.return_value = mock.MagicMock()
  mock_ctx = mock.MagicMock()
  mock_ctx.obj = dart.DARTConfig(
    console=mock.MagicMock(),
    verbose=0,
    color=True,
    appconfig=app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True),
  )
  dart.PrintAll(ctx=mock_ctx)
  mock_dart_instance.PrettyPrintAllDatabase.assert_called_once()
  assert mock_ctx.obj.console.print.call_count == 2


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
@mock.patch('src.tfinta.dart.DART', autospec=True)
def test_PrintTrip_body(mock_dart: mock.MagicMock, mock_gtfs: mock.MagicMock) -> None:
  """Test PrintTrip by directly calling the function to cover body lines."""
  mock_dart_instance = mock.MagicMock()
  mock_dart_instance.PrettyPrintTrip.return_value = iter(['line1'])
  mock_dart.return_value = mock_dart_instance
  mock_gtfs.return_value = mock.MagicMock()
  mock_ctx = mock.MagicMock()
  mock_ctx.obj = dart.DARTConfig(
    console=mock.MagicMock(),
    verbose=0,
    color=True,
    appconfig=app_config.AppConfig(base.APP_NAME, base.CONFIG_FILE_NAME, make_it_temporary=True),
  )
  dart.PrintTrip(ctx=mock_ctx, train='E108')
  mock_dart_instance.PrettyPrintTrip.assert_called_once_with(trip_name='E108')
  mock_ctx.obj.console.print.assert_called_once_with('line1')
