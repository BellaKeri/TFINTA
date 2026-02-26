# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""db.py unittest - database helpers (all queries mocked, no real Postgres needed)."""

from __future__ import annotations

import datetime
from unittest import mock

import pytest

from tfinta import db
from tfinta import realtime_data_model as dm
from tfinta import tfinta_base as base

# ---------------------------------------------------------------------------
# DayTime / DayRange helpers
# ---------------------------------------------------------------------------


def test_returns_none_for_none() -> None:
  """Test."""
  assert db._DayTime(None) is None


def test_returns_daytime() -> None:
  """Test."""
  dt = db._DayTime(3600)
  assert dt is not None
  assert dt.time == 3600


def test_returns_zero() -> None:
  """Test."""
  dt = db._DayTime(0)
  assert dt is not None
  assert dt.time == 0


def test_nullable_both_none() -> None:
  """Test."""
  dr = db._DayRange(None, None, nullable=True)
  assert dr.arrival is None
  assert dr.departure is None


def test_with_values() -> None:
  """Test."""
  dr = db._DayRange(100, 200)
  assert dr.arrival is not None
  assert dr.departure is not None
  assert dr.arrival.time == 100
  assert dr.departure.time == 200


# ---------------------------------------------------------------------------
# Pool management
# ---------------------------------------------------------------------------


def test_get_pool_raises_when_not_open() -> None:
  """Test."""
  db._pool = None
  with pytest.raises(db.Error, match='not initialized'):
    db.GetPool()


@mock.patch('tfinta.db.psycopg_pool.ConnectionPool')
def test_open_pool_creates_pool(mock_pool_cls: mock.MagicMock) -> None:
  """Test."""
  db._pool = None
  pool = db.OpenPool()
  assert pool is mock_pool_cls.return_value
  mock_pool_cls.assert_called_once()
  db.ClosePool()  # cleanup


@mock.patch('tfinta.db.psycopg_pool.ConnectionPool')
def test_open_pool_idempotent(mock_pool_cls: mock.MagicMock) -> None:
  """Test."""
  db._pool = None
  p1 = db.OpenPool()
  p2 = db.OpenPool()
  assert p1 is p2
  mock_pool_cls.assert_called_once()
  db.ClosePool()


def test_close_pool_idempotent() -> None:
  """Test."""
  db._pool = None
  db.ClosePool()  # should not raise


# ---------------------------------------------------------------------------
# fetch_stations
# ---------------------------------------------------------------------------


def test_returns_stations() -> None:
  """Test."""
  rows = [
    {
      'id': 228,
      'code': 'MHIDE',
      'description': 'Malahide',
      'latitude': 53.45,
      'longitude': -6.16,
      'alias': None,
    },
    {
      'id': 999,
      'code': 'CENTJ',
      'description': 'Central Junction',
      'latitude': None,
      'longitude': None,
      'alias': 'Dublin Connolly',
    },
  ]
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchall.return_value = rows
  db._pool = mock_pool
  try:
    stations = db.FetchStations()
    assert len(stations) == 2
    assert stations[0].code == 'MHIDE'
    assert stations[0].location is not None
    assert abs(stations[0].location.latitude - 53.45) < 1e-6
    assert stations[1].location is None
    assert stations[1].alias == 'Dublin Connolly'
  finally:
    db._pool = None


# ---------------------------------------------------------------------------
# fetch_running_trains
# ---------------------------------------------------------------------------


def test_returns_trains() -> None:
  """Test."""
  rows = [
    {
      'code': 'A152',
      'status': 2,
      'day': datetime.date(2025, 6, 29),
      'direction': 'Northbound',
      'message': 'A152\nRunning north',
      'latitude': 54.0,
      'longitude': -6.41,
    },
  ]
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchall.return_value = rows
  db._pool = mock_pool
  try:
    trains = db.FetchRunningTrains()
    assert len(trains) == 1
    assert trains[0].code == 'A152'
    assert trains[0].status == dm.TrainStatus.RUNNING
    assert trains[0].position is not None
  finally:
    db._pool = None


# ---------------------------------------------------------------------------
# resolve_station_code
# ---------------------------------------------------------------------------


def setup_pool() -> tuple[mock.MagicMock, mock.MagicMock]:
  """Test setup pool.

  Returns:
    tuple[mock.MagicMock, mock.MagicMock]: mock pool and cursor.

  """
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  db._pool = mock_pool
  return mock_pool, mock_cur


def test_exact_code_match() -> None:
  """Test."""
  _, mock_cur = setup_pool()
  mock_cur.fetchone.return_value = {'code': 'MHIDE'}
  try:
    assert db.ResolveStationCode('MHIDE') == 'MHIDE'
  finally:
    db._pool = None


def test_fragment_match_single() -> None:
  """Test."""
  _, mock_cur = setup_pool()
  # First fetchone (exact code) returns None, then fetchall for fragment
  mock_cur.fetchone.return_value = None
  mock_cur.fetchall.return_value = [{'code': 'MHIDE'}]
  try:
    assert db.ResolveStationCode('malahide') == 'MHIDE'
  finally:
    db._pool = None


def test_fragment_no_match() -> None:
  """Test."""
  _, mock_cur = setup_pool()
  mock_cur.fetchone.return_value = None
  mock_cur.fetchall.return_value = []
  try:
    with pytest.raises(db.Error, match='not found'):
      db.ResolveStationCode('nonexistent')
  finally:
    db._pool = None


def test_fragment_ambiguous() -> None:
  """Test."""
  _, mock_cur = setup_pool()
  mock_cur.fetchone.return_value = None
  mock_cur.fetchall.return_value = [{'code': 'MHIDE'}, {'code': 'MLNGR'}]
  try:
    with pytest.raises(db.Error, match='ambiguous'):
      db.ResolveStationCode('mal')
  finally:
    db._pool = None


# ---------------------------------------------------------------------------
# fetch_station_board
# ---------------------------------------------------------------------------


def test_no_query_returns_empty_stations() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchone.return_value = None
  db._pool = mock_pool
  try:
    qd, lines = db.FetchStationBoard('MHIDE')
    assert qd is None
    assert lines == []
  finally:
    db._pool = None


def test_returns_query_and_lines() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchone.return_value = {
    'id': 1,
    'tm_server': datetime.datetime(2025, 6, 29, 9, 0, 0),  # noqa: DTZ001
    'tm_query_seconds': 33267,
    'station_name': 'Malahide',
    'station_code': 'MHIDE',
    'day': datetime.date(2025, 6, 29),
  }
  mock_cur.fetchall.return_value = [
    {
      'train_code': 'P702',
      'origin_code': 'BRAY',
      'origin_name': 'Bray',
      'destination_code': 'CENTJ',
      'destination_name': 'Dublin Connolly',
      'trip_arrival_seconds': 31500,
      'trip_departure_seconds': 35100,
      'direction': 'Southbound',
      'due_in_seconds': 9,
      'late': 5,
      'location_type': 0,
      'status': 'En Route',
      'train_type': 1,
      'last_location': None,
      'scheduled_arrival_seconds': 33720,
      'scheduled_departure_seconds': 33780,
      'expected_arrival_seconds': 33720,
      'expected_departure_seconds': 34020,
    },
  ]
  db._pool = mock_pool
  try:
    qd, lines = db.FetchStationBoard('MHIDE')
    assert qd is not None
    assert qd.station_code == 'MHIDE'
    assert len(lines) == 1
    assert lines[0].train_code == 'P702'
    assert lines[0].late == 5
  finally:
    db._pool = None


# ---------------------------------------------------------------------------
# fetch_train_movements
# ---------------------------------------------------------------------------


def test_no_query_returns_empty_trains() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchone.return_value = None
  db._pool = mock_pool
  try:
    qd, stops = db.FetchTrainMovements('E108', datetime.date(2025, 6, 29))
    assert qd is None
    assert stops == []
  finally:
    db._pool = None


def test_returns_query_and_stops() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchone.return_value = {
    'id': 42,
    'train_code': 'E108',
    'day': datetime.date(2025, 6, 29),
    'origin_code': 'MHIDE',
    'origin_name': 'Malahide',
    'destination_code': 'BRAY',
    'destination_name': 'Bray',
  }
  mock_cur.fetchall.return_value = [
    {
      'station_code': 'MHIDE',
      'station_name': 'Malahide',
      'station_order': 1,
      'location_type': 1,
      'stop_type': 0,
      'auto_arrival': True,
      'auto_depart': True,
      'scheduled_arrival_seconds': None,
      'scheduled_departure_seconds': 34200,
      'expected_arrival_seconds': None,
      'expected_departure_seconds': 34200,
      'actual_arrival_seconds': 33564,
      'actual_departure_seconds': 34224,
    },
  ]
  db._pool = mock_pool
  try:
    qd, stops = db.FetchTrainMovements('E108', datetime.date(2025, 6, 29))
    assert qd is not None
    assert qd.train_code == 'E108'
    assert len(stops) == 1
    assert stops[0].station_code == 'MHIDE'
    assert stops[0].station_order == 1
    assert stops[0].auto_arrival is True
  finally:
    db._pool = None


# ---------------------------------------------------------------------------
# UpsertStations
# ---------------------------------------------------------------------------


def test_upsert_stations_empty() -> None:
  """Test."""
  assert db.UpsertStations([]) == 0


def test_upsert_stations() -> None:
  """Test."""
  from tfinta import tfinta_base as base  # noqa: PLC0415

  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.rowcount = 2
  db._pool = mock_pool
  try:
    stations = [
      dm.Station(
        id=228,
        code='MHIDE',
        description='Malahide',
        location=base.Point(latitude=53.45, longitude=-6.16),
        alias=None,
      ),
      dm.Station(
        id=999,
        code='CENTJ',
        description='Central Junction',
        location=None,
        alias='Dublin Connolly',
      ),
    ]
    result = db.UpsertStations(stations)
    assert result == 2
    mock_cur.executemany.assert_called_once()
    args = mock_cur.executemany.call_args
    sql = args[0][0]
    params = args[0][1]
    assert 'INSERT INTO stations' in sql
    assert 'ON CONFLICT (code) DO UPDATE' in sql
    assert len(params) == 2
    assert params[0]['code'] == 'MHIDE'
    assert abs(params[0]['latitude'] - 53.45) < 1e-6
    assert params[1]['code'] == 'CENTJ'
    assert params[1]['latitude'] is None
    assert params[1]['alias'] == 'Dublin Connolly'
    mock_conn.commit.assert_called_once()
  finally:
    db._pool = None


# ---------------------------------------------------------------------------
# UpsertRunningTrains
# ---------------------------------------------------------------------------


def test_upsert_running_trains_empty() -> None:
  """Test."""
  assert db.UpsertRunningTrains([]) == 0


def test_upsert_running_trains() -> None:
  """Test."""
  from tfinta import tfinta_base as base  # noqa: PLC0415

  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.rowcount = 1
  db._pool = mock_pool
  try:
    trains = [
      dm.RunningTrain(
        code='A152',
        status=dm.TrainStatus.RUNNING,
        day=datetime.date(2025, 6, 29),
        direction='Northbound',
        message='A152\nRunning north',
        position=base.Point(latitude=54.0, longitude=-6.41),
      ),
    ]
    result = db.UpsertRunningTrains(trains)
    assert result == 1
    mock_cur.executemany.assert_called_once()
    args = mock_cur.executemany.call_args
    sql = args[0][0]
    params = args[0][1]
    assert 'INSERT INTO running_trains' in sql
    assert 'ON CONFLICT (code, day) DO UPDATE' in sql
    assert len(params) == 1
    assert params[0]['code'] == 'A152'
    assert params[0]['status'] == 2  # TrainStatus.RUNNING.value
    assert abs(params[0]['latitude'] - 54.0) < 1e-6
    mock_conn.commit.assert_called_once()
  finally:
    db._pool = None


def test_upsert_running_trains_no_position() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.rowcount = 1
  db._pool = mock_pool
  try:
    trains = [
      dm.RunningTrain(
        code='B200',
        status=dm.TrainStatus.NOT_YET_RUNNING,
        day=datetime.date(2025, 6, 29),
        direction='Southbound',
        message='B200\nNot yet running',
        position=None,
      ),
    ]
    result = db.UpsertRunningTrains(trains)
    assert result == 1
    params = mock_cur.executemany.call_args[0][1]
    assert params[0]['latitude'] is None
    assert params[0]['longitude'] is None
  finally:
    db._pool = None


# ---------------------------------------------------------------------------
# InsertStationBoard
# ---------------------------------------------------------------------------


def _make_query_data() -> dm.StationLineQueryData:
  """Build a sample StationLineQueryData.

  Returns:
    dm.StationLineQueryData: sample query data.

  """
  return dm.StationLineQueryData(
    tm_server=datetime.datetime(2025, 6, 29, 9, 0, 0),  # noqa: DTZ001
    tm_query=base.DayTime(time=33267),
    station_name='Malahide',
    station_code='MHIDE',
    day=datetime.date(2025, 6, 29),
  )


def _make_station_line(query: dm.StationLineQueryData) -> dm.StationLine:
  """Build a sample StationLine.

  Returns:
    dm.StationLine: sample station line.

  """
  return dm.StationLine(
    query=query,
    train_code='P702',
    origin_code='BRAY',
    origin_name='Bray',
    destination_code='CENTJ',
    destination_name='Dublin Connolly',
    trip=base.DayRange(
      arrival=base.DayTime(time=31500),
      departure=base.DayTime(time=35100),
      strict=False,
      nullable=True,
    ),
    direction='Southbound',
    due_in=base.DayTime(time=9),
    late=5,
    location_type=dm.LocationType.STOP,
    status='En Route',
    train_type=dm.TrainType.DMU,
    last_location=None,
    scheduled=base.DayRange(
      arrival=base.DayTime(time=33720),
      departure=base.DayTime(time=33780),
      nullable=True,
    ),
    expected=base.DayRange(
      arrival=base.DayTime(time=33720),
      departure=base.DayTime(time=34020),
      nullable=True,
    ),
  )


def test_insert_station_board_no_lines() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchone.return_value = {'id': 42}
  db._pool = mock_pool
  try:
    qd = _make_query_data()
    result = db.InsertStationBoard(qd, [])
    assert result == 42
    # Query INSERT was called
    assert mock_cur.execute.call_count == 1
    sql = mock_cur.execute.call_args[0][0]
    assert 'INSERT INTO station_board_queries' in sql
    assert 'RETURNING id' in sql
    # No executemany for lines
    mock_cur.executemany.assert_not_called()
    mock_conn.commit.assert_called_once()
  finally:
    db._pool = None


def test_insert_station_board_with_lines() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchone.return_value = {'id': 42}
  db._pool = mock_pool
  try:
    qd = _make_query_data()
    line = _make_station_line(qd)
    result = db.InsertStationBoard(qd, [line])
    assert result == 42
    # Lines INSERT
    mock_cur.executemany.assert_called_once()
    line_args = mock_cur.executemany.call_args
    line_sql = line_args[0][0]
    line_params = line_args[0][1]
    assert 'INSERT INTO station_board_lines' in line_sql
    assert len(line_params) == 1
    assert line_params[0]['query_id'] == 42
    assert line_params[0]['train_code'] == 'P702'
    assert line_params[0]['late'] == 5
    assert line_params[0]['location_type'] == 0  # LocationType.STOP.value
    assert line_params[0]['train_type'] == 1  # TrainType.DMU.value
    assert line_params[0]['trip_arrival_seconds'] == 31500
    assert line_params[0]['scheduled_arrival_seconds'] == 33720
    assert line_params[0]['expected_departure_seconds'] == 34020
    mock_conn.commit.assert_called_once()
  finally:
    db._pool = None


# ---------------------------------------------------------------------------
# InsertTrainMovements
# ---------------------------------------------------------------------------


def _make_train_query_data() -> dm.TrainStopQueryData:
  """Build a sample TrainStopQueryData.

  Returns:
    dm.TrainStopQueryData: sample query data.

  """
  return dm.TrainStopQueryData(
    train_code='E108',
    day=datetime.date(2025, 6, 29),
    origin_code='MHIDE',
    origin_name='Malahide',
    destination_code='BRAY',
    destination_name='Bray',
  )


def _make_train_stop(query: dm.TrainStopQueryData) -> dm.TrainStop:
  """Build a sample TrainStop.

  Returns:
    dm.TrainStop: sample train stop.

  """
  return dm.TrainStop(
    query=query,
    station_code='MHIDE',
    station_name='Malahide',
    station_order=1,
    location_type=dm.LocationType.ORIGIN,
    stop_type=dm.StopType.UNKNOWN,
    auto_arrival=True,
    auto_depart=True,
    scheduled=base.DayRange(
      arrival=None,
      departure=base.DayTime(time=34200),
      nullable=True,
    ),
    expected=base.DayRange(
      arrival=None,
      departure=base.DayTime(time=34200),
      nullable=True,
    ),
    actual=base.DayRange(
      arrival=base.DayTime(time=33564),
      departure=base.DayTime(time=34224),
      strict=False,
      nullable=True,
    ),
  )


def test_insert_train_movements_no_stops() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchone.return_value = {'id': 99}
  db._pool = mock_pool
  try:
    qd = _make_train_query_data()
    result = db.InsertTrainMovements(qd, [])
    assert result == 99
    assert mock_cur.execute.call_count == 1
    sql = mock_cur.execute.call_args[0][0]
    assert 'INSERT INTO train_movement_queries' in sql
    assert 'RETURNING id' in sql
    mock_cur.executemany.assert_not_called()
    mock_conn.commit.assert_called_once()
  finally:
    db._pool = None


def test_insert_train_movements_with_stops() -> None:
  """Test."""
  mock_pool = mock.MagicMock()
  mock_conn = mock_pool.connection.return_value.__enter__.return_value
  mock_cur = mock_conn.cursor.return_value.__enter__.return_value
  mock_cur.fetchone.return_value = {'id': 99}
  db._pool = mock_pool
  try:
    qd = _make_train_query_data()
    stop = _make_train_stop(qd)
    result = db.InsertTrainMovements(qd, [stop])
    assert result == 99
    # Stops INSERT
    mock_cur.executemany.assert_called_once()
    stop_args = mock_cur.executemany.call_args
    stop_sql = stop_args[0][0]
    stop_params = stop_args[0][1]
    assert 'INSERT INTO train_stops' in stop_sql
    assert len(stop_params) == 1
    assert stop_params[0]['query_id'] == 99
    assert stop_params[0]['station_code'] == 'MHIDE'
    assert stop_params[0]['station_order'] == 1
    assert stop_params[0]['location_type'] == 1  # LocationType.ORIGIN.value
    assert stop_params[0]['stop_type'] == 0  # StopType.UNKNOWN.value
    assert stop_params[0]['auto_arrival'] is True
    assert stop_params[0]['auto_depart'] is True
    assert stop_params[0]['scheduled_arrival_seconds'] is None
    assert stop_params[0]['scheduled_departure_seconds'] == 34200
    assert stop_params[0]['actual_arrival_seconds'] == 33564
    assert stop_params[0]['actual_departure_seconds'] == 34224
    mock_conn.commit.assert_called_once()
  finally:
    db._pool = None
