# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Test utils."""

from __future__ import annotations

import dataclasses
import io
import pathlib
import types
from collections import abc
from typing import Self
from unittest import mock

from rich import table

# test dir
_TEST_DIR: pathlib.Path = pathlib.Path(__file__).parent
DATA_DIR: pathlib.Path = _TEST_DIR / 'data'


class FakeHTTPStream(io.BytesIO):
  """Wrapper mimics the object returned by urllib.request.urlopen (context-manager & read() method).

  Accepts *bytes* at construction.
  """

  def __init__(self, payload: bytes, /) -> None:  # noqa: D107
    super().__init__(payload)

  def __enter__(self) -> Self:  # noqa: D105
    return self

  def __exit__(  # noqa: D105
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: types.TracebackType | None,
  ) -> None:
    self.close()


class FakeHTTPFile(FakeHTTPStream):
  """Wrapper mimics the object returned by urllib.request.urlopen (context-manager & read() method).

  Accepts *a file path* at construction.
  """

  def __init__(self, payload_path: str | pathlib.Path, /) -> None:
    """Construct."""
    super().__init__(pathlib.Path(payload_path).read_bytes())


@dataclasses.dataclass(kw_only=False, slots=True, frozen=True)
class Data:
  """Expected data cell for AssertTable.

  We don't actually need this for now, since all styles are "inline".
  Later if we need this replace `str` for `Data` in ExpectedTable.

  """

  value: str
  style: str | None = None


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class ExpectedTable:
  """Expected data structure for AssertTable."""

  columns: list[str]
  rows: list[list[str]]


type ExpectedPrettyPrint = list[str | ExpectedTable]


def AssertTable(expected_data: ExpectedTable, actual_table: table.Table, /) -> None:
  """Assert that a rich Table matches expected data structure.

  Args:
    expected_data: ExpectedTable object, defining the columns and data to validate against.
    actual_table: A rich.table.Table object to validate

  """
  # check by columns
  n_cols: int = len(actual_table.columns)
  assert n_cols == len(expected_data.columns), 'incorrect number of headers'
  for i, actual_col in enumerate(actual_table.columns):
    val: str = expected_data.columns[i]
    assert str(actual_col.header) == val, f'Header {i}: expected {val!r}, got {actual_col.header!r}'
    cells_list = list(actual_col.cells)
    assert len(cells_list) == len(expected_data.rows), f'Col {i}: incorrect number of cells'
    for r, cell in enumerate(cells_list):
      assert n_cols == len(expected_data.rows[r]), f'incorrect number of columns in row {r}'
      val = expected_data.rows[r][i]
      assert str(cell) == val, f'Cell {r}/{i}: expected {val!r}, got {cell!r}'


def AssertPrettyPrint(
  expected_data: ExpectedPrettyPrint, actual_pretty: abc.Generator[str | table.Table, None, None], /
) -> None:
  """Assert that a "PrettyPrint" generator matches expected data structure.

  Args:
    expected_data: List of strings or ExpectedTable objects, defining the data to validate against.
    actual_pretty: Generator yielding strings or table.Table objects, to validate against.

  """
  for i, (expected, actual) in enumerate(zip(expected_data, actual_pretty, strict=True)):
    if isinstance(expected, str):
      assert expected == actual, f'Line {i}: expected {expected!r}, got {actual!r}'
    else:
      assert isinstance(actual, table.Table), f'Line {i}: not table, got {type(actual).__name__!r}'
      AssertTable(expected, actual)


def MockAppConfig(dir_path: str = 'db/path', config_file: str = 'transit.db') -> mock.MagicMock:
  """Create a mock AppConfig object for testing.

  DEPRECATED: Use app_config.AppConfig() with make_temporary=True or fixed_dir instead.

  Args:
    dir_path: Directory path for the config (ignored, creates mock paths)
    config_file: Config file name

  Returns:
    Mock AppConfig object with dir and path attributes

  """
  mock_config = mock.MagicMock()
  mock_config.app_name = 'TFINTA'
  mock_config.main_config = config_file
  # Create mock path objects that don't hit the filesystem
  mock_dir = mock.MagicMock(spec=pathlib.Path)
  mock_dir.__str__.return_value = dir_path.strip()  # pyright: ignore[reportAttributeAccessIssue]
  mock_dir.__truediv__ = lambda _self, _other: mock_path  # pyright: ignore[reportUnknownLambdaType] # For path / file operations
  mock_path = mock.MagicMock(spec=pathlib.Path)
  mock_path.__str__.return_value = f'{dir_path.strip()}/{config_file}'  # pyright: ignore[reportAttributeAccessIssue]
  mock_path.exists = mock.MagicMock(return_value=False)  # Default to not existing
  mock_config.dir = mock_dir
  mock_config.path = mock_path
  mock_config.temp = False
  return mock_config
