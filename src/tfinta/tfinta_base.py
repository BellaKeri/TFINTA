#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
"""TFINTA base constants and methods."""

import dataclasses
import datetime
import functools
# import pdb
from typing import Any, Callable, Self

from balparda_baselib import base as balparda_base

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 8)  # v1.8 - 2025/07/10


# copy useful stuff from balparda_baselib

LOG_FORMAT = balparda_base.LOG_FORMAT
MODULE_PRIVATE_DIR = balparda_base.MODULE_PRIVATE_DIR
STD_TIME_STRING = balparda_base.STD_TIME_STRING
STRIP_ANSI = balparda_base.STRIP_ANSI

NULL = balparda_base.TERM_END
BOLD = balparda_base.TERM_BOLD
BLUE = balparda_base.TERM_BLUE
LIGHT_BLUE = balparda_base.TERM_LIGHT_BLUE
GREEN = balparda_base.TERM_GREEN
RED = balparda_base.TERM_RED
LIGHT_RED = balparda_base.TERM_LIGHT_RED
YELLOW = balparda_base.TERM_YELLOW
CYAN = balparda_base.TERM_CYAN
MAGENTA = balparda_base.TERM_MAGENTA

BinSerialize = balparda_base.BinSerialize
BinDeSerialize = balparda_base.BinDeSerialize
Timer = balparda_base.Timer
HumanizedBytes = balparda_base.HumanizedBytes


# data parsing utils

BOOL_FIELD: dict[str, bool] = {'0': False, '1': True}
_DT_OBJ_GTFS: Callable[[str], datetime.datetime] = lambda s: datetime.datetime.strptime(s, '%Y%m%d')
_DT_OBJ_REALTIME: Callable[[str], datetime.datetime] = lambda s: datetime.datetime.strptime(s, '%d %b %Y')
# _UTC_DATE: Callable[[str], float] = lambda s: _DT_OBJ(s).replace(
#     tzinfo=datetime.timezone.utc).timestamp()
DATE_OBJ_GTFS: Callable[[str], datetime.date] = lambda s: _DT_OBJ_GTFS(s).date()
DATE_OBJ_REALTIME: Callable[[str], datetime.date] = lambda s: _DT_OBJ_REALTIME(s).date()
DATETIME_FROM_ISO: Callable[[str], datetime.datetime] = datetime.datetime.fromisoformat

NULL_TEXT: str = f'{BLUE}\u2205{NULL}'  # ∅
LIMITED_TEXT: Callable[[str | None, int], str] = (
    lambda s, w: NULL_TEXT if s is None else (s if len(s) <= w else f'{s[:(w - 1)]}\u2026'))  # …
PRETTY_BOOL: Callable[[bool | None], str] = lambda b: (  # ✓ and ✗
    f'{GREEN}\u2713{NULL}' if b else f'{RED}\u2717{NULL}')

DAY_NAME: dict[int, str] = {
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday',
}

SHORT_DAY_NAME: Callable[[int], str] = lambda i: DAY_NAME[i][:3]
PRETTY_DATE: Callable[[datetime.date | None], str] = lambda d: (
    NULL_TEXT if d is None else f'{d.isoformat()}\u00B7{SHORT_DAY_NAME(d.weekday())}')  # ·


class Error(Exception):
  """TFINTA exception."""


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DayTime:
  """A time during some arbitrary day, measured in int seconds since midnight."""
  time: int

  def __post_init__(self) -> None:
    if self.time < 0:
      raise Error(f'invalid time: {self}')

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, DayTime):
      raise TypeError(f'invalid DayTime type comparison {self!r} versus {other!r}')
    return self.time < other.time

  def ToHMS(self) -> str:
    """Seconds from midnight to 'HH:MM:SS' representation. Supports any positive integer."""
    self.__post_init__()
    h, sec = divmod(self.time, 3600)
    m, s = divmod(sec, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

  @classmethod
  def FromHMS(cls, time_str: str, /) -> Self:
    """Accepts 'H:MM:SS' or 'HH:MM:SS' and returns total seconds since 00:00:00.

    Supports hours ≥ 0 with no upper bound. Very flexible, will even accept 'H:M:S' for example.

    Args:
      time_str: String to convert ('H:MM:SS' or 'HH:MM:SS')

    Raises:
      Error: malformed input
    """
    try:
      h_str, m_str, s_str = time_str.split(':')
      h, m, s = int(h_str), int(m_str), int(s_str)
    except ValueError as err:
      raise Error(f'bad time literal {time_str!r}') from err
    if not (0 <= m < 60 and 0 <= s < 60):
      raise Error(f'bad time literal {time_str!r}: minute and second must be 0-59')
    return cls(time=h * 3600 + m * 60 + s)


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DayRange:
  """A time during some arbitrary day, measured in int seconds since midnight."""
  arrival: DayTime | None
  departure: DayTime | None
  strict: bool = True     # if False won't check that arrival <= departure
  nullable: bool = False  # if False won't allow None values

  def __post_init__(self) -> None:
    if not self.nullable and (self.arrival is None or self.departure is None):
      raise Error(f'this DayRange is "not nullable": {self}')
    if self.strict and self.arrival and self.departure and self.arrival.time > self.departure.time:
      raise Error(f'this DayRange is "strict" and checks that arrival <= departure: {self}')

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, DayRange):
      raise TypeError(f'invalid DayRange type comparison {self!r} versus {other!r}')
    if self.departure and other.departure and self.departure != other.departure:
      return self.departure.time < other.departure.time
    if self.arrival and other.arrival and self.arrival != other.arrival:
      return self.arrival.time < other.arrival.time
    if (self.departure and not other.departure) or (self.arrival and not other.arrival):
      return True
    return False


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Point:
  """A point (location) on Earth. Latitude and longitude in decimal degrees (WGS84)."""
  latitude: float   # latitude;   -90.0 <= lat <= 90.0  (required)
  longitude: float  # longitude; -180.0 <= lat <= 180.0 (required)

  def __post_init__(self) -> None:
    if not -90.0 <= self.latitude <= 90.0 or not -180.0 <= self.longitude <= 180.0:
      raise Error(f'invalid latitude/longitude: {self}')

  def ToDMS(self) -> tuple[str, str]:
    """Return latitude and longitude as DMS with Unicode symbols and N/S, E/W."""
    self.__post_init__()

    def _conv(deg_float: float, pos: str, neg: str, /) -> str:
      d: float = abs(deg_float)
      degrees = int(d)
      total_min: float = (d - degrees) * 60.0
      minutes = int(total_min)
      seconds: float = round((total_min - minutes) * 60.0, 2)  # 0.01 sec precision = 60cm or less
      if seconds >= 60.0:  # handle carry-over for seconds → minutes
        seconds = 0.0
        minutes += 1
      if minutes >= 60:  # handle carry-over for minutes → degrees
        minutes = 0
        degrees += 1
      hemisphere: str = pos if deg_float >= 0 else neg
      return f'{degrees}°{minutes}′{seconds:0.2f}″{hemisphere}'

    return (_conv(self.latitude, 'N', 'S'), _conv(self.longitude, 'E', 'W'))


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DaysRange:
  """Range of calendar days (supposes start <= end, but doesn't check). Sortable."""
  start: datetime.date
  end: datetime.date

  def __post_init__(self) -> None:
    if self.start > self.end:
      raise Error(f'invalid dates: {self}')

  def __lt__(self, other: Any) -> bool:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, DaysRange):
      raise TypeError(f'invalid DaysRange type comparison {self!r} versus {other!r}')
    if self.start != other.start:
      return self.start < other.start
    return self.end < other.end
