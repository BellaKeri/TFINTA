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


def _connection_info() -> str:
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


def open_pool() -> psycopg_pool.ConnectionPool:
  """Create (or return) the shared connection pool.

  Returns:
    psycopg_pool.ConnectionPool: the pool.

  """
  global _pool  # noqa: PLW0603
  if _pool is None:
    _pool = psycopg_pool.ConnectionPool(
      conninfo=_connection_info(),
      min_size=int(os.environ.get('TFINTA_DB_MIN_CONN', '2')),
      max_size=int(os.environ.get('TFINTA_DB_MAX_CONN', '10')),
      kwargs={'row_factory': psycopg.rows.dict_row},
    )
  return _pool


def close_pool() -> None:
  """Close the shared connection pool (idempotent)."""
  global _pool  # noqa: PLW0603
  if _pool is not None:
    _pool.close()
    _pool = None


def get_pool() -> psycopg_pool.ConnectionPool:
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


def _daytime(seconds: int | None) -> base.DayTime | None:
  """Convert nullable seconds-since-midnight to ``DayTime``.

  Args:
    seconds: seconds since midnight, or ``None``.

  Returns:
    base.DayTime | None: daytime or None.

  """
  if seconds is None:
    return None
  return base.DayTime(time=seconds)


def _dayrange(
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
    arrival=_daytime(arrival_s),
    departure=_daytime(departure_s),
    strict=strict,
    nullable=nullable,
  )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def fetch_stations() -> list[dm.Station]:
  """SELECT all stations, ordered by description.

  Returns:
    list[dm.Station]: all stations.

  """
  pool = get_pool()
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


def fetch_running_trains() -> list[dm.RunningTrain]:
  """SELECT running trains for today (UTC), ordered by status DESC then code.

  Returns:
    list[dm.RunningTrain]: running trains.

  """
  pool = get_pool()
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


def resolve_station_code(code_or_fragment: str) -> str:
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
  pool = get_pool()
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


def fetch_station_board(
  station_code: str,
) -> tuple[dm.StationLineQueryData | None, list[dm.StationLine]]:
  """SELECT the latest station board for the given code.

  Returns the most recent query row and its associated lines.

  Args:
    station_code: 5-letter station code.

  Returns:
    tuple: (query_data or None, list of StationLine).

  """
  pool = get_pool()
  with pool.connection() as conn, conn.cursor() as cur:
    # Latest query for this station
    cur.execute(
      'SELECT id, tm_server, tm_query_seconds, station_name, station_code, day '
      'FROM station_board_queries '
      'WHERE station_code = %s '
      'ORDER BY fetched_at DESC LIMIT 1',
      (station_code,),
    )
    qrow = cur.fetchone()
    if qrow is None:
      return None, []

    query_data = dm.StationLineQueryData(
      tm_server=qrow['tm_server'],  # type: ignore[call-overload]
      tm_query=(
        base.DayTime(time=int(qrow['tm_query_seconds']))  # type: ignore[call-overload]
        if qrow['tm_query_seconds'] is not None  # type: ignore[call-overload]
        else base.DayTime(time=0)
      ),
      station_name=str(qrow['station_name']),  # type: ignore[call-overload]
      station_code=str(qrow['station_code']),  # type: ignore[call-overload]
      day=qrow['day'],  # type: ignore[call-overload]
    )
    query_id: int = int(qrow['id'])  # type: ignore[call-overload]

    # Lines for that query
    cur.execute(
      'SELECT train_code, origin_code, origin_name, destination_code, destination_name, '
      '  trip_arrival_seconds, trip_departure_seconds, direction, due_in_seconds, '
      '  late, location_type, status, train_type, last_location, '
      '  scheduled_arrival_seconds, scheduled_departure_seconds, '
      '  expected_arrival_seconds, expected_departure_seconds '
      'FROM station_board_lines '
      'WHERE query_id = %s '
      'ORDER BY due_in_seconds, expected_departure_seconds',
      (query_id,),
    )
    line_rows: list[dict[str, object]] = cur.fetchall()  # type: ignore[assignment]

  lines: list[dm.StationLine] = [
    dm.StationLine(
      query=query_data,
      train_code=str(lr['train_code']),
      origin_code=str(lr['origin_code']),
      origin_name=str(lr['origin_name']),
      destination_code=str(lr['destination_code']),
      destination_name=str(lr['destination_name']),
      trip=_dayrange(
        lr['trip_arrival_seconds'],  # type: ignore[arg-type]
        lr['trip_departure_seconds'],  # type: ignore[arg-type]
        strict=False,
        nullable=True,
      ),
      direction=str(lr['direction']),
      due_in=_daytime(lr['due_in_seconds'])  # type: ignore[arg-type]
      or base.DayTime(time=0),
      late=int(lr['late']),  # type: ignore[call-overload]
      location_type=dm.LocationType(int(lr['location_type'])),  # type: ignore[call-overload]
      status=str(lr['status']) if lr['status'] is not None else None,
      train_type=dm.TrainType(int(lr['train_type'])),  # type: ignore[call-overload]
      last_location=str(lr['last_location']) if lr['last_location'] is not None else None,
      scheduled=_dayrange(
        lr['scheduled_arrival_seconds'],  # type: ignore[arg-type]
        lr['scheduled_departure_seconds'],  # type: ignore[arg-type]
        nullable=True,
      ),
      expected=_dayrange(
        lr['expected_arrival_seconds'],  # type: ignore[arg-type]
        lr['expected_departure_seconds'],  # type: ignore[arg-type]
        nullable=True,
      ),
    )
    for lr in line_rows
  ]
  return query_data, lines


def fetch_train_movements(
  train_code: str, day: datetime.date
) -> tuple[dm.TrainStopQueryData | None, list[dm.TrainStop]]:
  """SELECT the latest train movements for the given code and day.

  Args:
    train_code: train code (e.g. ``E108``).
    day: journey date.

  Returns:
    tuple: (query_data or None, list of TrainStop).

  """
  pool = get_pool()
  with pool.connection() as conn, conn.cursor() as cur:
    # Latest query for this train + day
    cur.execute(
      'SELECT id, train_code, day, origin_code, origin_name, '
      '  destination_code, destination_name '
      'FROM train_movement_queries '
      'WHERE train_code = %s AND day = %s '
      'ORDER BY fetched_at DESC LIMIT 1',
      (train_code, day),
    )
    qrow = cur.fetchone()
    if qrow is None:
      return None, []

    query_data = dm.TrainStopQueryData(
      train_code=str(qrow['train_code']),  # type: ignore[call-overload]
      day=qrow['day'],  # type: ignore[call-overload]
      origin_code=str(qrow['origin_code']),  # type: ignore[call-overload]
      origin_name=str(qrow['origin_name']),  # type: ignore[call-overload]
      destination_code=str(qrow['destination_code']),  # type: ignore[call-overload]
      destination_name=str(qrow['destination_name']),  # type: ignore[call-overload]
    )
    query_id: int = int(qrow['id'])  # type: ignore[call-overload]

    # Stops
    cur.execute(
      'SELECT station_code, station_name, station_order, location_type, '
      '  stop_type, auto_arrival, auto_depart, '
      '  scheduled_arrival_seconds, scheduled_departure_seconds, '
      '  expected_arrival_seconds, expected_departure_seconds, '
      '  actual_arrival_seconds, actual_departure_seconds '
      'FROM train_stops '
      'WHERE query_id = %s '
      'ORDER BY station_order',
      (query_id,),
    )
    stop_rows: list[dict[str, object]] = cur.fetchall()  # type: ignore[assignment]

  stops: list[dm.TrainStop] = [
    dm.TrainStop(
      query=query_data,
      station_code=str(sr['station_code']),
      station_name=str(sr['station_name']) if sr['station_name'] is not None else None,
      station_order=int(sr['station_order']),  # type: ignore[call-overload]
      location_type=dm.LocationType(int(sr['location_type'])),  # type: ignore[call-overload]
      stop_type=dm.StopType(int(sr['stop_type'])),  # type: ignore[call-overload]
      auto_arrival=bool(sr['auto_arrival']),
      auto_depart=bool(sr['auto_depart']),
      scheduled=_dayrange(
        sr['scheduled_arrival_seconds'],  # type: ignore[arg-type]
        sr['scheduled_departure_seconds'],  # type: ignore[arg-type]
        nullable=True,
      ),
      expected=_dayrange(
        sr['expected_arrival_seconds'],  # type: ignore[arg-type]
        sr['expected_departure_seconds'],  # type: ignore[arg-type]
        nullable=True,
      ),
      actual=_dayrange(
        sr['actual_arrival_seconds'],  # type: ignore[arg-type]
        sr['actual_departure_seconds'],  # type: ignore[arg-type]
        strict=False,
        nullable=True,
      ),
    )
    for sr in stop_rows
  ]
  return query_data, stops
