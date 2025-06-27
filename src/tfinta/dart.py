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
from typing import Generator, TypeVar

from balparda_baselib import base
import prettytable

from . import gtfs_data_model as dm
from . import gtfs

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 3)  # v1.3 - 2025/06/27


# defaults
_DEFAULT_DAYS_FRESHNESS = 10


class Error(gtfs.Error):
  """DART exception."""


_KEY = TypeVar('_KEY')
_VALUE = TypeVar('_VALUE')


def SortedItems(d: dict[_KEY, _VALUE], /) -> Generator[tuple[_KEY, _VALUE], None, None]:
  """Behaves like dict.items() but gets (key, value) pairs sorted by keys."""
  # migrate to def SortedItems[K: Any, V: Any](d: dict[K, V]) -> Generator[tuple[K, V], None, None]
  # as soon as pylance can process PEP 695 syntax
  for key in sorted(d.keys()):  # type: ignore
    yield (key, d[key])


class DART:
  """Dublin DART."""

  def __init__(self, gtfs_obj: gtfs.GTFS, /) -> None:
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

  def ScheduleFromTrip(self, trip: dm.Trip, /) -> tuple[dm.Track, dm.Schedule]:
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

  def ServicesForDay(self, day: datetime.date, /) -> set[int]:
    """Set of DART services for a single day."""
    return self._gtfs.ServicesForDay(day).intersection(self.Services())

  def WalkTrips(self, /, *, filter_services: set[int] | None = None) -> Generator[tuple[
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

  def WalkTrains(self, /, *, filter_services: set[int] | None = None) -> Generator[tuple[
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
    previous_key: tuple[dm.TrackEndpoints, dm.Track, str] | None = None
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

  def StationSchedule(self, stop_id: str, day: datetime.date, /) -> dict[
      tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[tuple[int, dm.Schedule, dm.Trip]]]]:
    """Data for trains in a `stop` for a specific `day`."""
    day_services: set[int] = self.ServicesForDay(day)
    station: dict[tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[tuple[int, dm.Schedule, dm.Trip]]]] = {}
    for _, _, schedule, name, trips_in_train in self.WalkTrains(
        filter_services=day_services):
      for i, stop in enumerate(schedule.stops):
        if stop.stop == stop_id:
          new_key: tuple[str, dm.ScheduleStop] = (schedule.stops[-1].stop, schedule.times[i])
          if new_key in station:
            raise Error(f'Duplicate stop/time {new_key}: NEW {trips_in_train} OLD {station[new_key][1]}')
          station[new_key] = (name, schedule, trips_in_train)
    return station

  ##################################################################################################
  # DART PRETTY PRINTS
  ##################################################################################################

  def PrettyDaySchedule(self, day: datetime.date, /) -> Generator[str, None, None]:
    """Generate a pretty version of a DART day's schedule."""
    if not day:
      raise Error('empty day')
    yield f'{base.TERM_BOLD}{base.TERM_MAGENTA}DART Schedule{base.TERM_END}'
    yield ''
    yield (f'Day:      {base.TERM_BOLD}{base.TERM_YELLOW}{day}{base.TERM_END} '
           f'{base.TERM_BOLD}({dm.DAY_NAME[day.weekday()]}){base.TERM_END}')
    day_services: set[int] = self.ServicesForDay(day)
    yield (f'Services: {base.TERM_BOLD}{base.TERM_YELLOW}'
           f'{", ".join(str(s) for s in sorted(day_services))}{base.TERM_END}')
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.TERM_BOLD}{base.TERM_CYAN}N/S{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Train{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Start{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}End{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Depart Time{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Service/Trip Codes/{base.TERM_END}'
         f'{base.TERM_RED}[\u2605Alt.Times]{base.TERM_END}'])  # ★
    for _, track, schedule, name, trips_in_train in self.WalkTrains(
        filter_services=day_services):
      trip_codes: str = ', '.join(
          f'{s}/{t.id}{"" if sc == schedule else f"/{base.TERM_RED}[\u2605]{base.TERM_END}{base.TERM_BOLD}"}'
          for s, sc, t in sorted(trips_in_train))
      table.add_row([  # type: ignore
          f'{base.TERM_BOLD}{dm.DART_DIRECTION(track)}{base.TERM_END}',
          f'{base.TERM_BOLD}{base.TERM_YELLOW}{name}{base.TERM_END}',
          f'{base.TERM_BOLD}{track.stops[0].name}{base.TERM_END}',
          f'{base.TERM_BOLD}{track.stops[-1].name}{base.TERM_END}',
          f'{base.TERM_BOLD}{base.TERM_YELLOW}{gtfs.SecondsToHMS(schedule.times[0].departure)}{base.TERM_END}',
          f'{base.TERM_BOLD}{trip_codes}{base.TERM_END}',
      ])
    yield from table.get_string().splitlines()  # type:ignore

  def PrettyStationSchedule(self, stop_id: str, day: datetime.date, /) -> Generator[str, None, None]:
    """Generate a pretty version of a DART station (stop) day's schedule."""
    stop_id = stop_id.strip()
    if not day or not stop_id:
      raise Error('empty stop/day')
    stop_name: str = self._gtfs.StopNameTranslator(stop_id)
    yield (f'{base.TERM_MAGENTA}DART Schedule for Station {base.TERM_BOLD}{stop_name} '
           f'- {stop_id}{base.TERM_END}')
    yield ''
    yield (f'Day:          {base.TERM_BOLD}{base.TERM_YELLOW}{day}{base.TERM_END} '
           f'{base.TERM_BOLD}({dm.DAY_NAME[day.weekday()]}){base.TERM_END}')
    day_services: set[int] = self.ServicesForDay(day)
    yield (f'Services:     {base.TERM_BOLD}{base.TERM_YELLOW}'
           f'{", ".join(str(s) for s in sorted(day_services))}{base.TERM_END}')
    day_dart_schedule = self.StationSchedule(stop_id, day)
    destinations: set[str] = {self._gtfs.StopNameTranslator(k[0]) for k in day_dart_schedule}
    yield f'Destinations: {base.TERM_BOLD}{base.TERM_YELLOW}{", ".join(sorted(destinations))}{base.TERM_END}'
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.TERM_BOLD}{base.TERM_CYAN}N/S{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Train{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Destination{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Arrival{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Departure{base.TERM_END}',
         f'{base.TERM_BOLD}{base.TERM_CYAN}Service/Trip Codes/{base.TERM_END}'
         f'{base.TERM_RED}[\u2605Alt.Times]{base.TERM_END}'])  # ★
    last_arrival: int = 0
    last_departure: int = 0
    for dest, time in sorted(day_dart_schedule.keys(), key=lambda k: (k[1], k[0])):
      name, schedule, trips_in_train = day_dart_schedule[(dest, time)]
      if time.arrival < last_arrival or time.departure < last_departure:
        # make sure both arrival and departures are strictly moving forward
        raise Error(f'time moved backwards in schedule @ {dest} / {time}')
      trip_codes: str = ', '.join(
          f'{s}/{t.id}{"" if sc == schedule else f"/{base.TERM_RED}[\u2605]{base.TERM_END}{base.TERM_BOLD}"}'
          for s, sc, t in sorted(trips_in_train))
      table.add_row([  # type: ignore
          f'{base.TERM_BOLD}{dm.DART_DIRECTION(trips_in_train[0][2])}{base.TERM_END}',
          f'{base.TERM_BOLD}{base.TERM_YELLOW}{name}{base.TERM_END}',
          f'{base.TERM_BOLD}{base.TERM_YELLOW}{schedule.stops[-1].name}{base.TERM_END}',
          f'{base.TERM_BOLD}{gtfs.SecondsToHMS(time.arrival)}{base.TERM_END}',
          f'{base.TERM_BOLD}{base.TERM_YELLOW}{gtfs.SecondsToHMS(time.departure)}{base.TERM_END}',
          f'{base.TERM_BOLD}{trip_codes}{base.TERM_END}',
      ])
      last_arrival, last_departure = time.arrival, time.departure
    yield from table.get_string().splitlines()  # type:ignore

  def PrettyPrintTrip(self, trip_name: str, /) -> Generator[str, None, None]:  # pylint: disable=too-many-locals
    """Generate a pretty version of a train (physical) trip, may be 2 Trips."""
    trip_name = trip_name.strip().upper()
    if not trip_name:
      raise Error('empty trip name/code')
    # get the trips for this name
    trains: dict[dm.Schedule, dict[int, list[dm.Trip]]] = {}
    trip: dm.Trip
    for _, _, _, name, trips_in_train in self.WalkTrains():
      if name.upper() != trip_name:
        continue
      for service, schedule, trip in trips_in_train:
        trains.setdefault(schedule, {}).setdefault(service, []).append(trip)
    if not trains:
      raise Error(f'trip name/code {trip_name!r} was not found')
    trips: list[dm.Trip] = [trip for schedule in sorted(trains.keys())
                            for service in sorted(trains[schedule].keys())
                            for trip in trains[schedule][service]]
    yield f'{base.TERM_MAGENTA}DART Trip {base.TERM_BOLD}{trip_name}{base.TERM_END}'
    yield ''
    # check for unexpected things that should not happen
    n_stops: int = len(trips[0].stops)
    for trip in trips[1:]:
      if (trips[0].route != trip.route or
          trips[0].agency != trip.agency or
          trips[0].direction != trip.direction or
          trips[0].headsign != trip.headsign or
          trips[0].name != trip.name):
        raise Error(
            f'route/agency/direction/headsign/name should be consistent: {trips[0]} versus {trip}')
      if n_stops != (n_trip := len(trip.stops)):
        raise Error(f'All trips should be the same size: {n_stops} versus {n_trip}')
    # print the static stuff
    agency, route, _ = self._gtfs.FindTrip(trips[0].id)
    if not agency or not route:
      raise Error(f'trip id {trips[0].id!r} was not found')
    yield f'Agency:        {base.TERM_BOLD}{base.TERM_YELLOW}{agency.name}{base.TERM_END}'
    yield f'Route:         {base.TERM_BOLD}{base.TERM_YELLOW}{route.id}{base.TERM_END}'
    yield f'  Short name:  {base.TERM_BOLD}{base.TERM_YELLOW}{route.short_name}{base.TERM_END}'
    yield f'  Long name:   {base.TERM_BOLD}{base.TERM_YELLOW}{route.long_name}{base.TERM_END}'
    yield (f'  Description: {base.TERM_BOLD}'
           f'{route.description if route.description else dm.NULL_TEXT}{base.TERM_END}')
    yield (f'Direction:     {base.TERM_BOLD}{base.TERM_YELLOW}'
           f'{"inbound" if trips[0].direction else "outbound"}{base.TERM_END}')
    yield (f'Headsign:      {base.TERM_BOLD}{trips[0].headsign if trips[0].headsign else dm.NULL_TEXT}'
           f'{base.TERM_END}')
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.TERM_BOLD}{base.TERM_CYAN}Trip ID{base.TERM_END}'] +
        [f'{base.TERM_BOLD}{base.TERM_MAGENTA}{t.id}{base.TERM_END}' for t in trips])
    # add the properties that are variable
    table.add_row(
        [f'{base.TERM_BOLD}{base.TERM_CYAN}Service{base.TERM_END}'] +
        [f'{base.TERM_BOLD}{base.TERM_YELLOW}{trip.service}{base.TERM_END}' for trip in trips])
    table.add_row(
        [f'{base.TERM_BOLD}{base.TERM_CYAN}Shape{base.TERM_END}'] +
        [(f'{base.TERM_BOLD}{trip.shape}{base.TERM_END}' if trip.shape else dm.NULL_TEXT)
         for trip in trips])
    table.add_row(
        [f'{base.TERM_BOLD}{base.TERM_CYAN}Block{base.TERM_END}'] +
        [(f'{base.TERM_BOLD}{dm.LIMITED_TEXT(trip.block, 10)}{base.TERM_END}'
          if trip.block else dm.NULL_TEXT) for trip in trips])
    table.add_row(
        [f'{base.TERM_BOLD}{base.TERM_CYAN}#{base.TERM_END}'] +
        [f'{base.TERM_BOLD}{base.TERM_CYAN}Stop{base.TERM_END}\n'
         f'{base.TERM_BOLD}{base.TERM_CYAN}Dropoff{base.TERM_END}\n'
         f'{base.TERM_BOLD}{base.TERM_CYAN}Pickup{base.TERM_END}'] * len(trips))
    # add the stops
    for seq in range(1, n_stops + 1):
      table_row: list[str] = [f'{base.TERM_BOLD}{base.TERM_CYAN}{seq}{base.TERM_END}']
      for trip in trips:
        stop: dm.Stop = trip.stops[seq]
        table_row.append(
            f'{base.TERM_BOLD}{base.TERM_YELLOW}'
            f'{dm.LIMITED_TEXT(self._gtfs.StopNameTranslator(stop.stop), 10)}{base.TERM_END}\n'
            f'{base.TERM_BOLD}{gtfs.SecondsToHMS(stop.scheduled.arrival)}'
            f'{dm.STOP_TYPE_STR[stop.dropoff]}{base.TERM_END}\n'
            f'{base.TERM_BOLD}{gtfs.SecondsToHMS(stop.scheduled.departure)}'
            f'{dm.STOP_TYPE_STR[stop.pickup]}{base.TERM_END}')
      table.add_row(table_row)
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # type:ignore


def main(argv: list[str] | None = None) -> int:  # pylint: disable=invalid-name,too-many-locals
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
  trips_parser: argparse.ArgumentParser = print_arg_subparsers.add_parser(
      'trips', help='Print Trips')
  trips_parser.add_argument(
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
  trip_parser: argparse.ArgumentParser = print_arg_subparsers.add_parser(
      'trip', help='Print DART Trip')
  trip_parser.add_argument(
      '-c', '--code', type=str, default='', help='DART train code, like "E108" for example')
  # ALL commands
  # parser.add_argument(
  #     '-r', '--readonly', type=bool, default=False,
  #     help='If "True" will not save database (default: False)')
  args: argparse.Namespace = parser.parse_args(argv)
  command = args.command.lower().strip() if args.command else ''
  database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
  # look at main command
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
      print()
      match print_command:
        case 'trips':
          # trips for a day
          for line in dart.PrettyDaySchedule(
              dm.DATE_OBJ(args.day) if args.day else datetime.date.today()):
            print(line)
        case 'station':
          # station chart for a day
          for line in dart.PrettyStationSchedule(
              database.StopIDFromNameFragmentOrID(args.station),
              dm.DATE_OBJ(args.day) if args.day else datetime.date.today()):
            print(line)
        case 'trip':
          # DART trip
          for line in dart.PrettyPrintTrip(args.code):
            print(line)
        case _:
          raise NotImplementedError()
      print()
    case _:
      raise NotImplementedError()
  return 0


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  sys.exit(main())
