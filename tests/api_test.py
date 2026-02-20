# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""api.py unittest."""

from __future__ import annotations

import collections.abc
import datetime
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from tfinta import __version__, api, realtime
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
def rt_mock() -> mock.MagicMock:
  """Return a fresh MagicMock specced as RealtimeRail.

  Returns:
    MagicMock with RealtimeRail spec.

  """
  return mock.MagicMock(spec=realtime.RealtimeRail)


@pytest.fixture
def client(rt_mock: mock.MagicMock) -> collections.abc.Generator[TestClient, None, None]:
  """TestClient with the lifespan triggered and RealtimeRail replaced by rt_mock.

  Yields:
    Configured TestClient for use in tests.

  """
  with (
    mock.patch('tfinta.api.realtime.RealtimeRail', return_value=rt_mock),
    TestClient(api.app) as c,
  ):
    yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
  """GET /health returns 200 with status=ok and the current version."""
  resp = client.get('/health')
  assert resp.status_code == 200
  body = resp.json()
  assert body['status'] == 'ok'
  assert body['version'] == __version__


# ---------------------------------------------------------------------------
# /stations
# ---------------------------------------------------------------------------


def test_get_stations_success(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /stations returns 200 and serialises every station."""
  rt_mock.StationsCall.return_value = [_STATION, _STATION_NO_LOCATION]
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
  rt_mock.StationsCall.assert_called_once_with()


def test_get_stations_empty(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /stations returns 200 with count=0 when there are no stations."""
  rt_mock.StationsCall.return_value = []
  resp = client.get('/stations')
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 0
  assert body['stations'] == []


def test_get_stations_upstream_error(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /stations returns 502 when RealtimeRail raises Error."""
  rt_mock.StationsCall.side_effect = realtime.Error('upstream failure')
  resp = client.get('/stations')
  assert resp.status_code == 502
  assert 'upstream failure' in resp.json()['detail']


# ---------------------------------------------------------------------------
# /running
# ---------------------------------------------------------------------------


def test_get_running_trains_success(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /running returns 200 and serialises every running train."""
  rt_mock.RunningTrainsCall.return_value = [_RUNNING_TRAIN, _RUNNING_TRAIN_NO_POS]
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
  rt_mock.RunningTrainsCall.assert_called_once_with()


def test_get_running_trains_empty(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /running returns 200 with count=0 when no trains are running."""
  rt_mock.RunningTrainsCall.return_value = []
  resp = client.get('/running')
  assert resp.status_code == 200
  assert resp.json() == {'count': 0, 'trains': []}


def test_get_running_trains_upstream_error(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /running returns 502 when RealtimeRail raises Error."""
  rt_mock.RunningTrainsCall.side_effect = realtime.Error('network glitch')
  resp = client.get('/running')
  assert resp.status_code == 502
  assert 'network glitch' in resp.json()['detail']


# ---------------------------------------------------------------------------
# /station/{station_code}
# ---------------------------------------------------------------------------


def test_get_station_board_success(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /station/MHIDE returns 200 and serialises query + lines."""
  rt_mock.StationCodeFromNameFragmentOrCode.return_value = 'MHIDE'
  rt_mock.StationBoardCall.return_value = (_STATION_QUERY, [_STATION_LINE])
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
  rt_mock.StationCodeFromNameFragmentOrCode.assert_called_once_with('MHIDE')
  rt_mock.StationBoardCall.assert_called_once_with('MHIDE')


def test_get_station_board_name_fragment(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /station/malahide resolves the name fragment via StationCodeFromNameFragmentOrCode."""
  rt_mock.StationCodeFromNameFragmentOrCode.return_value = 'MHIDE'
  rt_mock.StationBoardCall.return_value = (_STATION_QUERY, [_STATION_LINE])
  resp = client.get('/station/malahide')
  assert resp.status_code == 200
  rt_mock.StationCodeFromNameFragmentOrCode.assert_called_once_with('malahide')
  rt_mock.StationBoardCall.assert_called_once_with('MHIDE')


def test_get_station_board_empty(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /station/MHIDE returns 200 with count=0 and no query when board is empty."""
  rt_mock.StationCodeFromNameFragmentOrCode.return_value = 'MHIDE'
  rt_mock.StationBoardCall.return_value = (None, [])
  resp = client.get('/station/MHIDE')
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 0
  assert body['lines'] == []
  assert body['query'] is None


def test_get_station_board_resolve_error(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /station/unknown returns 502 when station code/fragment can't be resolved."""
  rt_mock.StationCodeFromNameFragmentOrCode.side_effect = realtime.Error('not found')
  resp = client.get('/station/unknown')
  assert resp.status_code == 502
  assert 'not found' in resp.json()['detail']


def test_get_station_board_call_error(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /station/MHIDE returns 502 when StationBoardCall raises Error."""
  rt_mock.StationCodeFromNameFragmentOrCode.return_value = 'MHIDE'
  rt_mock.StationBoardCall.side_effect = realtime.Error('board unavailable')
  resp = client.get('/station/MHIDE')
  assert resp.status_code == 502


# ---------------------------------------------------------------------------
# /train/{train_code}
# ---------------------------------------------------------------------------


def test_get_train_movements_success_explicit_day(
  client: TestClient, rt_mock: mock.MagicMock
) -> None:
  """GET /train/E108?day=20250629 returns 200 and serialises query + stops."""
  rt_mock.TrainDataCall.return_value = (_TRAIN_QUERY, [_TRAIN_STOP])
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
  rt_mock.TrainDataCall.assert_called_once_with('E108', datetime.date(2025, 6, 29))


def test_get_train_movements_default_day(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /train/E108 (no day param) defaults to today (UTC)."""
  fixed_date = datetime.date(2026, 2, 20)
  rt_mock.TrainDataCall.return_value = (None, [])
  with mock.patch('tfinta.api.datetime') as mock_dt:
    mock_dt.UTC = datetime.UTC
    mock_dt.date = datetime.date  # needed so typeguard can inspect the real type
    mock_dt.datetime.now.return_value.date.return_value = fixed_date
    resp = client.get('/train/E108')
  assert resp.status_code == 200
  rt_mock.TrainDataCall.assert_called_once_with('E108', fixed_date)


def test_get_train_movements_empty(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /train/E108?day=20250629 returns 200/count=0 when train has no movements."""
  rt_mock.TrainDataCall.return_value = (None, [])
  resp = client.get('/train/E108', params={'day': 20250629})
  assert resp.status_code == 200
  body = resp.json()
  assert body['count'] == 0
  assert body['stops'] == []
  assert body['query'] is None


def test_get_train_movements_upstream_error(client: TestClient, rt_mock: mock.MagicMock) -> None:
  """GET /train/E108 returns 502 when TrainDataCall raises Error."""
  rt_mock.TrainDataCall.side_effect = realtime.Error('train not found')
  resp = client.get('/train/E108', params={'day': 20250629})
  assert resp.status_code == 502
  assert 'train not found' in resp.json()['detail']


def test_get_train_movements_day_out_of_range(client: TestClient) -> None:
  """GET /train/E108?day=19991231 returns 422 (day below minimum)."""
  resp = client.get('/train/E108', params={'day': 19991231})
  assert resp.status_code == 422


def test_get_train_movements_day_above_max(client: TestClient) -> None:
  """GET /train/E108?day=22000101 returns 422 (day above maximum)."""
  resp = client.get('/train/E108', params={'day': 22000101})
  assert resp.status_code == 422


# ---------------------------------------------------------------------------
# OpenAPI metadata
# ---------------------------------------------------------------------------


def test_openapi_schema(client: TestClient) -> None:
  """GET /openapi.json returns 200 with the expected title and all routes present."""
  resp = client.get('/openapi.json')
  assert resp.status_code == 200
  schema = resp.json()
  assert schema['info']['title'] == 'TFINTA Realtime API'
  assert schema['info']['version'] == __version__
  paths = schema['paths']
  assert '/health' in paths
  assert '/stations' in paths
  assert '/running' in paths
  assert '/station/{station_code}' in paths
  assert '/train/{train_code}' in paths


def test_openapi_operation_ids(client: TestClient) -> None:
  """Every route exposes a clean operationId suitable for code-generation."""
  resp = client.get('/openapi.json')
  assert resp.status_code == 200
  paths = resp.json()['paths']
  assert paths['/health']['get']['operationId'] == 'health'
  assert paths['/stations']['get']['operationId'] == 'getStations'
  assert paths['/running']['get']['operationId'] == 'getRunningTrains'
  assert paths['/station/{station_code}']['get']['operationId'] == 'getStationBoard'
  assert paths['/train/{train_code}']['get']['operationId'] == 'getTrainMovements'


def test_openapi_error_responses(client: TestClient) -> None:
  """Data endpoints document a 502 error response with ErrorResponse schema."""
  resp = client.get('/openapi.json')
  assert resp.status_code == 200
  paths = resp.json()['paths']
  for route in ('/stations', '/running', '/station/{station_code}', '/train/{train_code}'):
    responses = paths[route]['get']['responses']
    assert '502' in responses, f'{route} missing 502 response'


def test_openapi_enum_literals(client: TestClient) -> None:
  """Enum string fields expose ``enum`` constraints in the OpenAPI schema."""
  resp = client.get('/openapi.json')
  assert resp.status_code == 200
  schema = resp.json()
  # Resolve RunningTrainModel.status
  running_props = schema['components']['schemas']['RunningTrainModel']['properties']
  status_schema = running_props['status']
  # Pydantic may inline enum values or use anyOf; accept both
  status_enum: list[str] | None = status_schema.get('enum')
  if status_enum is None:
    # anyOf with const entries
    status_enum = [opt.get('const') for opt in status_schema.get('anyOf', []) if 'const' in opt]
  assert set(status_enum) == {'TERMINATED', 'NOT_YET_RUNNING', 'RUNNING'}
  # Resolve TrainStopModel.stop_type
  stop_props = schema['components']['schemas']['TrainStopModel']['properties']
  stop_type = stop_props['stop_type']
  stop_enum: list[str] | None = stop_type.get('enum')
  if stop_enum is None:
    stop_enum = [opt.get('const') for opt in stop_type.get('anyOf', []) if 'const' in opt]
  assert set(stop_enum) == {'UNKNOWN', 'CURRENT', 'NEXT'}


def test_docs_endpoint(client: TestClient) -> None:
  """GET /docs returns 200 (Swagger UI is served)."""
  resp = client.get('/docs')
  assert resp.status_code == 200


def test_redoc_endpoint(client: TestClient) -> None:
  """GET /redoc returns 200 (ReDoc UI is served)."""
  resp = client.get('/redoc')
  assert resp.status_code == 200
