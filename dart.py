#!/usr/bin/env python3
#
# Copyright 2025 Balparda (balparda@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""Dublin DART: data and extensible tables."""

import argparse
import dataclasses
import datetime
import functools
import logging
# import pdb
from typing import Any, Callable, Generator, Iterable, Optional, Union

from baselib import base

import gtfs_data_model as dm
import gtfs

__author__ = 'balparda@github.com'
__version__ = (1, 0)


# defaults
_DEFAULT_DAYS_FRESHNESS = 10
DART_SHORT_NAME = 'DART'
DART_LONG_NAME = 'Bray - Howth'


class Error(gtfs.Error):
  """DART exception."""


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class TrackEndpoints:
  """A track start and end stops."""
  start: str       # stop_times.txt/stop_id (required) -> stops.txt/stop_id
  end: str         # stop_times.txt/stop_id (required) -> stops.txt/stop_id
  direction: bool  # trips.txt/direction_id (required)


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class AgnosticEndpoints:
  """A track extremities (start & stop) but in a fixed (sorted) order."""
  ends: tuple[str, str]  # SORTED!! stop_times.txt/stop_id (required) -> stops.txt/stop_id


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DARTTrackStop:
  """A DART stop."""
  stop: str                       # stop_times.txt/stop_id (required) -> stops.txt/stop_id
  headsign: Optional[str] = None  # stop_times.txt/stop_headsign
  pickup: dm.StopPointType = dm.StopPointType.REGULAR   # stop_times.txt/pickup_type
  dropoff: dm.StopPointType = dm.StopPointType.REGULAR  # stop_times.txt/drop_off_type


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class Track:
  """Collection of stops. A directional shape on the train tracks, basically."""
  direction: bool              # trips.txt/direction_id (required)
  stops: tuple[DARTTrackStop]  # (tuple so it is hashable!)


def SortTracks(tracks: Iterable[Track], stop_namer: Callable[[str], str]) -> list[Track]:
  """Return sorted list of Tracks."""
  comp: Callable[[Track], tuple[bool, str, str]] = lambda t: (
      (t.direction, stop_namer(t.stops[0].stop), stop_namer(t.stops[-1].stop)))
  return sorted(tracks, key=comp)


DART_DIRECTION: Callable[[Union[dm.Trip, TrackEndpoints, Track]], str] = (
    lambda t: 'S' if t.direction else 'N')


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DARTScheduleStop:
  """A DART timetable entry."""
  arrival: int     # stop_times.txt/arrival_time - seconds from midnight, to represent 'HH:MM:SS'   (required)
  departure: int   # stop_times.txt/departure_time - seconds from midnight, to represent 'HH:MM:SS' (required)
  timepoint: bool  # stop_times.txt/timepoint (required) - False==Times are considered approximate; True==Times are considered exact


@functools.total_ordering
@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DARTSchedule(Track):
  """A DART track scheduled (timed) route. A track + timetable, basically."""
  times: tuple[DARTScheduleStop]  # (tuple so it is hashable!)

  def __lt__(self, other: Any) -> Any:
    """Less than. Makes sortable (b/c base class already defines __eq__)."""
    if not isinstance(other, DARTSchedule):
      return NotImplemented
    return self.times[0].departure < other.times[0].departure


def EndpointsFromTrack(track: Track) -> tuple[AgnosticEndpoints, TrackEndpoints]:
  """Builds track endpoints from a track."""
  endpoints = TrackEndpoints(
      start=track.stops[0].stop, end=track.stops[-1].stop, direction=track.direction)
  ordered: tuple[str, str] = (
      (endpoints.start, endpoints.end) if endpoints.end >= endpoints.start else
      (endpoints.end, endpoints.start))
  return (AgnosticEndpoints(ends=ordered), endpoints)


def ScheduleFromTrip(trip: dm.Trip) -> tuple[Track, DARTSchedule]:
  """Builds a schedule object from this particular trip."""
  stops: tuple[DARTTrackStop] = tuple(DARTTrackStop(  # type:ignore
      stop=trip.stops[i].stop,
      headsign=trip.stops[i].headsign,
      pickup=trip.stops[i].pickup,
      dropoff=trip.stops[i].dropoff
  ) for i in range(1, len(trip.stops)))  # this way guarantees we hit every int (seq)
  return (
      Track(
          direction=trip.direction,
          stops=stops,
      ),
      DARTSchedule(
          direction=trip.direction,
          stops=stops,
          times=tuple(DARTScheduleStop(  # type:ignore
              arrival=trip.stops[i].arrival,
              departure=trip.stops[i].departure,
              timepoint=trip.stops[i].timepoint,
          ) for i in range(1, len(trip.stops))),  # this way guarantees we hit every int (seq)
      ),
  )


# @dataclasses.dataclass(kw_only=True, slots=True, frozen=False)  # mutable b/c of dict
# class DARTTrip:
#   """DART trip, deduplicated."""
#   # unique DART "trip"
#   start_stop: str       # (PK) stop_times.txt/stop_id                 (required) -> stops.txt/stop_id
#   start_departure: int  # (PK) stop_times.txt/departure_time - seconds from midnight, to represent 'HH:MM:SS' (required)
#   shape: str            # (PK) trips.txt/shape_id         (required) -> shapes.txt/shape_id
#   # immutable for DART "trip"
#   route: str            # trips.txt/route_id         (required) -> routes.txt/route_id
#   agency: int           # <<INFERRED>> -> agency.txt/agency_id
#   headsign: str         # trips.txt/trip_headsign    (required)
#   direction: bool       # trips.txt/direction_id     (required)
#   stops: dict[int, dm.Stop]  # {stop_times.txt/stop_sequence: Stop}
#   # the many trips in this group
#   rail_trips: dict[int, list[RailTrip]]  # {trips.txt/service_id: RailTrip}


class DART:
  """Dublin DART."""

  def __init__(self, gtfs_obj: gtfs.GTFS) -> None:
    """Constructor."""
    # get DB
    if not gtfs_obj:
      raise Error('Empty GTFS object (database)')
    self._gtfs: gtfs.GTFS = gtfs_obj
    # get DART Agency/Route or die
    dart_agency, dart_route = self._gtfs.FindAgencyRoute(
        gtfs.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL,
        DART_SHORT_NAME, long_name=DART_LONG_NAME)
    if not dart_agency or not dart_route:
      raise gtfs.Error('Database does not have the DART route: maybe run `read` command?')
    self._dart_agency: dm.Agency = dart_agency
    self._dart_route: dm.Route = dart_route
    # group dart trips by track then by schedule then by service
    self._dart_trips: dict[AgnosticEndpoints, dict[TrackEndpoints, dict[Track, dict[DARTSchedule, dict[int, list[dm.Trip]]]]]] = {}
    for trip in dart_route.trips.values():
      track, schedule = ScheduleFromTrip(trip)
      agnostic, endpoints = EndpointsFromTrack(track)
      self._dart_trips.setdefault(agnostic, {}).setdefault(endpoints, {}).setdefault(
          track, {}).setdefault(schedule, {}).setdefault(trip.service, []).append(trip)

  def DARTServices(self) -> set[int]:
    """Set of all DART services."""
    return {t.service for t in self._dart_route.trips.values()}

  def DARTServicesForDay(self, day: datetime.date) -> set[int]:
    """Set of DART services for a single day."""
    return self._gtfs.ServicesForDay(day).intersection(self.DARTServices())

  def TrackRouteName(self, endpoints: TrackEndpoints) -> tuple[str, str]:
    """Gets (name_start, name_end) for a TrackEndpoints object."""
    _, start_name, _ = self._gtfs.StopName(endpoints.start)
    _, end_name, _ = self._gtfs.StopName(endpoints.end)
    if not start_name or not end_name:
      raise Error(f'Invalid codes found in endpoints: {endpoints}')
    return (start_name, end_name)

  def WalkTrips(self) -> Generator[
      tuple[AgnosticEndpoints, TrackEndpoints, Track, DARTSchedule, int, list[dm.Trip]], None, None]:
    """Iterates over all DART trips in a sensible order."""
    # TODO: order is not yet sensible...
    for agnostic, endpoints in self._dart_trips.items():
      for endpoint, tracks in endpoints.items():
        for track, schedules in tracks.items():
          for schedule in sorted(schedules.keys()):
            for service, trips in schedules[schedule].items():
              # for trip in trips:
              yield (agnostic, endpoint, track, schedule, service, trips)


def Main() -> None:
  """Main entry point."""
  # parse the input arguments, add subparser for `command`
  parser: argparse.ArgumentParser = argparse.ArgumentParser()
  command_arg_subparsers = parser.add_subparsers(dest='command')
  # "read" command
  read_parser: argparse.ArgumentParser = command_arg_subparsers.add_parser(
      'read', help='Read DB from official sources')
  read_parser.add_argument(
      '-f', '--freshness', type=int, default=_DEFAULT_DAYS_FRESHNESS,
      help=f'Number of days to cache; 0 == always load (default: {_DEFAULT_DAYS_FRESHNESS})')
  read_parser.add_argument(
      '-r', '--replace', type=int, default=0,
      help='0 == does not load the same version again ; 1 == forces replace version (default: 0)')
  # "print" command
  print_parser: argparse.ArgumentParser = command_arg_subparsers.add_parser(
      'print', help='Print DB')
  print_parser.add_argument(
      '-d', '--day', type=str, default='',
      help='day to consider in "YYYYMMDD" format (default: TODAY/NOW)')
  # ALL commands
  # parser.add_argument(
  #     '-r', '--readonly', type=bool, default=False,
  #     help='If "True" will not save database (default: False)')
  args: argparse.Namespace = parser.parse_args()
  command = args.command.lower().strip() if args.command else ''
  # start
  print(f'{base.TERM_BLUE}{base.TERM_BOLD}***********************************************')
  print(f'**                 {base.TERM_LIGHT_RED}DART DB{base.TERM_BLUE}                   **')
  print('**   balparda@gmail.com (Daniel Balparda)    **')
  print(f'***********************************************{base.TERM_END}')
  success_message: str = f'{base.TERM_WARNING}premature end? user paused?'
  try:
    # open DB
    database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
    # execute the command
    print()
    with base.Timer() as op_timer:
      match command:
        case 'read':
          database.LoadData(
              gtfs.IRISH_RAIL_OPERATOR, gtfs.IRISH_RAIL_LINK,
              freshness=args.freshness, force_replace=bool(args.replace))
        case 'print':
          print()
          dart = DART(database)
          day: datetime.date = gtfs.DATE_OBJ(args.day) if args.day else datetime.date.today()
          print(f'DART @ {day}/{day.weekday()}')
          print()
          dart_services: set[int] = dart.DARTServicesForDay(day)
          print(f'DART services: {sorted(dart_services)}')
          print()
          for _, endpoint, _, schedule, service, trips in dart.WalkTrips():
            if service in dart_services:
              start_name, end_name = dart.TrackRouteName(endpoint)
              print(f'{DART_DIRECTION(endpoint)} {start_name} => {end_name} '
                    f'@ {gtfs.SecondsToHMS(schedule.times[0].departure)} ({service}) : '
                    f'{",".join(t.id for t in trips)}')
          print()
        case _:
          raise NotImplementedError()
      print()
      print()
    print(f'Executed in {base.TERM_GREEN}{op_timer.readable}{base.TERM_END}')
    print()
    success_message = f'{base.TERM_GREEN}success'
  except Exception as err:
    success_message = f'{base.TERM_FAIL}error: {err}'
    raise
  finally:
    print(f'{base.TERM_BLUE}{base.TERM_BOLD}THE END: {success_message}{base.TERM_END}')


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  Main()
