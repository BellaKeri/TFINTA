# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Test utils."""

from __future__ import annotations

import dataclasses
import io
import os.path
import pathlib
import types
from typing import Self

from rich import table

# test dir
_TEST_DIR: str = os.path.split(__file__)[0]
DATA_DIR: str = os.path.join(_TEST_DIR, 'data')  # noqa: PTH118


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

  def __init__(self, payload_path: str, /) -> None:  # noqa: D107
    super().__init__(pathlib.Path(payload_path).read_bytes())


@dataclasses.dataclass(kw_only=False, slots=True, frozen=True)
class Data:
  """Expected data cell for AssertTable."""

  value: str
  style: str | None = None


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class ExpectedTable:
  """Expected data structure for AssertTable."""

  columns: list[Data]
  rows: list[list[Data]]


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
    expected_col: Data = expected_data.columns[i]
    val: str = expected_col.value
    assert str(actual_col.header) == val, f'Header {i}: expected {val!r}, got {actual_col.header!r}'
    if expected_col.style is not None:
      assert str(actual_col.style) == expected_col.style, (
        f'Header {i} style: expected {expected_col.style!r}, got {actual_col.style!r}'
      )
    cells_list = list(actual_col.cells)
    assert len(cells_list) == len(expected_data.rows), f'Col {i}: incorrect number of cells'
    for r, cell in enumerate(cells_list):
      assert n_cols == len(expected_data.rows[r]), f'incorrect number of columns in row {r}'
      expected_cell: Data = expected_data.rows[r][i]
      assert str(cell) == expected_cell.value, (
        f'Cell {r}/{i}: expected {expected_cell.value!r}, got {cell!r}'
      )
      if expected_cell.style is not None:
        style_str = str(getattr(cell, 'style', ''))
        assert style_str == expected_cell.style, (
          f'Cell {r}/{i} style: expected {expected_cell.style!r}, got {style_str!r}'
        )
