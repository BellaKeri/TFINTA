# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""TFINTA Realtime fastapi.FastAPI application.

Wraps ``RealtimeRail`` calls behind a REST/JSON API with automatic OpenAPI
documentation.  Intended for deployment on Google Cloud Run (or any
container-based hosting).

Run locally with::

    uvicorn tfinta.api:app --reload --port 8080

The interactive docs are then available at ``http://localhost:8080/docs``.
"""

from __future__ import annotations

import contextlib
import datetime
from collections import abc
from typing import Annotated, Any

import fastapi
import pydantic

from . import __version__, realtime
from . import realtime_data_model as dm
from . import tfinta_base as base

# ---------------------------------------------------------------------------
# Shared error model (visible in the OpenAPI schema)
# ---------------------------------------------------------------------------


class ErrorResponse(pydantic.BaseModel):
  """Standard error body returned by all non-2xx responses."""

  detail: str = pydantic.Field(description='Human-readable error message.')


type ErrorResponseType = dict[int | str, dict[str, Any]]


_RESPONSES_502: ErrorResponseType = {
  502: {
    'description': 'Upstream Irish Rail API error.',
    'model': ErrorResponse,
  },
}
_RESPONSES_503: ErrorResponseType = {
  503: {
    'description': 'Service not ready (still starting up).',
    'model': ErrorResponse,
  },
}

# ---------------------------------------------------------------------------
# Application lifespan: create the shared RealtimeRail instance once
# ---------------------------------------------------------------------------

_realtime: realtime.RealtimeRail | None = None


@contextlib.asynccontextmanager
async def _lifespan(_app: fastapi.FastAPI) -> abc.AsyncGenerator[None, None]:  # noqa: RUF029
  """Create the shared RealtimeRail instance on startup."""
  global _realtime  # noqa: PLW0603
  _realtime = realtime.RealtimeRail()
  yield
  _realtime = None


# ---------------------------------------------------------------------------
# fastapi.FastAPI application
# ---------------------------------------------------------------------------


def _custom_operation_id(route: fastapi.routing.APIRoute) -> str:
  """Derive a clean ``operationId`` from the endpoint function name.

  Falls back to the default FastAPI scheme when no name is set.

  Returns:
    str: the operation ID string.

  """
  return route.name


app = fastapi.FastAPI(
  title='TFINTA Realtime API',
  description=(
    'REST API for Irish Rail Realtime data '
    '(stations, running trains, station boards, train movements).'
  ),
  version=__version__,
  lifespan=_lifespan,
  docs_url='/docs',
  redoc_url='/redoc',
  generate_unique_id_function=_custom_operation_id,
  servers=[
    {'url': '/', 'description': 'Current server'},
  ],
)


def _get_realtime() -> realtime.RealtimeRail:
  """Return the shared ``RealtimeRail``, raising 503 if unavailable.

  Returns:
    realtime.RealtimeRail: the shared instance.

  Raises:
    fastapi.HTTPException: if the service is not ready (503).

  """
  if _realtime is None:  # pragma: no cover
    raise fastapi.HTTPException(status_code=503, detail='Service not ready')
  return _realtime


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get(
  '/health',
  tags=['health'],
  operation_id='health',
  summary='Health check',
)
async def health() -> dict[str, str]:
  """Liveness / readiness probe for Cloud Run.

  Returns:
    dict[str, str]: status and version.

  """
  return {'status': 'ok', 'version': __version__}


# ---------------------------------------------------------------------------
# Stations
# ---------------------------------------------------------------------------


@app.get(
  '/stations',
  response_model=dm.StationsResponse,
  tags=['stations'],
  summary='List all Irish Rail stations',
  operation_id='getStations',
  responses=_RESPONSES_502,
)
async def get_stations() -> dm.StationsResponse:
  """Return every station known to Irish Rail Realtime.

  Returns:
    dm.StationsResponse: all stations.

  Raises:
    fastapi.HTTPException: upstream error (502).

  """
  try:
    stations: list[dm.Station] = _get_realtime().StationsCall()
  except realtime.Error as exc:
    raise fastapi.HTTPException(status_code=502, detail=str(exc)) from exc
  return dm.StationsResponse(
    count=len(stations),
    stations=[dm.StationModel.from_domain(s) for s in stations],
  )


# ---------------------------------------------------------------------------
# Running trains
# ---------------------------------------------------------------------------


@app.get(
  '/running',
  response_model=dm.RunningTrainsResponse,
  tags=['trains'],
  summary='List currently running trains',
  operation_id='getRunningTrains',
  responses=_RESPONSES_502,
)
async def get_running_trains() -> dm.RunningTrainsResponse:
  """Return all trains currently operating on the network.

  Returns:
    dm.RunningTrainsResponse: running trains.

  Raises:
    fastapi.HTTPException: upstream error (502).

  """
  try:
    trains: list[dm.RunningTrain] = _get_realtime().RunningTrainsCall()
  except realtime.Error as exc:
    raise fastapi.HTTPException(status_code=502, detail=str(exc)) from exc
  return dm.RunningTrainsResponse(
    count=len(trains),
    trains=[dm.RunningTrainModel.from_domain(t) for t in trains],
  )


# ---------------------------------------------------------------------------
# Station board
# ---------------------------------------------------------------------------


@app.get(
  '/station/{station_code}',
  response_model=dm.StationBoardResponse,
  tags=['stations'],
  summary='Station departure/arrival board',
  operation_id='getStationBoard',
  responses=_RESPONSES_502,
)
async def get_station_board(
  station_code: Annotated[
    str,
    fastapi.Path(
      description=(
        'Either a 5-letter station code (e.g. ``LURGN``) or a search '
        'fragment that uniquely identifies a station (e.g. ``lurgan``).'
      ),
      examples=['LURGN', 'lurgan'],
    ),
  ],
) -> dm.StationBoardResponse:
  """Trains due to serve the given station in the next ~90 minutes.

  Returns:
    dm.StationBoardResponse: station board.

  Raises:
    fastapi.HTTPException: upstream error (502).

  """
  rt: realtime.RealtimeRail = _get_realtime()
  query_data: dm.StationLineQueryData | None
  lines: list[dm.StationLine]
  try:
    resolved_code: str = rt.StationCodeFromNameFragmentOrCode(station_code)
    query_data, lines = rt.StationBoardCall(resolved_code)
  except realtime.Error as exc:
    raise fastapi.HTTPException(status_code=502, detail=str(exc)) from exc
  return dm.StationBoardResponse(
    query=(
      dm.StationLineQueryDataModel.from_domain(query_data) if query_data is not None else None
    ),
    count=len(lines),
    lines=[dm.StationLineModel.from_domain(ln) for ln in lines],
  )


# ---------------------------------------------------------------------------
# Train movements
# ---------------------------------------------------------------------------


@app.get(
  '/train/{train_code}',
  response_model=dm.TrainMovementsResponse,
  tags=['trains'],
  summary='Train movements / stops',
  operation_id='getTrainMovements',
  responses=_RESPONSES_502,
)
async def get_train_movements(
  train_code: Annotated[
    str,
    fastapi.Path(
      description='Train code, e.g. ``E108``.',
      examples=['E108'],
    ),
  ],
  day: Annotated[
    int | None,
    fastapi.Query(
      ge=20000101,
      le=21991231,
      description='Day in YYYYMMDD format.  Defaults to today (UTC).',
      examples=[20260201],
    ),
  ] = None,
) -> dm.TrainMovementsResponse:
  """Return the ordered list of stops for a single train on a given day.

  Returns:
    dm.TrainMovementsResponse: train movements.

  Raises:
    fastapi.HTTPException: upstream error (502).

  """
  day_obj: datetime.date = (
    base.DATE_OBJ_GTFS(str(day))
    if day is not None
    else datetime.datetime.now(tz=datetime.UTC).date()
  )
  query_data: dm.TrainStopQueryData | None
  stops: list[dm.TrainStop]
  try:
    query_data, stops = _get_realtime().TrainDataCall(train_code, day_obj)
  except realtime.Error as exc:
    raise fastapi.HTTPException(status_code=502, detail=str(exc)) from exc
  return dm.TrainMovementsResponse(
    query=(dm.TrainStopQueryDataModel.from_domain(query_data) if query_data is not None else None),
    count=len(stops),
    stops=[dm.TrainStopModel.from_domain(s) for s in stops],
  )
