#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
"""gtfs.py unittest."""

import io
import pathlib
# import pdb
import sys
from typing import Any, Self
# from unittest import mock
import zipfile

import pytest

from src.tfinta import gtfs


__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 2)


TEST_DIR: pathlib.Path = pathlib.Path(__file__).with_suffix('')
DATA_DIR: pathlib.Path = TEST_DIR / 'data'
CSV_PATH: pathlib.Path = DATA_DIR / 'sample.csv'
ZIP_DIR: pathlib.Path = DATA_DIR / 'zip_1'


def test_HMSToSeconds() -> None:
  """Test."""
  with pytest.raises(ValueError):
    gtfs.HMSToSeconds('01')
  with pytest.raises(ValueError):
    gtfs.HMSToSeconds('01:01')
  with pytest.raises(ValueError):
    gtfs.HMSToSeconds('01:01:aa')
  with pytest.raises(ValueError):
    gtfs.HMSToSeconds('00:-1:00')
  with pytest.raises(ValueError):
    gtfs.HMSToSeconds('00:00:-1')
  with pytest.raises(ValueError):
    gtfs.HMSToSeconds('00:60:00')
  with pytest.raises(ValueError):
    gtfs.HMSToSeconds('00:00:60')
  assert gtfs.HMSToSeconds('00:00:00') == 0
  assert gtfs.HMSToSeconds('00:00:01') == 1
  assert gtfs.HMSToSeconds('00:00:10') == 10
  assert gtfs.HMSToSeconds('00:01:00') == 60
  assert gtfs.HMSToSeconds('00:10:00') == 600
  assert gtfs.HMSToSeconds('01:00:00') == 3600
  assert gtfs.HMSToSeconds('10:00:00') == 36000
  assert gtfs.HMSToSeconds('23:59:59') == 86399
  assert gtfs.HMSToSeconds('24:00:00') == 86400
  assert gtfs.HMSToSeconds('24:01:01') == 86461
  assert gtfs.HMSToSeconds('240:33:11') == 865991
  assert gtfs.HMSToSeconds('666:33:11') == 2399591


def test_SecondsToHMS() -> None:
  """Test."""
  with pytest.raises(ValueError):
    gtfs.SecondsToHMS(-1)
  assert gtfs.SecondsToHMS(0) == '00:00:00'
  assert gtfs.SecondsToHMS(1) == '00:00:01'
  assert gtfs.SecondsToHMS(60) == '00:01:00'
  assert gtfs.SecondsToHMS(3600) == '01:00:00'
  assert gtfs.SecondsToHMS(86399) == '23:59:59'
  assert gtfs.SecondsToHMS(86400) == '24:00:00'
  assert gtfs.SecondsToHMS(2399591) == '666:33:11'


def _ZipDirBytes(src_dir: pathlib.Path) -> bytes:
  """Create an in-memory ZIP from every *.txt file under `src_dir` (non-recursive)."""
  buf = io.BytesIO()
  with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for txt in src_dir.glob('*.txt'):
      zf.writestr(txt.name, txt.read_text(encoding='utf-8'))
  return buf.getvalue()


@pytest.fixture
def zip_1() -> bytes:
  """Create an in-memory ZIP for dir `zip_1`."""
  return _ZipDirBytes(ZIP_DIR)


class FakeHTTPStream(io.BytesIO):
  """
  Minimal wrapper that mimics the object returned by urllib.request.urlopen
  (context-manager & read() method).  Accepts *bytes* at construction.
  """
  def __init__(self, payload: bytes) -> None:
    super().__init__(payload)

  def __enter__(self) -> Self:
    return self

  def __exit__(self, unused_exc_type: Any, unused_exc_val: Any, unused_exc_tb: Any):  # type:ignore
    self.close()
    return False  # propagate exceptions


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
