#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
"""Dublin DART: data and extensible tables."""

import argparse
import datetime
import logging
# import pdb
from typing import Callable, Generator, Optional

from baselib import base  # pylint: disable=no-name-in-module
import prettytable

import gtfs_data_model as dm
import gtfs

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__ = (1, 1)


# defaults
_DEFAULT_DAYS_FRESHNESS = 10
DART_SHORT_NAME = 'DART'
DART_LONG_NAME = 'Bray - Howth'

# useful
DART_DIRECTION: Callable[[dm.Trip | dm.TrackEndpoints | dm.Track], str] = (
    lambda t: 'S' if t.direction else 'N')


class Error(gtfs.Error):
  """DART exception."""


def EndpointsFromTrack(track: dm.Track) -> tuple[dm.AgnosticEndpoints, dm.TrackEndpoints]:
  """Builds track endpoints from a track."""
  endpoints = dm.TrackEndpoints(
      start=track.stops[0].stop, end=track.stops[-1].stop, direction=track.direction)
  ordered: tuple[str, str] = (
      (endpoints.start, endpoints.end) if endpoints.end >= endpoints.start else
      (endpoints.end, endpoints.start))
  return (dm.AgnosticEndpoints(ends=ordered), endpoints)


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
    self._dart_trips: dict[dm.AgnosticEndpoints, dict[dm.TrackEndpoints, dict[
        dm.Track, dict[dm.Schedule, dict[int, list[dm.Trip]]]]]] = {}
    for trip in dart_route.trips.values():
      track, schedule = self.ScheduleFromTrip(trip)
      agnostic, endpoints = EndpointsFromTrack(track)
      self._dart_trips.setdefault(agnostic, {}).setdefault(endpoints, {}).setdefault(
          track, {}).setdefault(schedule, {}).setdefault(trip.service, []).append(trip)

  def StopNameTranslator(self, stop_id: str) -> str:
    """Translates a stop ID into a name. If not found raises."""
    name: Optional[str] = self._gtfs.StopName(stop_id)[1]
    if not name:
      raise Error(f'Invalid stop code found: {stop_id}')
    return name

  def ScheduleFromTrip(self, trip: dm.Trip) -> tuple[dm.Track, dm.Schedule]:
    """Builds a schedule object from this particular trip."""
    stops: tuple[dm.TrackStop] = tuple(dm.TrackStop(  # type:ignore
        stop=trip.stops[i].stop,
        name=self.StopNameTranslator(trip.stops[i].stop),  # needs this for sorting later!!
        headsign=trip.stops[i].headsign,
        pickup=trip.stops[i].pickup,
        dropoff=trip.stops[i].dropoff,
    ) for i in range(1, len(trip.stops)))  # this way guarantees we hit every int (seq)
    return (
        dm.Track(
            direction=trip.direction,
            stops=stops,
        ),
        dm.Schedule(
            direction=trip.direction,
            stops=stops,
            times=tuple(dm.ScheduleStop(  # type:ignore
                arrival=trip.stops[i].arrival,
                departure=trip.stops[i].departure,
                timepoint=trip.stops[i].timepoint,
            ) for i in range(1, len(trip.stops))),  # this way guarantees we hit every int (seq)
        ),
    )

  def DARTServices(self) -> set[int]:
    """Set of all DART services."""
    return {t.service for t in self._dart_route.trips.values()}

  def DARTServicesForDay(self, day: datetime.date) -> set[int]:
    """Set of DART services for a single day."""
    return self._gtfs.ServicesForDay(day).intersection(self.DARTServices())

  def WalkTrips(self) -> Generator[
      tuple[dm.AgnosticEndpoints, dm.TrackEndpoints, dm.Track,
            dm.Schedule, int, list[dm.Trip]], None, None]:
    """Iterates over all DART trips in a sensible order."""
    for agnostic, endpoints in self._dart_trips.items():
      for endpoint, tracks in endpoints.items():
        for track, schedules in tracks.items():
          for schedule in sorted(schedules.keys()):
            for service, trips in schedules[schedule].items():
              # for trip in trips:
              yield (agnostic, endpoint, track, schedule, service, trips)

  def DaySchedule(self, day: datetime.date) -> tuple[
      set[int], dict[dm.Schedule, list[tuple[int, dm.Trip]]]]:
    """Schedule for `day`.

    Args:
      day: datetime.date to fetch schedule for

    Returns:
      ({service1, service2, ...}, {schedule: [(service1, trip1), (service2, trip2), ...]})
    """
    dart_services: set[int] = self.DARTServicesForDay(day)
    day_dart_schedule: dict[dm.Schedule, list[tuple[int, dm.Trip]]] = {}
    for _, _, _, schedule, service, trips in self.WalkTrips():
      if service in dart_services:
        day_dart_schedule.setdefault(schedule, []).extend((service, t) for t in trips)
    return (dart_services, day_dart_schedule)


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
          dart_services, day_dart_schedule = dart.DaySchedule(day)
          print(f'DART services: {sorted(dart_services)}')
          print()
          table = prettytable.PrettyTable(['N/S', 'Start', 'End', 'Time', 'Trips'])
          for schedule in sorted(day_dart_schedule.keys()):
            table.add_row([  # type: ignore
                DART_DIRECTION(schedule),
                schedule.stops[0].name,
                schedule.stops[-1].name,
                gtfs.SecondsToHMS(schedule.times[0].departure),
                ', '.join(f'{s}/{t.id}' for s, t in sorted(day_dart_schedule[schedule], key=lambda s: s[0])),
            ])
          print(table)
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
