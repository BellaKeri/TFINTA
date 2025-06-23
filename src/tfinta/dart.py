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
import sys
from typing import Generator, Optional

from balparda_baselib import base
import prettytable

from . import gtfs_data_model as dm
from . import gtfs

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__ = (1, 1)


# defaults
_DEFAULT_DAYS_FRESHNESS = 10


class Error(gtfs.Error):
  """DART exception."""


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
        dm.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL,
        dm.DART_SHORT_NAME, long_name=dm.DART_LONG_NAME)
    if not dart_agency or not dart_route:
      raise gtfs.Error('Database does not have the DART route: maybe run `read` command?')
    self._dart_agency: dm.Agency = dart_agency
    self._dart_route: dm.Route = dart_route
    # group dart trips by track then by schedule then by service
    self._dart_trips: dm.CondensedTrips = {}
    for trip in dart_route.trips.values():
      track, schedule = self.ScheduleFromTrip(trip)
      agnostic, endpoints = dm.EndpointsFromTrack(track)
      self._dart_trips.setdefault(agnostic, {}).setdefault(endpoints, {}).setdefault(
          track, {}).setdefault(schedule, {}).setdefault(trip.service, []).append(trip)

  def ScheduleFromTrip(self, trip: dm.Trip) -> tuple[dm.Track, dm.Schedule]:
    """Builds a schedule object from this particular trip."""
    stops: tuple[dm.TrackStop] = tuple(dm.TrackStop(  # type:ignore
        stop=trip.stops[i].stop,
        name=self._gtfs.StopNameTranslator(trip.stops[i].stop),  # needs this for sorting later!!
        headsign=trip.stops[i].headsign,
        pickup=trip.stops[i].pickup,
        dropoff=trip.stops[i].dropoff,
    ) for i in range(1, len(trip.stops) + 1))  # this way guarantees we hit every int (seq)
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
            ) for i in range(1, len(trip.stops) + 1)),  # this way guarantees we hit every int (seq)
        ),
    )

  def Services(self) -> set[int]:
    """Set of all DART services."""
    return {t.service for t in self._dart_route.trips.values()}

  def ServicesForDay(self, day: datetime.date) -> set[int]:
    """Set of DART services for a single day."""
    return self._gtfs.ServicesForDay(day).intersection(self.Services())

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
    dart_services: set[int] = self.ServicesForDay(day)
    day_dart_schedule: dict[dm.Schedule, list[tuple[int, dm.Trip]]] = {}
    for _, _, _, schedule, service, trips in self.WalkTrips():
      if service in dart_services:
        day_dart_schedule.setdefault(schedule, []).extend((service, t) for t in trips)
    return (dart_services, day_dart_schedule)

  ##################################################################################################
  # DART PRETTY PRINTS
  ##################################################################################################

  def PrettyDaySchedule(self, day: datetime.date) -> Generator[str, None, None]:
    """Generate a pretty version of a DART day's schedule."""
    if not day:
      raise Error('empty day')
    yield 'DART Schedule'
    yield f'Day:      {day} ({dm.DAY_NAME[day.weekday()]})'
    dart_services, day_dart_schedule = self.DaySchedule(day)
    yield f'Services: {tuple(sorted(dart_services))}'
    yield ''
    table = prettytable.PrettyTable(['N/S', 'Start', 'End', 'Depart Time', 'Trip Codes'])
    for schedule in sorted(day_dart_schedule.keys()):
      table.add_row([  # type: ignore
          dm.DART_DIRECTION(schedule),
          schedule.stops[0].name,
          schedule.stops[-1].name,
          gtfs.SecondsToHMS(schedule.times[0].departure),
          ', '.join(f'{s}/{t.id}' for s, t in sorted(
              day_dart_schedule[schedule], key=lambda s: s[0])),
      ])
    yield from table.get_string().splitlines()  # type:ignore


def main(argv: Optional[list[str]] = None) -> int:  # pylint: disable=invalid-name
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
  args: argparse.Namespace = parser.parse_args(argv)
  command = args.command.lower().strip() if args.command else ''
  # start
  print(f'{base.TERM_BLUE}{base.TERM_BOLD}***********************************************')
  print(f'**                 {base.TERM_LIGHT_RED}DART DB{base.TERM_BLUE}                   **')
  print('**   balparda@github.com (Daniel Balparda)   **')
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
              dm.IRISH_RAIL_OPERATOR, dm.IRISH_RAIL_LINK,
              allow_unknown_file=True, allow_unknown_field=False,
              freshness=args.freshness, force_replace=bool(args.replace), override=None)
        case 'print':
          print()
          dart = DART(database)
          for line in dart.PrettyDaySchedule(
              dm.DATE_OBJ(args.day) if args.day else datetime.date.today()):
            print(line)
        case _:
          raise NotImplementedError()
      print()
      print()
    print(f'Executed in {base.TERM_GREEN}{op_timer.readable}{base.TERM_END}')
    print()
    success_message = f'{base.TERM_GREEN}success'
    return 0
  except Exception as err:
    success_message = f'{base.TERM_FAIL}error: {err}'
    raise
  finally:
    print(f'{base.TERM_BLUE}{base.TERM_BOLD}THE END: {success_message}{base.TERM_END}')


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  sys.exit(main())
