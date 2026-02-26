# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""PostgreSQL connection pool and query helpers for TFINTA DB API.

Configuration is driven by environment variables:

- ``TFINTA_DB_HOST``     - default ``localhost``
- ``TFINTA_DB_PORT``     - default ``5432``
- ``TFINTA_DB_NAME``     - default ``tfinta``
- ``TFINTA_DB_USER``     - default ``tfinta``
- ``TFINTA_DB_PASSWORD`` - default ``tfinta``
- ``TFINTA_DB_MIN_CONN`` - minimum pool connections (default ``2``)
- ``TFINTA_DB_MAX_CONN`` - maximum pool connections (default ``10``)
"""

from __future__ import annotations

import datetime
import os

import psycopg
import psycopg.rows
import psycopg_pool

from . import realtime_data_model as dm
from . import tfinta_base as base

# ---------------------------------------------------------------------------
# Pool management
# ---------------------------------------------------------------------------


def _ConnectionInfo() -> str:
  """Build a libpq connection string from environment variables.

  Returns:
    str: PostgreSQL connection-info string.

  """
  return psycopg.conninfo.make_conninfo(  # type: ignore
    host=os.environ.get('TFINTA_DB_HOST', 'localhost'),
    port=int(os.environ.get('TFINTA_DB_PORT', '5432')),
    dbname=os.environ.get('TFINTA_DB_NAME', 'tfinta'),
    user=os.environ.get('TFINTA_DB_USER', 'tfinta'),
    password=os.environ.get('TFINTA_DB_PASSWORD', 'tfinta'),
  )


class Error(base.Error):
  """DB-layer exception."""


_pool: psycopg_pool.ConnectionPool | None = None


def OpenPool() -> psycopg_pool.ConnectionPool:
  """Create (or return) the shared connection pool.

  Returns:
    psycopg_pool.ConnectionPool: the pool.

  """
  global _pool  # noqa: PLW0603
  if _pool is None:
    _pool = psycopg_pool.ConnectionPool(
      conninfo=_ConnectionInfo(),
      min_size=int(os.environ.get('TFINTA_DB_MIN_CONN', '2')),
      max_size=int(os.environ.get('TFINTA_DB_MAX_CONN', '10')),
      kwargs={'row_factory': psycopg.rows.dict_row},
    )
  return _pool


def ClosePool() -> None:
  """Close the shared connection pool (idempotent)."""
  global _pool  # noqa: PLW0603
  if _pool is not None:
    _pool.close()
    _pool = None


def GetPool() -> psycopg_pool.ConnectionPool:
  """Return the pool, raising ``Error`` if not open.

  Returns:
    psycopg_pool.ConnectionPool: the pool.

  Raises:
    Error: if the pool has not been opened yet.

  """
  if _pool is None:
    raise Error('DB pool not initialized')
  return _pool


# ---------------------------------------------------------------------------
# Helper: seconds ↔ DayTime / DayRange
# ---------------------------------------------------------------------------


def _DayTime(seconds: int | None) -> base.DayTime | None:
  """Convert nullable seconds-since-midnight to ``DayTime``.

  Args:
    seconds: seconds since midnight, or ``None``.

  Returns:
    base.DayTime | None: daytime or None.

  """
  if seconds is None:
    return None
  return base.DayTime(time=seconds)


def _DayRange(
  arrival_s: int | None, departure_s: int | None, *, strict: bool = True, nullable: bool = True
) -> base.DayRange:
  """Build a ``DayRange`` from nullable arrival/departure seconds.

  Args:
    arrival_s: arrival seconds since midnight.
    departure_s: departure seconds since midnight.
    strict: enforce arrival <= departure.
    nullable: allow None values.

  Returns:
    base.DayRange: the range.

  """
  return base.DayRange(
    arrival=_DayTime(arrival_s),
    departure=_DayTime(departure_s),
    strict=strict,
    nullable=nullable,
  )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def FetchStations() -> list[dm.Station]:
  """SELECT all stations, ordered by description.

  Returns:
    list[dm.Station]: all stations.

  """
  pool = GetPool()
  with pool.connection() as conn, conn.cursor() as cur:
    cur.execute(
      'SELECT id, code, description, latitude, longitude, alias FROM stations ORDER BY description'
    )
    rows: list[dict[str, object]] = cur.fetchall()  # type: ignore[assignment]
  return [
    dm.Station(
      id=int(r['id']),  # type: ignore[call-overload]
      code=str(r['code']),
      description=str(r['description']),
      location=(
        base.Point(
          latitude=float(r['latitude']),  # type: ignore[arg-type]
          longitude=float(r['longitude']),  # type: ignore[arg-type]
        )
        if r['latitude'] is not None and r['longitude'] is not None
        else None
      ),
      alias=str(r['alias']) if r['alias'] is not None else None,
    )
    for r in rows
  ]


def FetchRunningTrains() -> list[dm.RunningTrain]:
  """SELECT running trains for today (UTC), ordered by status DESC then code.

  Returns:
    list[dm.RunningTrain]: running trains.

  """
  pool = GetPool()
  today: datetime.date = datetime.datetime.now(tz=datetime.UTC).date()
  with pool.connection() as conn, conn.cursor() as cur:
    cur.execute(
      'SELECT code, status, day, direction, message, latitude, longitude '
      'FROM running_trains WHERE day = %s '
      'ORDER BY status DESC, code',
      (today,),
    )
    rows: list[dict[str, object]] = cur.fetchall()  # type: ignore[assignment]
  return [
    dm.RunningTrain(
      code=str(r['code']),
      status=dm.TrainStatus(int(r['status'])),  # type: ignore[call-overload]
      day=r['day'],  # type: ignore[arg-type]
      direction=str(r['direction']),
      message=str(r['message']),
      position=(
        base.Point(
          latitude=float(r['latitude']),  # type: ignore[arg-type]
          longitude=float(r['longitude']),  # type: ignore[arg-type]
        )
        if r['latitude'] is not None and r['longitude'] is not None
        else None
      ),
    )
    for r in rows
  ]


def ResolveStationCode(code_or_fragment: str) -> str:
  """Look up station code by exact code or case-insensitive name/alias fragment.

  Mirrors ``RealtimeRail.StationCodeFromNameFragmentOrCode``.

  Args:
    code_or_fragment: station code or search fragment.

  Returns:
    str: resolved station code.

  Raises:
    Error: if not found or ambiguous.

  """
  code_or_fragment = code_or_fragment.strip()
  pool = GetPool()
  with pool.connection() as conn, conn.cursor() as cur:
    # 1. Try exact code match (case-insensitive)
    cur.execute('SELECT code FROM stations WHERE UPPER(code) = %s', (code_or_fragment.upper(),))
    row = cur.fetchone()
    if row is not None:
      return str(row['code'])  # type: ignore[call-overload]
    # 2. Fragment search in description and alias
    fragment = f'%{code_or_fragment.lower()}%'
    cur.execute(
      'SELECT code FROM stations WHERE LOWER(description) LIKE %s OR LOWER(alias) LIKE %s',
      (fragment, fragment),
    )
    matches: list[dict[str, object]] = cur.fetchall()  # type: ignore[assignment]
  if not matches:
    raise Error(f'station code/description {code_or_fragment!r} not found')
  if len(matches) > 1:
    codes = {str(m['code']) for m in matches}
    raise Error(f'station code/description {code_or_fragment!r} ambiguous, matches codes: {codes}')
  return str(matches[0]['code'])


def FetchStationBoardLines(station_code: str) -> list[dm.StationLine]:
  """SELECT station board lines for the given station code.

  Args:
    station_code: 5-letter station code.

  Returns:
    list[dm.StationLine]: station board lines, ordered by due_in then expected departure.

  """
  pool = GetPool()
  with pool.connection() as conn, conn.cursor() as cur:
    cur.execute(
      'SELECT train_code, origin_code, origin_name, destination_code, destination_name, '
      '  trip_arrival_seconds, trip_departure_seconds, direction, due_in_seconds, '
      '  late, location_type, status, train_type, last_location, '
      '  scheduled_arrival_seconds, scheduled_departure_seconds, '
      '  expected_arrival_seconds, expected_departure_seconds '
      'FROM station_board_lines '
      'WHERE station_code = %s '
      'ORDER BY due_in_seconds, expected_departure_seconds',
      (station_code,),
    )
    rows: list[dict[str, object]] = cur.fetchall()  # type: ignore[assignment]
  return [
    dm.StationLine(
      query=dm.StationLineQueryData(
        tm_server=datetime.datetime.now(tz=datetime.UTC),
        tm_query=base.DayTime(time=0),
        station_name='',
        station_code=station_code,
        day=datetime.datetime.now(tz=datetime.UTC).date(),
      ),
      train_code=str(lr['train_code']),
      origin_code=str(lr['origin_code']),
      origin_name=str(lr['origin_name']),
      destination_code=str(lr['destination_code']),
      destination_name=str(lr['destination_name']),
      trip=_DayRange(
        lr['trip_arrival_seconds'],  # type: ignore[arg-type]
        lr['trip_departure_seconds'],  # type: ignore[arg-type]
        strict=False,
        nullable=True,
      ),
      direction=str(lr['direction']),
      due_in=_DayTime(lr['due_in_seconds'])  # type: ignore[arg-type]
      or base.DayTime(time=0),
      late=int(lr['late']),  # type: ignore[call-overload]
      location_type=dm.LocationType(int(lr['location_type'])),  # type: ignore[call-overload]
      status=str(lr['status']) if lr['status'] is not None else None,
      train_type=dm.TrainType(int(lr['train_type'])),  # type: ignore[call-overload]
      last_location=str(lr['last_location']) if lr['last_location'] is not None else None,
      scheduled=_DayRange(
        lr['scheduled_arrival_seconds'],  # type: ignore[arg-type]
        lr['scheduled_departure_seconds'],  # type: ignore[arg-type]
        nullable=True,
      ),
      expected=_DayRange(
        lr['expected_arrival_seconds'],  # type: ignore[arg-type]
        lr['expected_departure_seconds'],  # type: ignore[arg-type]
        nullable=True,
      ),
    )
    for lr in rows
  ]


def FetchTrainStops(train_code: str, day: datetime.date) -> list[dm.TrainStop]:
  """SELECT train stops for the given train code and day.

  Args:
    train_code: train code (e.g. ``E108``).
    day: journey date.

  Returns:
    list[dm.TrainStop]: train stops, ordered by station_order.

  """
  pool = GetPool()
  with pool.connection() as conn, conn.cursor() as cur:
    cur.execute(
      'SELECT station_code, station_name, station_order, location_type, '
      '  stop_type, auto_arrival, auto_depart, '
      '  scheduled_arrival_seconds, scheduled_departure_seconds, '
      '  expected_arrival_seconds, expected_departure_seconds, '
      '  actual_arrival_seconds, actual_departure_seconds '
      'FROM train_stops '
      'WHERE train_code = %s AND day = %s '
      'ORDER BY station_order',
      (train_code, day),
    )
    rows: list[dict[str, object]] = cur.fetchall()  # type: ignore[assignment]
  return [
    dm.TrainStop(
      query=dm.TrainStopQueryData(
        train_code=train_code,
        day=day,
        origin_code='',
        origin_name='',
        destination_code='',
        destination_name='',
      ),
      station_code=str(sr['station_code']),
      station_name=str(sr['station_name']) if sr['station_name'] is not None else None,
      station_order=int(sr['station_order']),  # type: ignore[call-overload]
      location_type=dm.LocationType(int(sr['location_type'])),  # type: ignore[call-overload]
      stop_type=dm.StopType(int(sr['stop_type'])),  # type: ignore[call-overload]
      auto_arrival=bool(sr['auto_arrival']),
      auto_depart=bool(sr['auto_depart']),
      scheduled=_DayRange(
        sr['scheduled_arrival_seconds'],  # type: ignore[arg-type]
        sr['scheduled_departure_seconds'],  # type: ignore[arg-type]
        nullable=True,
      ),
      expected=_DayRange(
        sr['expected_arrival_seconds'],  # type: ignore[arg-type]
        sr['expected_departure_seconds'],  # type: ignore[arg-type]
        nullable=True,
      ),
      actual=_DayRange(
        sr['actual_arrival_seconds'],  # type: ignore[arg-type]
        sr['actual_departure_seconds'],  # type: ignore[arg-type]
        strict=False,
        nullable=True,
      ),
    )
    for sr in rows
  ]


# ---------------------------------------------------------------------------
# Inserts / Upserts
# ---------------------------------------------------------------------------


def UpsertStations(stations: list[dm.Station]) -> int:
  """INSERT or UPDATE stations (keyed by code).

  Uses ``ON CONFLICT (code) DO UPDATE`` so callers can blindly push the latest
  station list without worrying about duplicates.

  Args:
    stations: station objects to upsert.

  Returns:
    int: number of rows affected.

  """
  if not stations:
    return 0
  pool = GetPool()
  with pool.connection() as conn, conn.cursor() as cur:
    sql = (
      'INSERT INTO stations (id, code, description, latitude, longitude, alias, updated_at) '
      'VALUES (%(id)s, %(code)s, %(description)s, %(latitude)s, %(longitude)s, '
      '  %(alias)s, now()) '
      'ON CONFLICT (code) DO UPDATE SET '
      '  id = EXCLUDED.id, '
      '  description = EXCLUDED.description, '
      '  latitude = EXCLUDED.latitude, '
      '  longitude = EXCLUDED.longitude, '
      '  alias = EXCLUDED.alias, '
      '  updated_at = now()'
    )
    params = [
      {
        'id': s.id,
        'code': s.code,
        'description': s.description,
        'latitude': s.location.latitude if s.location else None,
        'longitude': s.location.longitude if s.location else None,
        'alias': s.alias,
      }
      for s in stations
    ]
    cur.executemany(sql, params)
    count: int = cur.rowcount
    conn.commit()
  return count


def UpsertRunningTrains(trains: list[dm.RunningTrain]) -> int:
  """INSERT or UPDATE running trains (keyed by code).

  Args:
    trains: running train objects to upsert.

  Returns:
    int: number of rows affected.

  """
  if not trains:
    return 0
  pool = GetPool()
  with pool.connection() as conn, conn.cursor() as cur:
    sql = (
      'INSERT INTO running_trains '
      '  (code, status, day, direction, message, latitude, longitude, updated_at) '
      'VALUES (%(code)s, %(status)s, %(day)s, %(direction)s, %(message)s, '
      '  %(latitude)s, %(longitude)s, now()) '
      'ON CONFLICT (code) DO UPDATE SET '
      '  status = EXCLUDED.status, '
      '  day = EXCLUDED.day, '
      '  direction = EXCLUDED.direction, '
      '  message = EXCLUDED.message, '
      '  latitude = EXCLUDED.latitude, '
      '  longitude = EXCLUDED.longitude, '
      '  updated_at = now()'
    )
    params = [
      {
        'code': t.code,
        'status': t.status.value,
        'day': t.day,
        'direction': t.direction,
        'message': t.message,
        'latitude': t.position.latitude if t.position else None,
        'longitude': t.position.longitude if t.position else None,
      }
      for t in trains
    ]
    cur.executemany(sql, params)
    count: int = cur.rowcount
    conn.commit()
  return count


def UpsertStationBoardLines(station_code: str, lines: list[dm.StationLine]) -> int:
  """INSERT or UPDATE station board lines (keyed by station_code + train_code).

  Replaces all lines for the given station atomically: deletes existing rows
  then inserts fresh ones inside a single transaction.

  Args:
    station_code: 5-letter station code.
    lines: station board line objects to upsert.

  Returns:
    int: number of rows inserted.

  """
  pool = GetPool()
  with pool.connection() as conn, conn.cursor() as cur:
    # Delete existing lines for this station and re-insert
    cur.execute('DELETE FROM station_board_lines WHERE station_code = %s', (station_code,))
    if not lines:
      conn.commit()
      return 0
    sql = (
      'INSERT INTO station_board_lines '
      '  (station_code, train_code, origin_code, origin_name, '
      '   destination_code, destination_name, '
      '   trip_arrival_seconds, trip_departure_seconds, direction, '
      '   due_in_seconds, late, location_type, status, train_type, '
      '   last_location, scheduled_arrival_seconds, scheduled_departure_seconds, '
      '   expected_arrival_seconds, expected_departure_seconds, updated_at) '
      'VALUES (%(station_code)s, %(train_code)s, %(origin_code)s, %(origin_name)s, '
      '  %(destination_code)s, %(destination_name)s, '
      '  %(trip_arrival_seconds)s, %(trip_departure_seconds)s, %(direction)s, '
      '  %(due_in_seconds)s, %(late)s, %(location_type)s, %(status)s, '
      '  %(train_type)s, %(last_location)s, '
      '  %(scheduled_arrival_seconds)s, %(scheduled_departure_seconds)s, '
      '  %(expected_arrival_seconds)s, %(expected_departure_seconds)s, now())'
    )
    params = [
      {
        'station_code': station_code,
        'train_code': ln.train_code,
        'origin_code': ln.origin_code,
        'origin_name': ln.origin_name,
        'destination_code': ln.destination_code,
        'destination_name': ln.destination_name,
        'trip_arrival_seconds': ln.trip.arrival.time if ln.trip.arrival else None,
        'trip_departure_seconds': ln.trip.departure.time if ln.trip.departure else None,
        'direction': ln.direction,
        'due_in_seconds': ln.due_in.time,
        'late': ln.late,
        'location_type': ln.location_type.value,
        'status': ln.status,
        'train_type': ln.train_type.value,
        'last_location': ln.last_location,
        'scheduled_arrival_seconds': (ln.scheduled.arrival.time if ln.scheduled.arrival else None),
        'scheduled_departure_seconds': (
          ln.scheduled.departure.time if ln.scheduled.departure else None
        ),
        'expected_arrival_seconds': (ln.expected.arrival.time if ln.expected.arrival else None),
        'expected_departure_seconds': (
          ln.expected.departure.time if ln.expected.departure else None
        ),
      }
      for ln in lines
    ]
    cur.executemany(sql, params)
    count: int = cur.rowcount
    conn.commit()
  return count


def UpsertTrainStops(train_code: str, day: datetime.date, stops: list[dm.TrainStop]) -> int:
  """INSERT or UPDATE train stops (keyed by train_code + day + station_order).

  Replaces all stops for the given train/day atomically: deletes existing rows
  then inserts fresh ones inside a single transaction.

  Args:
    train_code: train code (e.g. ``E108``).
    day: journey date.
    stops: train stop objects to upsert.

  Returns:
    int: number of rows inserted.

  """
  pool = GetPool()
  with pool.connection() as conn, conn.cursor() as cur:
    # Delete existing stops for this train+day and re-insert
    cur.execute('DELETE FROM train_stops WHERE train_code = %s AND day = %s', (train_code, day))
    if not stops:
      conn.commit()
      return 0
    sql = (
      'INSERT INTO train_stops '
      '  (train_code, day, station_code, station_name, station_order, location_type, '
      '   stop_type, auto_arrival, auto_depart, '
      '   scheduled_arrival_seconds, scheduled_departure_seconds, '
      '   expected_arrival_seconds, expected_departure_seconds, '
      '   actual_arrival_seconds, actual_departure_seconds, updated_at) '
      'VALUES (%(train_code)s, %(day)s, %(station_code)s, %(station_name)s, %(station_order)s, '
      '  %(location_type)s, %(stop_type)s, %(auto_arrival)s, %(auto_depart)s, '
      '  %(scheduled_arrival_seconds)s, %(scheduled_departure_seconds)s, '
      '  %(expected_arrival_seconds)s, %(expected_departure_seconds)s, '
      '  %(actual_arrival_seconds)s, %(actual_departure_seconds)s, now())'
    )
    params = [
      {
        'train_code': train_code,
        'day': day,
        'station_code': s.station_code,
        'station_name': s.station_name,
        'station_order': s.station_order,
        'location_type': s.location_type.value,
        'stop_type': s.stop_type.value,
        'auto_arrival': s.auto_arrival,
        'auto_depart': s.auto_depart,
        'scheduled_arrival_seconds': (s.scheduled.arrival.time if s.scheduled.arrival else None),
        'scheduled_departure_seconds': (
          s.scheduled.departure.time if s.scheduled.departure else None
        ),
        'expected_arrival_seconds': (s.expected.arrival.time if s.expected.arrival else None),
        'expected_departure_seconds': (s.expected.departure.time if s.expected.departure else None),
        'actual_arrival_seconds': (s.actual.arrival.time if s.actual.arrival else None),
        'actual_departure_seconds': (s.actual.departure.time if s.actual.departure else None),
      }
      for s in stops
    ]
    cur.executemany(sql, params)
    count: int = cur.rowcount
    conn.commit()
  return count
