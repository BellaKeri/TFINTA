#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
"""Test utils."""

import io
import os.path
# import pdb
from typing import Any, Self

__author__ = 'BellaKeri@github.com , balparda@github.com'


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
    with open(payload_path, 'rb') as payload:
      super().__init__(payload.read())
