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
from typing import Generator, Optional, TypeVar

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


_KEY = TypeVar('_KEY')
_VALUE = TypeVar('_VALUE')


def SortedItems(d: dict[_KEY, _VALUE]) -> Generator[tuple[_KEY, _VALUE], None, None]:
  """Behaves like dict.items() but gets (key, value) pairs sorted by keys."""
  # migrate to def SortedItems[K: Any, V: Any](d: dict[K, V]) -> Generator[tuple[K, V], None, None]
  # as soon as pylance can process PEP 695 syntax
  for key in sorted(d.keys()):  # type: ignore
    yield (key, d[key])


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
    self._dart_services_count: dict[int, int] = {}  # {service: count(trips)}
    for trip in self._dart_route.trips.values():
      track, schedule = self.ScheduleFromTrip(trip)
      endpoints: dm.TrackEndpoints = dm.EndpointsFromTrack(track)[1]
      if not trip.name:
        raise Error(f'empty trip name: {trip}')
      self._dart_trips.setdefault(endpoints, {}).setdefault(
          track, {}).setdefault(trip.name, {}).setdefault(trip.service, {}).setdefault(
              schedule, []).append(trip)
      self._dart_services_count[trip.service] = self._dart_services_count.get(trip.service, 0) + 1
    # count them: we can't have lost any, or we need to investigate!
    if (total_trips := len(self._dart_route.trips)) != (collected_trips := sum(
        len(trips)
        for tracks in self._dart_trips.values()
        for names in tracks.values()
        for services in names.values()
        for schedules in services.values()
        for trips in schedules.values())) or total_trips != sum(self._dart_services_count.values()):
      raise Error(
          f'DART route has {total_trips} trips, but only {collected_trips} in structure '
          f'and {self._dart_services_count}')

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
            times=tuple(  # type:ignore
                # this way guarantees we hit every int (seq)
                trip.stops[i].scheduled for i in range(1, len(trip.stops) + 1)),
        ),
    )

  def Services(self) -> set[int]:
    """Set of all DART services."""
    return {t.service for t in self._dart_route.trips.values()}

  def ServicesForDay(self, day: datetime.date) -> set[int]:
    """Set of DART services for a single day."""
    return self._gtfs.ServicesForDay(day).intersection(self.Services())

  def WalkTrips(self, filter_services: Optional[set[int]] = None) -> Generator[tuple[
      dm.TrackEndpoints, dm.Track, str, int, dm.Schedule, dm.Trip], None, None]:
    """Iterates over all DART trips in a sensible order."""
    for endpoint, track_map in SortedItems(self._dart_trips):  # pylint: disable=too-many-nested-blocks
      for track, name_map in SortedItems(track_map):
        for name, service_map in SortedItems(name_map):
          for service, schedule_map in SortedItems(service_map):
            if not filter_services or service in filter_services:
              for schedule, trip_list in SortedItems(schedule_map):
                for trip in trip_list:
                  yield (endpoint, track, name, service, schedule, trip)

  def WalkTrains(self, filter_services: Optional[set[int]] = None) -> Generator[tuple[
      dm.TrackEndpoints, dm.Track, dm.Schedule, str,
      list[tuple[int, dm.Schedule, dm.Trip]]], None, None]:
    """Iterates over actual physical DART trains in a sensible order.

    DART behaves oddly:
    (1) After you group by the obvious things a single train will do (agnostic, endpoint, track)
        a single DART train can only be unique looking at Trip.name (trips.txt/trip_short_name);
        the documentation for GTFS states "a trip_short_name value, if provided, should uniquely
        identify a trip within a service day" and DART seems to use this a lot;
    (2) Two physically identical "trips" (i.e. a single "train") can have 2 slightly diverging
        Schedules (i.e. timetables); they may start the same and diverge (usually by 2 to 10 min)
        or they may start diverged and converge; this is why the "canonical" Schedule will be
        the "min()" of the schedules, i.e. the first to depart, the "smaller" in time
    """
    # go over the trips (self.WalkTrips) and bucket by trip.name, which is a physical DART train
    key: tuple[dm.TrackEndpoints, dm.Track, str]
    previous_key: Optional[tuple[dm.TrackEndpoints, dm.Track, str]] = None
    trips_in_train: list[tuple[int, dm.Schedule, dm.Trip]] = []
    schedules_in_train: set[dm.Schedule] = set()
    for endpoint, track, name, service, schedule, trip in self.WalkTrips(
        filter_services=filter_services):
      key = (endpoint, track, name)
      if key == previous_key:
        # same name (same train)
        trips_in_train.append((service, schedule, trip))
        schedules_in_train.add(schedule)
      else:
        # new name (different train)
        if previous_key and trips_in_train and schedules_in_train:
          yield (
              previous_key[0], previous_key[1], min(schedules_in_train), previous_key[2],  # pylint: disable=unsubscriptable-object
              sorted(trips_in_train))
        trips_in_train = [(service, schedule, trip)]
        schedules_in_train = {schedule}
        previous_key = key
    # make sure we return last one
    if previous_key and trips_in_train and schedules_in_train:
      yield (
          previous_key[0], previous_key[1],
          min(schedules_in_train), previous_key[2], sorted(trips_in_train))

  ##################################################################################################
  # DART PRETTY PRINTS
  ##################################################################################################

  def PrettyDaySchedule(self, day: datetime.date) -> Generator[str, None, None]:
    """Generate a pretty version of a DART day's schedule."""
    if not day:
      raise Error('empty day')
    yield 'DART Schedule'
    yield f'Day:      {day} ({dm.DAY_NAME[day.weekday()]})'
    day_services: set[int] = self.ServicesForDay(day)
    yield f'Services: {tuple(sorted(day_services))}'
    yield ''
    table = prettytable.PrettyTable(
        ['N/S', 'Start', 'End', 'Depart Time', 'Train', 'Service/Trip Codes/[*Alt.Times]'])
    for _, track, schedule, name, trips_in_train in self.WalkTrains(
        filter_services=day_services):
      table.add_row([  # type: ignore
          dm.DART_DIRECTION(track),
          track.stops[0].name,
          track.stops[-1].name,
          gtfs.SecondsToHMS(schedule.times[0].departure),
          name,
          ', '.join(f'{s}/{t.id}{"" if sc == schedule else "/[*]"}'
                    for s, sc, t in sorted(trips_in_train)),
      ])
    yield from table.get_string().splitlines()  # type:ignore


def main(argv: Optional[list[str]] = None) -> int:  # pylint: disable=invalid-name,too-many-locals
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
  print_arg_subparsers = print_parser.add_subparsers(dest='print_command')
  trip_parser: argparse.ArgumentParser = print_arg_subparsers.add_parser(
      'trips', help='Print Trips')
  trip_parser.add_argument(
      '-d', '--day', type=str, default='',
      help='day to consider in "YYYYMMDD" format (default: TODAY/NOW)')
  station_parser: argparse.ArgumentParser = print_arg_subparsers.add_parser(
      'station', help='Print Station Chart')
  station_parser.add_argument(
      '-s', '--station', type=str, default='',
      help='station to print chart for; finds by ID (stops.txt/stop_id) or by name (stop_name)')
  station_parser.add_argument(
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
          # look at sub-command for print
          print_command = args.print_command.lower().strip() if args.print_command else ''
          dart = DART(database)
          match print_command:
            case 'trips':
              # trips for a day
              for line in dart.PrettyDaySchedule(
                  dm.DATE_OBJ(args.day) if args.day else datetime.date.today()):
                print(line)
            case 'station':
              # station chart for a day
              raise NotImplementedError()
              # for line in dart.PrettyStationSchedule(
              #     database.StopIDFromNameFragmentOrID(args.station),
              #     dm.DATE_OBJ(args.day) if args.day else datetime.date.today()):
              #   print(line)
            case _:
              raise NotImplementedError()
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
