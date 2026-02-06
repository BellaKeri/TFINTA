# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""TFINTA base constants and methods."""

from __future__ import annotations

import dataclasses
import datetime
import functools
import re
import time
from collections import abc
from typing import Self

import platformdirs
from transcrypto.utils import base

# Logging and formatting

ANSI_ESCAPE: re.Pattern[str] = re.compile(r'\x1b\[[0-9;]*m')
STRIP_ANSI: abc.Callable[[str], str] = lambda s: ANSI_ESCAPE.sub('', s)

# Time utilities

TIME_FORMAT: str = '%Y/%b/%d-%H:%M:%S-UTC'
STD_TIME_STRING: abc.Callable[[int | float | None], str] = lambda tm: (
  time.strftime(TIME_FORMAT, time.gmtime(tm)) if tm else '-'
)

# Path utilities

DEFAULT_DATA_DIR: str = str(platformdirs.user_data_path('tfinta'))


# data parsing utils

BOOL_FIELD: dict[str, bool] = {'0': False, '1': True}
_DT_OBJ_GTFS: abc.Callable[[str], datetime.datetime] = lambda s: datetime.datetime.strptime(  # noqa: DTZ007
  s, '%Y%m%d'
)
_DT_OBJ_REALTIME: abc.Callable[[str], datetime.datetime] = lambda s: datetime.datetime.strptime(  # noqa: DTZ007
  s, '%d %b %Y'
)
# _UTC_DATE: abc.Callable[[str], float] = lambda s: _DT_OBJ(s).replace(
#     tzinfo=datetime.timezone.utc).timestamp()
DATE_OBJ_GTFS: abc.Callable[[str], datetime.date] = lambda s: _DT_OBJ_GTFS(s).date()
DATE_OBJ_REALTIME: abc.Callable[[str], datetime.date] = lambda s: _DT_OBJ_REALTIME(s).date()
DATETIME_FROM_ISO: abc.Callable[[str], datetime.datetime] = datetime.datetime.fromisoformat

NULL_TEXT: str = '\u2205'  # ∅
LIMITED_TEXT: abc.Callable[[str | None, int], str] = (
  lambda s, w: NULL_TEXT if s is None else (s if len(s) <= w else f'{s[: (w - 1)]}\u2026')  # …
)
PRETTY_BOOL: abc.Callable[[bool | None], str] = lambda b: (  # ✓ and ✗
  '\u2713' if b else '\u2717'
)

DAY_NAME: dict[int, str] = {
  0: 'Monday',
  1: 'Tuesday',
  2: 'Wednesday',
  3: 'Thursday',
  4: 'Friday',
  5: 'Saturday',
  6: 'Sunday',
}

SHORT_DAY_NAME: abc.Callable[[int], str] = lambda i: DAY_NAME[i][:3]
PRETTY_DATE: abc.Callable[[datetime.date | None], str] = lambda d: (
  NULL_TEXT if d is None else f'{d.isoformat()}\u00b7{SHORT_DAY_NAME(d.weekday())}'
)  # ·


class Error(base.Error):
  """TFINTA exception."""


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DayTime:
  """A time during some arbitrary day, measured in int seconds since midnight."""

  time: int

  def __post_init__(self) -> None:
    """Check construction.

    Raises:
      Error: if time < 0

    """
    if self.time < 0:
      raise Error(f'invalid time: {self}')

  def __lt__(self, other: DayTime) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (DayTime): Other object to compare against.

    Returns:
        bool: True if this DayTime is less than the other, False otherwise.

    """
    return self.time < other.time

  def ToHMS(self) -> str:
    """Seconds from midnight to 'HH:MM:SS' representation. Supports any positive integer.

    Returns:
      str: Time in 'HH:MM:SS' format.

    """
    h, sec = divmod(self.time, 3600)
    m, s = divmod(sec, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

  @classmethod
  def FromHMS(cls, time_str: str, /) -> Self:
    """Convert 'H:MM:SS' or 'HH:MM:SS' and returns total seconds since 00:00:00.

    Supports hours ≥ 0 with no upper bound. Very flexible, will even accept 'H:M:S' for example.

    Args:
      time_str: String to convert ('H:MM:SS' or 'HH:MM:SS')

    Returns:
      DayTime: Corresponding DayTime object.

    Raises:
      Error: malformed input

    """
    try:
      h_str, m_str, s_str = time_str.split(':')
      h, m, s = int(h_str), int(m_str), int(s_str)
    except ValueError as err:
      raise Error(f'bad time literal {time_str!r}') from err
    if not (0 <= m < 60 and 0 <= s < 60):  # noqa: PLR2004
      raise Error(f'bad time literal {time_str!r}: minute and second must be 0-59')
    return cls(time=h * 3600 + m * 60 + s)


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DayRange:
  """A time during some arbitrary day, measured in int seconds since midnight."""

  arrival: DayTime | None
  departure: DayTime | None
  strict: bool = True  # if False won't check that arrival <= departure
  nullable: bool = False  # if False won't allow None values

  def __post_init__(self) -> None:
    """Check construction.

    Raises:
      Error: if not nullable and arrival or departure is None or if strict and arrival > departure

    """
    if not self.nullable and (self.arrival is None or self.departure is None):
      raise Error(f'this DayRange is "not nullable": {self}')
    if self.strict and self.arrival and self.departure and self.arrival.time > self.departure.time:
      raise Error(f'this DayRange is "strict" and checks that arrival <= departure: {self}')

  def __lt__(self, other: DayRange) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (DayRange): Other object to compare against.

    Returns:
        bool: True if this DayRange is less than the other, False otherwise.

    """
    if self.departure and other.departure and self.departure != other.departure:
      return self.departure.time < other.departure.time
    if self.arrival and other.arrival and self.arrival != other.arrival:
      return self.arrival.time < other.arrival.time
    return bool((self.departure and not other.departure) or (self.arrival and not other.arrival))


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Point:
  """A point (location) on Earth. Latitude and longitude in decimal degrees (WGS84)."""

  latitude: float  # latitude;   -90.0 <= lat <= 90.0  (required)
  longitude: float  # longitude; -180.0 <= lat <= 180.0 (required)

  def __post_init__(self) -> None:
    """Check construction.

    Raises:
      Error: if latitude or longitude out of bounds

    """
    if not -90.0 <= self.latitude <= 90.0 or not -180.0 <= self.longitude <= 180.0:  # noqa: PLR2004
      raise Error(f'invalid latitude/longitude: {self}')

  def ToDMS(self) -> tuple[str, str]:
    """Return latitude and longitude as DMS with Unicode symbols and N/S, E/W.

    Returns:
      tuple[str, str]: (latitude DMS, longitude DMS)

    """

    def _conv(deg_float: float, pos: str, neg: str, /) -> str:
      d: float = abs(deg_float)
      degrees = int(d)
      total_min: float = (d - degrees) * 60.0
      minutes = int(total_min)
      seconds: float = round((total_min - minutes) * 60.0, 2)  # 0.01 sec precision = 60cm or less
      if seconds >= 60.0:  # handle carry-over for seconds → minutes  # noqa: PLR2004
        seconds = 0.0
        minutes += 1
      if minutes >= 60:  # handle carry-over for minutes → degrees  # noqa: PLR2004
        minutes = 0
        degrees += 1
      hemisphere: str = pos if deg_float >= 0 else neg
      return f'{degrees}°{minutes}′{seconds:0.2f}″{hemisphere}'  # noqa: RUF001

    return (_conv(self.latitude, 'N', 'S'), _conv(self.longitude, 'E', 'W'))


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DaysRange:
  """Range of calendar days (supposes start <= end, but doesn't check). Sortable."""

  start: datetime.date
  end: datetime.date

  def __post_init__(self) -> None:
    """Check construction.

    Raises:
      Error: if start > end

    """
    if self.start > self.end:
      raise Error(f'invalid dates: {self}')

  def __lt__(self, other: DaysRange) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__).

    Args:
        other (DaysRange): Other object to compare against.

    Returns:
        bool: True if this DaysRange is less than the other, False otherwise.

    """
    if self.start != other.start:
      return self.start < other.start
    return self.end < other.end
