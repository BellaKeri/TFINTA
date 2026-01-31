# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Test utils."""

from __future__ import annotations

import io
import os.path
import pathlib

# import pdb
from typing import Any, Self

from src.tfinta import tfinta_base as base

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = base.__version__


# test dir
_TEST_DIR: str = os.path.split(__file__)[0]
DATA_DIR: str = os.path.join(_TEST_DIR, 'data')


class FakeHTTPStream(io.BytesIO):
  """Minimal wrapper that mimics the object returned by urllib.request.urlopen
  (context-manager & read() method).  Accepts *bytes* at construction.
  """

  def __init__(self, payload: bytes, /) -> None:
    super().__init__(payload)

  def __enter__(self) -> Self:
    return self

  def __exit__(self, unused_exc_type: Any, unused_exc_val: Any, unused_exc_tb: Any):  # type:ignore
    self.close()
    return False  # propagate exceptions


class FakeHTTPFile(FakeHTTPStream):
  """Minimal wrapper that mimics the object returned by urllib.request.urlopen
  (context-manager & read() method).  Accepts *a file path* at construction.
  """

  def __init__(self, payload_path: str, /) -> None:
    with pathlib.Path(payload_path).open('rb') as payload:
      super().__init__(payload.read())
