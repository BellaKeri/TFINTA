# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""db.py unittest - database helpers (all queries mocked, no real Postgres needed)."""

from __future__ import annotations

import datetime
from unittest import mock

import pytest

from tfinta import db
from tfinta import realtime_data_model as dm

# ---------------------------------------------------------------------------
# DayTime / DayRange helpers
# ---------------------------------------------------------------------------


def test_returns_none_for_none() -> None:
  """Test."""
  assert db._daytime(None) is None


def test_returns_daytime() -> None:
  """Test."""
  dt = db._daytime(3600)
  assert dt is not None
  assert dt.time == 3600


def test_returns_zero() -> None:
  """Test."""
  dt = db._daytime(0)
  assert dt is not None
  assert dt.time == 0


def test_nullable_both_none() -> None:
  """Test."""
  dr = db._dayrange(None, None, nullable=True)
  assert dr.arrival is None
  assert dr.departure is None


def test_with_values() -> None:
  """Test."""
  dr = db._dayrange(100, 200)
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
    db.get_pool()


@mock.patch('tfinta.db.psycopg_pool.ConnectionPool')
def test_open_pool_creates_pool(mock_pool_cls: mock.MagicMock) -> None:
  """Test."""
  db._pool = None
  pool = db.open_pool()
  assert pool is mock_pool_cls.return_value
  mock_pool_cls.assert_called_once()
  db.close_pool()  # cleanup


@mock.patch('tfinta.db.psycopg_pool.ConnectionPool')
def test_open_pool_idempotent(mock_pool_cls: mock.MagicMock) -> None:
  """Test."""
  db._pool = None
  p1 = db.open_pool()
  p2 = db.open_pool()
  assert p1 is p2
  mock_pool_cls.assert_called_once()
  db.close_pool()


def test_close_pool_idempotent() -> None:
  """Test."""
  db._pool = None
  db.close_pool()  # should not raise


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
    stations = db.fetch_stations()
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
    trains = db.fetch_running_trains()
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
    assert db.resolve_station_code('MHIDE') == 'MHIDE'
  finally:
    db._pool = None


def test_fragment_match_single() -> None:
  """Test."""
  _, mock_cur = setup_pool()
  # First fetchone (exact code) returns None, then fetchall for fragment
  mock_cur.fetchone.return_value = None
  mock_cur.fetchall.return_value = [{'code': 'MHIDE'}]
  try:
    assert db.resolve_station_code('malahide') == 'MHIDE'
  finally:
    db._pool = None


def test_fragment_no_match() -> None:
  """Test."""
  _, mock_cur = setup_pool()
  mock_cur.fetchone.return_value = None
  mock_cur.fetchall.return_value = []
  try:
    with pytest.raises(db.Error, match='not found'):
      db.resolve_station_code('nonexistent')
  finally:
    db._pool = None


def test_fragment_ambiguous() -> None:
  """Test."""
  _, mock_cur = setup_pool()
  mock_cur.fetchone.return_value = None
  mock_cur.fetchall.return_value = [{'code': 'MHIDE'}, {'code': 'MLNGR'}]
  try:
    with pytest.raises(db.Error, match='ambiguous'):
      db.resolve_station_code('mal')
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
    qd, lines = db.fetch_station_board('MHIDE')
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
    qd, lines = db.fetch_station_board('MHIDE')
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
    qd, stops = db.fetch_train_movements('E108', datetime.date(2025, 6, 29))
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
    qd, stops = db.fetch_train_movements('E108', datetime.date(2025, 6, 29))
    assert qd is not None
    assert qd.train_code == 'E108'
    assert len(stops) == 1
    assert stops[0].station_code == 'MHIDE'
    assert stops[0].station_order == 1
    assert stops[0].auto_arrival is True
  finally:
    db._pool = None
