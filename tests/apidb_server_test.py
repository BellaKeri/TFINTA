# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""apidb_server.py unittest."""

from __future__ import annotations

from unittest import mock

import pytest
from click import testing as click_testing
from transcrypto.utils import config as app_config
from transcrypto.utils import logging as tc_logging
from typer import testing as typer_testing

from tfinta import apidb_server


@pytest.fixture(autouse=True)
def reset_cli_logging_singletons() -> None:
  """Reset global console/logging state between tests.

  The CLI callback initializes a global Rich console singleton via InitLogging().
  Tests invoke the CLI multiple times across test cases, so we must reset that
  singleton to keep tests isolated.
  """
  tc_logging.ResetConsole()
  app_config.ResetConfig()


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


def test_main_version() -> None:
  """Test --version flag exits 0 and prints a non-empty version string."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(apidb_server.app, ['--version'])
  assert result.exit_code == 0
  assert result.output.strip()


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------


def test_main_markdown() -> None:
  """Test markdown command succeeds and prints docs to console."""
  with mock.patch('transcrypto.utils.logging.InitLogging') as mock_init_logging:
    mock_console = mock.MagicMock()
    mock_init_logging.return_value = (mock_console, 0, False)
    result: click_testing.Result = typer_testing.CliRunner().invoke(apidb_server.app, ['markdown'])
    assert result.exit_code == 0
    mock_console.print.assert_called_once()


# ---------------------------------------------------------------------------
# run - default options
# ---------------------------------------------------------------------------


@mock.patch('tfinta.apidb_server.uvicorn.run', autospec=True)
def test_main_run_defaults(mock_uvicorn: mock.MagicMock) -> None:
  """Test ``run`` command with no extra flags starts uvicorn with default host/port."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(apidb_server.app, ['run'])
  assert result.exit_code == 0, result.output
  mock_uvicorn.assert_called_once_with(
    'tfinta.apidb:app',
    host='0.0.0.0',  # noqa: S104
    port=8081,
    reload=False,
    log_level='error',
  )


# ---------------------------------------------------------------------------
# run - custom host / port
# ---------------------------------------------------------------------------


@mock.patch('tfinta.apidb_server.uvicorn.run', autospec=True)
def test_main_run_custom_host_port(mock_uvicorn: mock.MagicMock) -> None:
  """Test ``run --host 127.0.0.1 --port 9000`` passes custom values to uvicorn."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    apidb_server.app, ['run', '--host', '127.0.0.1', '--port', '9000']
  )
  assert result.exit_code == 0, result.output
  mock_uvicorn.assert_called_once_with(
    'tfinta.apidb:app',
    host='127.0.0.1',
    port=9000,
    reload=False,
    log_level='error',
  )


@mock.patch('tfinta.apidb_server.uvicorn.run', autospec=True)
def test_main_run_short_flags(mock_uvicorn: mock.MagicMock) -> None:
  """Test ``run -h 0.0.0.0 -p 8888`` short-flag aliases work."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    apidb_server.app,
    ['run', '-h', '0.0.0.0', '-p', '8888'],  # noqa: S104
  )
  assert result.exit_code == 0, result.output
  mock_uvicorn.assert_called_once_with(
    'tfinta.apidb:app',
    host='0.0.0.0',  # noqa: S104
    port=8888,
    reload=False,
    log_level='error',
  )


# ---------------------------------------------------------------------------
# run - reload flag
# ---------------------------------------------------------------------------


@mock.patch('tfinta.apidb_server.uvicorn.run', autospec=True)
def test_main_run_reload(mock_uvicorn: mock.MagicMock) -> None:
  """Test ``run --reload`` passes reload=True to uvicorn."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    apidb_server.app, ['run', '--reload']
  )
  assert result.exit_code == 0, result.output
  mock_uvicorn.assert_called_once_with(
    'tfinta.apidb:app',
    host='0.0.0.0',  # noqa: S104
    port=8081,
    reload=True,
    log_level='error',
  )


@mock.patch('tfinta.apidb_server.uvicorn.run', autospec=True)
def test_main_run_no_reload(mock_uvicorn: mock.MagicMock) -> None:
  """Test ``run --no-reload`` explicitly passes reload=False."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    apidb_server.app, ['run', '--no-reload']
  )
  assert result.exit_code == 0, result.output
  mock_uvicorn.assert_called_once_with(
    'tfinta.apidb:app',
    host='0.0.0.0',  # noqa: S104
    port=8081,
    reload=False,
    log_level='error',
  )


# ---------------------------------------------------------------------------
# run - verbosity -> log_level mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
  ('verbose_flags', 'expected_log_level'),
  [
    ([], 'error'),
    (['-v'], 'warning'),
    (['-vv'], 'info'),
    (['-vvv'], 'debug'),
  ],
)
@mock.patch('tfinta.apidb_server.uvicorn.run', autospec=True)
def test_main_run_verbosity(
  mock_uvicorn: mock.MagicMock,
  verbose_flags: list[str],
  expected_log_level: str,
) -> None:
  """Test that -v/-vv/-vvv flags translate to the correct uvicorn log_level."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    apidb_server.app, [*verbose_flags, 'run']
  )
  assert result.exit_code == 0, result.output
  _, call_kwargs = mock_uvicorn.call_args
  assert call_kwargs['log_level'] == expected_log_level


# ---------------------------------------------------------------------------
# run - combined options
# ---------------------------------------------------------------------------


@mock.patch('tfinta.apidb_server.uvicorn.run', autospec=True)
def test_main_run_all_options(mock_uvicorn: mock.MagicMock) -> None:
  """Test a fully specified ``run`` invocation passes all options correctly."""
  result: click_testing.Result = typer_testing.CliRunner().invoke(
    apidb_server.app,
    ['-vv', 'run', '--host', '0.0.0.0', '--port', '8081', '--reload'],  # noqa: S104
  )
  assert result.exit_code == 0, result.output
  mock_uvicorn.assert_called_once_with(
    'tfinta.apidb:app',
    host='0.0.0.0',  # noqa: S104
    port=8081,
    reload=True,
    log_level='info',
  )
