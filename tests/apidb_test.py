# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""apidb.py unittest - DB-backed API endpoints.

All database calls are mocked via ``unittest.mock.patch`` on the ``db`` module
functions, so no real PostgreSQL instance is needed.
"""

from __future__ import annotations

import collections.abc
import datetime
from unittest import mock

import pytest
from fastapi import testclient

from tfinta import __version__, apidb, db
from tfinta import realtime_data_model as dm
from tfinta import tfinta_base as base

# ---------------------------------------------------------------------------
# Minimal domain objects reused across test cases
# ---------------------------------------------------------------------------

_STATION = dm.Station(
  id=228,
  code='MHIDE',
  description='Malahide',
  location=base.Point(latitude=53.45, longitude=-6.16),
  alias=None,
)
_STATION_NO_LOCATION = dm.Station(
  id=999,
  code='CENTJ',
  description='Central Junction',
  location=None,
  alias='Dublin Connolly',
)

_RUNNING_TRAIN = dm.RunningTrain(
  code='A152',
  status=dm.TrainStatus.RUNNING,
  day=datetime.date(2025, 6, 29),
  direction='Northbound',
  message='A152\nRunning north',
  position=base.Point(latitude=54.0, longitude=-6.41),
)
_RUNNING_TRAIN_NO_POS = dm.RunningTrain(
  code='A407',
  status=dm.TrainStatus.NOT_YET_RUNNING,
  day=datetime.date(2025, 6, 29),
  direction='Southbound',
  message='A407\nNot yet',
  position=None,
)

_STATION_QUERY = dm.StationLineQueryData(
  tm_server=datetime.datetime(2025, 6, 29, 9, 0, 0),  # noqa: DTZ001
  tm_query=base.DayTime(time=33267),
  station_name='Malahide',
  station_code='MHIDE',
  day=datetime.date(2025, 6, 29),
)
_STATION_LINE = dm.StationLine(
  query=_STATION_QUERY,
  train_code='P702',
  origin_code='BRAY',
  origin_name='Bray',
  destination_code='CENTJ',
  destination_name='Dublin Connolly',
  trip=base.DayRange(arrival=base.DayTime(time=31500), departure=base.DayTime(time=35100)),
  direction='Southbound',
  due_in=base.DayTime(time=9),
  late=5,
  location_type=dm.LocationType.STOP,
  status='En Route',
  scheduled=base.DayRange(
    arrival=base.DayTime(time=33720),
    departure=base.DayTime(time=33780),
    nullable=True,
  ),
  expected=base.DayRange(
    arrival=base.DayTime(time=33720),
    departure=base.DayTime(time=34020),
    nullable=True,
    strict=False,
  ),
  train_type=dm.TrainType.DMU,
)

_TRAIN_QUERY = dm.TrainStopQueryData(
  train_code='E108',
  day=datetime.date(2025, 6, 29),
  origin_code='MHIDE',
  origin_name='Malahide',
  destination_code='BRAY',
  destination_name='Bray',
)
_TRAIN_STOP = dm.TrainStop(
  query=_TRAIN_QUERY,
  auto_arrival=True,
  auto_depart=True,
  location_type=dm.LocationType.ORIGIN,
  stop_type=dm.StopType.UNKNOWN,
  station_order=1,
  station_code='MHIDE',
  station_name='Malahide',
  scheduled=base.DayRange(arrival=None, departure=base.DayTime(time=34200), nullable=True),
  expected=base.DayRange(
    arrival=None, departure=base.DayTime(time=34200), nullable=True, strict=False
  ),
  actual=base.DayRange(
    arrival=base.DayTime(time=33564),
    departure=base.DayTime(time=34224),
    nullable=True,
  ),
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> collections.abc.Generator[testclient.TestClient, None, None]:
  """testclient.TestClient with DB pool mocked out.

  Yields:
    Configured testclient.TestClient for use in tests.

  """
  with (
    mock.patch('tfinta.db.OpenPool'),
    mock.patch('tfinta.db.ClosePool'),
    testclient.TestClient(apidb.app) as c,
  ):
    yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client: testclient.TestClient) -> None:
  """GET /health returns 200 with status=ok and the current version + '-db'."""
  resp = client.get('/health')
  assert resp.status_code == 200
  body = resp.json()
  assert body['status'] == 'ok'
  assert body['version'] == __version__ + '-db'


# ---------------------------------------------------------------------------
# /stations
# ---------------------------------------------------------------------------


@mock.patch('tfinta.db.FetchStations')
def test_get_stations_success(mock_fetch: mock.MagicMock, client: testclient.TestClient) -> None:
  """GET /stations returns 200 and serialises every station."""
  mock_fetch.return_value = [_STATION, _STATION_NO_LOCATION]
  resp = client.get('/stations')
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 2
  assert len(body['stations']) == 2
  first = body['stations'][0]
  assert first['code'] == 'MHIDE'
  assert first['id'] == 228
  assert first['description'] == 'Malahide'
  assert first['location'] == {'latitude': 53.45, 'longitude': -6.16}
  assert first['alias'] is None
  second = body['stations'][1]
  assert second['location'] is None
  assert second['alias'] == 'Dublin Connolly'
  mock_fetch.assert_called_once_with()


@mock.patch('tfinta.db.FetchStations')
def test_get_stations_empty(mock_fetch: mock.MagicMock, client: testclient.TestClient) -> None:
  """GET /stations returns 200 with count=0 when there are no stations."""
  mock_fetch.return_value = []
  resp = client.get('/stations')
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 0
  assert body['stations'] == []


@mock.patch('tfinta.db.FetchStations')
def test_get_stations_db_error(mock_fetch: mock.MagicMock, client: testclient.TestClient) -> None:
  """GET /stations returns 502 when db raises Error."""
  mock_fetch.side_effect = db.Error('connection refused')
  resp = client.get('/stations')
  assert resp.status_code == 502
  assert 'connection refused' in resp.json()['detail']


# ---------------------------------------------------------------------------
# /running
# ---------------------------------------------------------------------------


@mock.patch('tfinta.db.FetchRunningTrains')
def test_get_running_trains_success(
  mock_fetch: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /running returns 200 and serialises every running train."""
  mock_fetch.return_value = [_RUNNING_TRAIN, _RUNNING_TRAIN_NO_POS]
  resp = client.get('/running')
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 2
  assert len(body['trains']) == 2
  first = body['trains'][0]
  assert first['code'] == 'A152'
  assert first['status'] == 'RUNNING'
  assert first['day'] == '2025-06-29'
  assert first['direction'] == 'Northbound'
  assert first['position'] == {'latitude': 54.0, 'longitude': -6.41}
  second = body['trains'][1]
  assert second['status'] == 'NOT_YET_RUNNING'
  assert second['position'] is None
  mock_fetch.assert_called_once_with()


@mock.patch('tfinta.db.FetchRunningTrains')
def test_get_running_trains_empty(
  mock_fetch: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /running returns 200 with count=0 when no trains are running."""
  mock_fetch.return_value = []
  resp = client.get('/running')
  assert resp.status_code == 200
  assert resp.json() == {'count': 0, 'trains': []}


@mock.patch('tfinta.db.FetchRunningTrains')
def test_get_running_trains_db_error(
  mock_fetch: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /running returns 502 when db raises Error."""
  mock_fetch.side_effect = db.Error('pool exhausted')
  resp = client.get('/running')
  assert resp.status_code == 502
  assert 'pool exhausted' in resp.json()['detail']


# ---------------------------------------------------------------------------
# /station/{station_code}
# ---------------------------------------------------------------------------


@mock.patch('tfinta.db.FetchStationBoard')
@mock.patch('tfinta.db.ResolveStationCode')
def test_get_station_board_success(
  mock_resolve: mock.MagicMock, mock_board: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /station/MHIDE returns 200 and serialises query + lines."""
  mock_resolve.return_value = 'MHIDE'
  mock_board.return_value = (_STATION_QUERY, [_STATION_LINE])
  resp = client.get('/station/MHIDE')
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 1
  assert len(body['lines']) == 1
  query = body['query']
  assert query['station_code'] == 'MHIDE'
  assert query['station_name'] == 'Malahide'
  line = body['lines'][0]
  assert line['train_code'] == 'P702'
  assert line['origin_code'] == 'BRAY'
  assert line['destination_code'] == 'CENTJ'
  assert line['late'] == 5
  assert line['location_type'] == 'STOP'
  assert line['train_type'] == 'DMU'
  mock_resolve.assert_called_once_with('MHIDE')
  mock_board.assert_called_once_with('MHIDE')


@mock.patch('tfinta.db.FetchStationBoard')
@mock.patch('tfinta.db.ResolveStationCode')
def test_get_station_board_name_fragment(
  mock_resolve: mock.MagicMock, mock_board: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /station/malahide resolves the name fragment."""
  mock_resolve.return_value = 'MHIDE'
  mock_board.return_value = (_STATION_QUERY, [_STATION_LINE])
  resp = client.get('/station/malahide')
  assert resp.status_code == 200
  mock_resolve.assert_called_once_with('malahide')
  mock_board.assert_called_once_with('MHIDE')


@mock.patch('tfinta.db.FetchStationBoard')
@mock.patch('tfinta.db.ResolveStationCode')
def test_get_station_board_empty(
  mock_resolve: mock.MagicMock, mock_board: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /station/MHIDE returns 200 with count=0 and no query when board is empty."""
  mock_resolve.return_value = 'MHIDE'
  mock_board.return_value = (None, [])
  resp = client.get('/station/MHIDE')
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 0
  assert body['lines'] == []
  assert body['query'] is None


@mock.patch('tfinta.db.ResolveStationCode')
def test_get_station_board_resolve_error(
  mock_resolve: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /station/unknown returns 502 when station code/fragment can't be resolved."""
  mock_resolve.side_effect = db.Error('not found')
  resp = client.get('/station/unknown')
  assert resp.status_code == 502
  assert 'not found' in resp.json()['detail']


@mock.patch('tfinta.db.FetchStationBoard')
@mock.patch('tfinta.db.ResolveStationCode')
def test_get_station_board_call_error(
  mock_resolve: mock.MagicMock, mock_board: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /station/MHIDE returns 502 when fetch_station_board raises Error."""
  mock_resolve.return_value = 'MHIDE'
  mock_board.side_effect = db.Error('board unavailable')
  resp = client.get('/station/MHIDE')
  assert resp.status_code == 502


# ---------------------------------------------------------------------------
# /train/{train_code}
# ---------------------------------------------------------------------------


@mock.patch('tfinta.db.FetchTrainMovements')
def test_get_train_movements_success_explicit_day(
  mock_fetch: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /train/E108?day=20250629 returns 200 and serialises query + stops."""
  mock_fetch.return_value = (_TRAIN_QUERY, [_TRAIN_STOP])
  resp = client.get('/train/E108', params={'day': 20250629})
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 1
  assert len(body['stops']) == 1
  query = body['query']
  assert query['train_code'] == 'E108'
  assert query['origin_code'] == 'MHIDE'
  assert query['destination_code'] == 'BRAY'
  stop = body['stops'][0]
  assert stop['station_code'] == 'MHIDE'
  assert stop['station_name'] == 'Malahide'
  assert stop['station_order'] == 1
  assert stop['location_type'] == 'ORIGIN'
  assert stop['stop_type'] == 'UNKNOWN'
  assert stop['auto_arrival'] is True
  assert stop['auto_depart'] is True
  mock_fetch.assert_called_once_with('E108', datetime.date(2025, 6, 29))


@mock.patch('tfinta.db.FetchTrainMovements')
def test_get_train_movements_default_day(
  mock_fetch: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /train/E108 (no day param) defaults to today (UTC)."""
  fixed_date = datetime.date(2026, 2, 20)
  mock_fetch.return_value = (None, [])
  with mock.patch('tfinta.apidb.datetime') as mock_dt:
    mock_dt.UTC = datetime.UTC
    mock_dt.date = datetime.date
    mock_dt.datetime.now.return_value.date.return_value = fixed_date
    resp = client.get('/train/E108')
  assert resp.status_code == 200
  mock_fetch.assert_called_once_with('E108', fixed_date)


@mock.patch('tfinta.db.FetchTrainMovements')
def test_get_train_movements_empty(
  mock_fetch: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /train/E108?day=20250629 returns 200/count=0 when no movements."""
  mock_fetch.return_value = (None, [])
  resp = client.get('/train/E108', params={'day': 20250629})
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 0
  assert body['stops'] == []
  assert body['query'] is None


@mock.patch('tfinta.db.FetchTrainMovements')
def test_get_train_movements_db_error(
  mock_fetch: mock.MagicMock, client: testclient.TestClient
) -> None:
  """GET /train/E108 returns 502 when fetch_train_movements raises Error."""
  mock_fetch.side_effect = db.Error('train not found')
  resp = client.get('/train/E108', params={'day': 20250629})
  assert resp.status_code == 502
  assert 'train not found' in resp.json()['detail']


def test_get_train_movements_day_out_of_range(client: testclient.TestClient) -> None:
  """GET /train/E108?day=19991231 returns 422 (day below minimum)."""
  resp = client.get('/train/E108', params={'day': 19991231})
  assert resp.status_code == 422


def test_get_train_movements_day_above_max(client: testclient.TestClient) -> None:
  """GET /train/E108?day=22000101 returns 422 (day above maximum)."""
  resp = client.get('/train/E108', params={'day': 22000101})
  assert resp.status_code == 422


# ---------------------------------------------------------------------------
# OpenAPI metadata
# ---------------------------------------------------------------------------


def test_openapi_schema(client: testclient.TestClient) -> None:
  """GET /openapi.json returns 200 with the expected title and all routes present."""
  resp = client.get('/openapi.json')
  assert resp.status_code == 200
  schema = resp.json()
  assert schema['info']['title'] == 'TFINTA Realtime SQL-DB API'
  assert schema['info']['version'] == __version__ + '-db'
  paths = schema['paths']
  assert '/health' in paths
  assert '/stations' in paths
  assert '/running' in paths
  assert '/station/{station_code}' in paths
  assert '/train/{train_code}' in paths


def test_openapi_operation_ids(client: testclient.TestClient) -> None:
  """Every route exposes a clean operationId."""
  resp = client.get('/openapi.json')
  assert resp.status_code == 200
  paths = resp.json()['paths']
  assert paths['/health']['get']['operationId'] == 'health'
  assert paths['/stations']['get']['operationId'] == 'getStations'
  assert paths['/running']['get']['operationId'] == 'getRunningTrains'
  assert paths['/station/{station_code}']['get']['operationId'] == 'getStationBoard'
  assert paths['/train/{train_code}']['get']['operationId'] == 'getTrainMovements'


def test_docs_endpoint(client: testclient.TestClient) -> None:
  """GET /docs returns 200 (Swagger UI is served)."""
  resp = client.get('/docs')
  assert resp.status_code == 200


def test_redoc_endpoint(client: testclient.TestClient) -> None:
  """GET /redoc returns 200 (ReDoc UI is served)."""
  resp = client.get('/redoc')
  assert resp.status_code == 200
