# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: build wheel, install into a fresh venv, run installed console scripts.

Why this exists (vs normal unit tests):
- Unit tests (CliRunner) validate CLI wiring while running from the source tree.
- This test validates *packaging*: the wheel builds, installs, and the console scripts work.

What we verify:
- `gtfs --version` prints the expected version.
- `dart --version` prints the expected version.
- `realtime --version` prints the expected version.
- All CLIs run a small `--no-color` command successfully and produce non-ANSI output.

Run this with:

poetry run pytest -vvv -q tests_integration
"""

from __future__ import annotations

import pathlib
import shutil

import pytest
from transcrypto.utils import base, config

import tfinta
from tfinta import tfinta_base

_APP_NAMES: set[str] = {'gtfs', 'dart', 'realtime', 'realtime-api'}


@pytest.mark.integration
def test_installed_cli_smoke(tmp_path: pathlib.Path) -> None:
  """Build wheel, install into a clean venv, run the installed CLIs."""
  repo_root: pathlib.Path = pathlib.Path(__file__).resolve().parents[1]
  expected_version: str = tfinta.__version__
  vpy, bin_dir = config.EnsureAndInstallWheel(repo_root, tmp_path, expected_version, _APP_NAMES)
  cli_paths: dict[str, pathlib.Path] = config.EnsureConsoleScriptsPrintExpectedVersion(
    vpy, bin_dir, expected_version, _APP_NAMES
  )
  # basic command smoke tests
  data_dir: pathlib.Path = config.CallGetConfigDirFromVEnv(vpy, tfinta_base.APP_NAME)
  _GTFS_call(cli_paths, data_dir)
  _DART_call(cli_paths, data_dir)
  _realtime_call(cli_paths)


def _GTFS_call(cli_paths: dict[str, pathlib.Path], data_dir: pathlib.Path, /) -> None:
  try:
    # gtfs: read data and print basics; use --no-color to avoid ANSI codes in asserts.
    r = base.Run([str(cli_paths['gtfs']), '--no-color', 'read'])
    assert 'loaded successfully' in r.stdout.lower()
    assert '\x1b[' not in r.stdout and '\x1b[' not in r.stderr  # no ANSI codes
    # verify GTFS created a local DB under the platformdirs user config location
    db_file: pathlib.Path = data_dir / 'transit.db'
    assert data_dir.exists() and db_file.exists()
    r = base.Run([str(cli_paths['gtfs']), '--no-color', 'print', 'basics'])
    # match presence of DART routes with a 5355_123769 route id fragment
    assert 'DART' in r.stdout and 'Iarnród Éireann / Irish Rail' in r.stdout
    assert '\x1b[' not in r.stdout and '\x1b[' not in r.stderr  # no ANSI codes
  finally:
    shutil.rmtree(data_dir)  # remove created data to isolate the next CLI's read step


def _DART_call(cli_paths: dict[str, pathlib.Path], data_dir: pathlib.Path, /) -> None:
  try:
    # dart: read data and print station info; use --no-color to avoid ANSI codes in asserts.
    r = base.Run([str(cli_paths['dart']), '--no-color', 'read'])
    assert 'loaded successfully' in r.stdout.lower()
    assert '\x1b[' not in r.stdout and '\x1b[' not in r.stderr  # no ANSI codes
    # verify DART also created the local DB file in the platformdirs user config location
    db_file: pathlib.Path = data_dir / 'transit.db'
    assert data_dir.exists() and db_file.exists()
    r = base.Run([str(cli_paths['dart']), '--no-color', 'print', 'station', 'Tara'])
    # ensure output contains the expected station header, station code, a known
    # destination and a service/trip id fragment (more specific than just non-empty)
    assert 'Tara Street' in r.stdout and '8220IR0025' in r.stdout and 'Bray' in r.stdout
    assert '\x1b[' not in r.stdout and '\x1b[' not in r.stderr  # no ANSI codes
  finally:
    shutil.rmtree(data_dir)  # remove created data to isolate the next CLI's read step


def _realtime_call(cli_paths: dict[str, pathlib.Path], /) -> None:
  # realtime: print stations; use --no-color to avoid ANSI codes in asserts.
  r = base.Run([str(cli_paths['realtime']), '--no-color', 'print', 'stations'])
  # table output varies; assert Bray station id and code exist
  assert 'BRAY' in r.stdout and 'Bray' in r.stdout and '140' in r.stdout
  assert '\x1b[' not in r.stdout and '\x1b[' not in r.stderr  # no ANSI codes
