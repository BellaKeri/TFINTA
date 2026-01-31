# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""gtfs.py unittest."""

from __future__ import annotations

import datetime

# import pdb
import sys

import pytest
from src.tfinta import tfinta_base as base

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = base.__version__  # tests inherit version from module


@pytest.mark.parametrize(
  'hms',
  [
    '01',
    '01:01',
    '01:01:aa',
    '00:-1:00',
    '00:00:-1',
    '00:60:00',
    '00:00:60',
  ],
)
def test_DayTime_HMSToSeconds_fail(hms: str) -> None:
  """Test."""
  with pytest.raises(base.Error):
    base.DayTime.FromHMS(hms)


@pytest.mark.parametrize(
  'hms, sec',
  [
    ('00:00:00', 0),
    ('00:00:01', 1),
    ('00:00:10', 10),
    ('00:01:00', 60),
    ('00:10:00', 600),
    ('01:00:00', 3600),
    ('10:00:00', 36000),
    ('23:59:59', 86399),
    ('24:00:00', 86400),
    ('24:01:01', 86461),
    ('240:33:11', 865991),
    ('666:33:11', 2399591),
  ],
)
def test_DayTime_HMSToSeconds(hms: str, sec: int) -> None:
  """Test."""
  assert base.DayTime.FromHMS(hms).time == sec


@pytest.mark.parametrize(
  'sec, hms',
  [
    (0, '00:00:00'),
    (1, '00:00:01'),
    (60, '00:01:00'),
    (3600, '01:00:00'),
    (86399, '23:59:59'),
    (86400, '24:00:00'),
    (2399591, '666:33:11'),
  ],
)
def test_DayTime_SecondsToHMS(sec: int, hms: str) -> None:
  """Test."""
  assert base.DayTime(time=sec).ToHMS() == hms


def test_DayTime_fail() -> None:
  """Test."""
  with pytest.raises(base.Error):
    base.DayTime(time=-1)


@pytest.mark.parametrize(
  'latitude, longitude, dms',
  [
    (0, 0, ('0°0′0.00″N', '0°0′0.00″E')),
    (90, 180, ('90°0′0.00″N', '180°0′0.00″E')),
    (89.999999, 179.999999, ('90°0′0.00″N', '180°0′0.00″E')),
    (89.99999, 179.99999, ('89°59′59.96″N', '179°59′59.96″E')),
    (-90, -180, ('90°0′0.00″S', '180°0′0.00″W')),
    (10, -10, ('10°0′0.00″N', '10°0′0.00″W')),
    (-10, 10, ('10°0′0.00″S', '10°0′0.00″E')),
    (1 / 3, 2 / 3, ('0°20′0.00″N', '0°40′0.00″E')),
    (1 / 3 + 1 / 180, 2 / 3 + 2 / 180, ('0°20′20.00″N', '0°40′40.00″E')),
    (1 / 10, 2 / 100, ('0°6′0.00″N', '0°1′12.00″E')),
    (56.8348294, -34.283768584, ('56°50′5.39″N', '34°17′1.57″W')),
    (-78.837465, 10.38475, ('78°50′14.87″S', '10°23′5.10″E')),
  ],
)
def test_Point_DMS(latitude: float, longitude: float, dms: str) -> None:
  """Test."""
  assert base.Point(latitude=latitude, longitude=longitude).ToDMS() == dms


@pytest.mark.parametrize(
  'latitude, longitude',
  [
    (90.000001, 0),
    (-90.000001, 0),
    (0, 180.000001),
    (0, -180.000001),
  ],
)
def test_Point_error(latitude: float, longitude: float) -> None:
  """Test."""
  with pytest.raises(base.Error, match='invalid latitude/longitude'):
    base.Point(latitude=latitude, longitude=longitude)


def test_DaysRange_error() -> None:
  """Test."""
  base.DaysRange(start=datetime.date(2000, 1, 1), end=datetime.date(2010, 1, 1))
  with pytest.raises(base.Error, match='invalid dates'):
    base.DaysRange(start=datetime.date(2010, 1, 1), end=datetime.date(2000, 1, 1))


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
