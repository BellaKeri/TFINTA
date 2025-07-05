#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
"""Dublin DART: data and extensible tables."""

import argparse
import collections
import copy
import datetime
import logging
# import pdb
import sys
from typing import Generator, TypeVar

import prettytable

from . import tfinta_base as base
from . import gtfs_data_model as dm
from . import gtfs

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = base.__version__


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
    # group DART trips by name
    trains: dict[str, list[tuple[int, dm.Schedule, dm.Trip]]] = {}
    for trip in self._dart_route.trips.values():
      if not trip.name:
        raise Error(f'empty trip name: {trip.id}')
      schedule: dm.Schedule = self.ScheduleFromTrip(trip)
      if (n_stops := len(schedule.stops)) < 2 or len(schedule.times) < 2:
        raise Error(f'trip {trip.id} has fewer than 2 stops: {n_stops}')
      trains.setdefault(trip.name, []).append((trip.service, schedule, trip))
    # get train code names and find an ordering
    trip_names: list[tuple[dm.Schedule, str]] = list(
        (min(s for _, s, _ in tr), n) for n, tr in trains.items())
    trip_names.sort()
    # create ordered dict to preserve sorted train codes
    self._dart_trips: collections.OrderedDict[
        str, list[tuple[int, dm.Schedule, dm.Trip]]] = collections.OrderedDict()
    for _, name in trip_names:
      self._dart_trips[name] = sorted(trains[name], key=lambda t: (t[1], t[0]))  # also sort the values!

  def ScheduleFromTrip(self, trip: dm.Trip, /) -> dm.Schedule:
    """Builds a schedule object from this particular trip."""
    stops: tuple[dm.TrackStop] = tuple(dm.TrackStop(  # type:ignore
        stop=trip.stops[i].stop,
        name=self._gtfs.StopNameTranslator(trip.stops[i].stop),  # needs this for sorting later!!
        headsign=trip.stops[i].headsign,
        pickup=trip.stops[i].pickup,
        dropoff=trip.stops[i].dropoff,
    ) for i in range(1, len(trip.stops) + 1))  # this way guarantees we hit every int (seq)
    return dm.Schedule(
        direction=trip.direction,
        stops=stops,
        times=tuple(  # type:ignore
            # this way guarantees we hit every int (seq)
            trip.stops[i].scheduled for i in range(1, len(trip.stops) + 1)))

  def Services(self) -> set[int]:
    """Set of all DART services."""
    return {t.service for t in self._dart_route.trips.values()}

  def ServicesForDay(self, day: datetime.date, /) -> set[int]:
    """Set of DART services for a single day."""
    return self._gtfs.ServicesForDay(day).intersection(self.Services())

  def WalkTrains(self, /, *, filter_services: set[int] | None = None) -> Generator[tuple[
      dm.Schedule, str, list[tuple[int, dm.Schedule, dm.Trip]]], None, None]:
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
    # collect the trains that are actually running today
    filtered_trains: list[tuple[dm.Schedule, str, list[tuple[int, dm.Schedule, dm.Trip]]]] = []
    for name, trips in self._dart_trips.items():
      filtered_trips: list[tuple[int, dm.Schedule, dm.Trip]] = [
          t for t in trips if (filter_services is None or t[0] in filter_services)]
      if not filtered_trips:
        continue  # this train code has no trip today
      filtered_trains.append(
          (min(s for _, s, _ in filtered_trips), name,
           sorted(filtered_trips, key=lambda t: (t[1], t[0]))))
    yield from sorted(filtered_trains, key=lambda t: (  # re-sort by:
        t[0].direction,                 # North/South
        t[0].stops[0].name,             # start stop
        t[0].stops[-1].name,            # destination stop
        t[0].times[0].times.departure,  # HH:MM:SS as seconds
        t[1],                           # tie-break with the train code (E800, ...)
    ))

  def StationSchedule(self, stop_id: str, day: datetime.date, /) -> dict[
      tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[tuple[int, dm.Schedule, dm.Trip]]]]:
    """Data for trains in a `stop` for a specific `day`."""
    station: dict[tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[tuple[int, dm.Schedule, dm.Trip]]]] = {}
    for schedule, name, trips_in_train in self.WalkTrains(filter_services=self.ServicesForDay(day)):
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

  def PrettyPrintCalendar(self) -> Generator[str, None, None]:
    """Generate a pretty version of calendar data."""
    yield from self._gtfs.PrettyPrintCalendar(filter_to=self.Services())

  def PrettyPrintStops(self) -> Generator[str, None, None]:
    """Generate a pretty version of the stops."""
    all_stops: set[str] = {stop.stop for _, _, trips in self.WalkTrains()
                           for _, _, trip in trips
                           for stop in trip.stops.values()}
    yield from self._gtfs.PrettyPrintStops(filter_to=all_stops)

  def PrettyDaySchedule(self, /, *, day: datetime.date) -> Generator[str, None, None]:
    """Generate a pretty version of a DART day's schedule."""
    if not day:
      raise Error('empty day')
    yield f'{base.BOLD}{base.MAGENTA}DART Schedule{base.NULL}'
    yield ''
    yield (f'Day:      {base.BOLD}{base.YELLOW}{day}{base.NULL} '
           f'{base.BOLD}({base.DAY_NAME[day.weekday()]}){base.NULL}')
    day_services: set[int] = self.ServicesForDay(day)
    yield (f'Services: {base.BOLD}{base.YELLOW}'
           f'{", ".join(str(s) for s in sorted(day_services))}{base.NULL}')
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.BOLD}{base.CYAN}N/S{base.NULL}',
         f'{base.BOLD}{base.CYAN}Train{base.NULL}',
         f'{base.BOLD}{base.CYAN}Start{base.NULL}',
         f'{base.BOLD}{base.CYAN}End{base.NULL}',
         f'{base.BOLD}{base.CYAN}Depart Time{base.NULL}',
         f'{base.BOLD}{base.CYAN}Service/Trip Codes/{base.NULL}'
         f'{base.RED}[\u2605Alt.Times]{base.NULL}'])  # ★
    for schedule, name, trips_in_train in self.WalkTrains(filter_services=day_services):
      trip_codes: str = ', '.join(
          f'{s}/{t.id}{"" if sc == schedule else f"/{base.RED}[★]{base.NULL}{base.BOLD}"}'
          for s, sc, t in trips_in_train)
      table.add_row([  # type: ignore
          f'{base.BOLD}{dm.DART_DIRECTION(schedule)}{base.NULL}',
          f'{base.BOLD}{base.YELLOW}{name}{base.NULL}',
          f'{base.BOLD}{schedule.stops[0].name}{base.NULL}',
          f'{base.BOLD}{schedule.stops[-1].name}{base.NULL}',
          f'{base.BOLD}{base.YELLOW}'
          f'{schedule.times[0].times.departure.ToHMS() if schedule.times[0].times.departure else base.NULL_TEXT}'
          f'{base.NULL}',
          f'{base.BOLD}{trip_codes}{base.NULL}',
      ])
    yield from table.get_string().splitlines()  # type:ignore

  def PrettyStationSchedule(self, /, *, stop_id: str, day: datetime.date) -> Generator[str, None, None]:  # pylint: disable=too-many-locals
    """Generate a pretty version of a DART station (stop) day's schedule."""
    stop_id = stop_id.strip()
    if not day or not stop_id:
      raise Error('empty stop/day')
    stop_name: str = self._gtfs.StopNameTranslator(stop_id)
    yield (f'{base.MAGENTA}DART Schedule for Station {base.BOLD}{stop_name} '
           f'- {stop_id}{base.NULL}')
    yield ''
    yield (f'Day:          {base.BOLD}{base.YELLOW}{day}{base.NULL} '
           f'{base.BOLD}({base.DAY_NAME[day.weekday()]}){base.NULL}')
    day_services: set[int] = self.ServicesForDay(day)
    yield (f'Services:     {base.BOLD}{base.YELLOW}'
           f'{", ".join(str(s) for s in sorted(day_services))}{base.NULL}')
    day_dart_schedule: dict[tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[
        tuple[int, dm.Schedule, dm.Trip]]]] = self.StationSchedule(stop_id, day)
    destinations: set[str] = {self._gtfs.StopNameTranslator(k[0]) for k in day_dart_schedule}
    yield f'Destinations: {base.BOLD}{base.YELLOW}{", ".join(sorted(destinations))}{base.NULL}'
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.BOLD}{base.CYAN}N/S{base.NULL}',
         f'{base.BOLD}{base.CYAN}Train{base.NULL}',
         f'{base.BOLD}{base.CYAN}Destination{base.NULL}',
         f'{base.BOLD}{base.CYAN}Arrival{base.NULL}',
         f'{base.BOLD}{base.CYAN}Departure{base.NULL}',
         f'{base.BOLD}{base.CYAN}Service/Trip Codes/{base.NULL}'
         f'{base.RED}[\u2605Alt.Times]{base.NULL}'])  # ★
    last_arrival: int = 0
    last_departure: int = 0
    for dest, tm in sorted(day_dart_schedule.keys(), key=lambda k: (k[1], k[0])):
      name, schedule, trips_in_train = day_dart_schedule[(dest, tm)]
      if ((tm.times.arrival and tm.times.arrival.time < last_arrival) or
          (tm.times.departure and tm.times.departure.time < last_departure)):
        # make sure both arrival and departures are strictly moving forward
        raise Error(f'time moved backwards in schedule @ {dest} / {tm}')
      trip_codes: str = ', '.join(
          f'{s}/{t.id}{"" if sc == schedule else f"/{base.RED}[★]{base.NULL}{base.BOLD}"}'
          for s, sc, t in sorted(trips_in_train))
      table.add_row([  # type: ignore
          f'{base.BOLD}{dm.DART_DIRECTION(trips_in_train[0][2])}{base.NULL}',
          f'{base.BOLD}{base.YELLOW}{name}{base.NULL}',
          f'{base.BOLD}{base.YELLOW}{schedule.stops[-1].name}{base.NULL}',
          f'{base.BOLD}'
          f'{tm.times.arrival.ToHMS() if tm.times.arrival else base.NULL_TEXT}{base.NULL}',
          f'{base.BOLD}{base.YELLOW}'
          f'{tm.times.departure.ToHMS() if tm.times.departure else base.NULL_TEXT}{base.NULL}',
          f'{base.BOLD}{trip_codes}{base.NULL}',
      ])
      last_arrival = tm.times.arrival.time if tm.times.arrival else 0
      last_departure = tm.times.departure.time if tm.times.departure else 0
    yield from table.get_string().splitlines()  # type:ignore

  def PrettyPrintTrip(self, /, *, trip_name: str) -> Generator[str, None, None]:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Generate a pretty version of a train (physical) trip, may be 2 Trips."""
    # get the trips for this name
    trip_name = trip_name.strip()
    trains: list[tuple[int, dm.Schedule, dm.Trip]] = self._dart_trips.get(trip_name, [])
    trips: list[dm.Trip] = [t for _, _, t in trains]
    if not trip_name or not trains or not trips:
      raise Error(f'invalid trip name/code {trip_name!r}')
    # gather the start/end stops for the longest trip
    trip: dm.Trip
    n_stops: int = 0
    min_stop: str | None = None
    max_stop: str | None = None
    for _, _, trip in trains:
      if (len_trip := len(trip.stops)) > n_stops:
        n_stops, min_stop, max_stop = len_trip, trip.stops[1].stop, trip.stops[len_trip].stop
    yield f'{base.MAGENTA}DART Trip {base.BOLD}{trip_name}{base.NULL}'
    yield ''
    # check for unexpected things that should not happen and pad trips that are shorter
    padded_trips: list[dm.Trip] = []
    for trip in trips:
      if (trips[0].route != trip.route or
          trips[0].agency != trip.agency or
          trips[0].headsign != trip.headsign or
          trips[0].name != trip.name):
        raise Error(
            'route/agency/headsign/name should be consistent '
            f'{trip_name!r}: {trips[0]} versus {trip}')
      if n_stops != (n_trip := len(trip.stops)):
        n_missing: int = n_stops - n_trip
        new_trip: dm.Trip = copy.deepcopy(trip)
        if trip.stops[1].stop == min_stop:
          # stops are aligned with beginning of longest trips, example 'E947'
          for _ in range(n_missing):
            new_trip.stops[max(new_trip.stops) + 1] = dm.NULL_STOP
        elif trip.stops[len(trip.stops)].stop == max_stop:
          # stops are aligned with end of longest trips, example 'E400'/'E720'
          for i in sorted(new_trip.stops, reverse=True):
            new_trip.stops[i + n_missing] = new_trip.stops[i]
            del new_trip.stops[i]
          for i in range(n_missing):
            new_trip.stops[i + 1] = dm.NULL_STOP
        else:
          raise Error(
              f'Could not find alignment, missing {n_missing} @ {trip_name!r}/{min_stop=}'
              f'/{max_stop=}: {[s.stop for s in trip.stops.values()]}')
        padded_trips.append(new_trip)
      else:
        # size is already max, we just copy
        padded_trips.append(trip)
    trips = padded_trips
    # print the static stuff
    agency, route, _ = self._gtfs.FindTrip(trips[0].id)
    if not agency or not route:
      raise Error(f'trip id {trips[0].id!r} was not found ({trip_name!r})')
    yield f'Agency:        {base.BOLD}{base.YELLOW}{agency.name}{base.NULL}'
    yield f'Route:         {base.BOLD}{base.YELLOW}{route.id}{base.NULL}'
    yield f'  Short name:  {base.BOLD}{base.YELLOW}{route.short_name}{base.NULL}'
    yield f'  Long name:   {base.BOLD}{base.YELLOW}{route.long_name}{base.NULL}'
    yield (f'  Description: {base.BOLD}'
           f'{route.description if route.description else base.NULL_TEXT}{base.NULL}')
    yield (f'Headsign:      {base.BOLD}{trips[0].headsign if trips[0].headsign else base.NULL_TEXT}'
           f'{base.NULL}')
    yield ''
    table = prettytable.PrettyTable(
        [f'{base.BOLD}{base.CYAN}Trip ID{base.NULL}'] +
        [f'{base.BOLD}{base.MAGENTA}{t.id}{base.NULL}' for t in trips])
    # add the properties that are variable
    table.add_row(
        [f'{base.BOLD}{base.CYAN}Service{base.NULL}'] +
        [f'{base.BOLD}{base.YELLOW}{trip.service}{base.NULL}' for trip in trips])
    table.add_row(
        # direction can vary, example 'E725'
        [f'{base.BOLD}{base.CYAN}N/S{base.NULL}'] +
        [f'{base.BOLD}{dm.DART_DIRECTION(trip)}{base.NULL}' for trip in trips])
    table.add_row(
        [f'{base.BOLD}{base.CYAN}Shape{base.NULL}'] +
        [(f'{base.BOLD}{trip.shape}{base.NULL}' if trip.shape else base.NULL_TEXT)
         for trip in trips])
    table.add_row(
        [f'{base.BOLD}{base.CYAN}Block{base.NULL}'] +
        [(f'{base.BOLD}{base.LIMITED_TEXT(trip.block, 10)}{base.NULL}'
          if trip.block else base.NULL_TEXT) for trip in trips])
    table.add_row(
        [f'{base.BOLD}{base.CYAN}#{base.NULL}'] +
        [f'{base.BOLD}{base.CYAN}Stop{base.NULL}\n'
         f'{base.BOLD}{base.CYAN}Dropoff{base.NULL}\n'
         f'{base.BOLD}{base.CYAN}Pickup{base.NULL}'] * len(trips))
    # add the stops
    for seq in range(1, n_stops + 1):
      table_row: list[str] = [f'{base.BOLD}{base.CYAN}{seq}{base.NULL}']
      for trip in trips:
        stop: dm.Stop = trip.stops[seq]
        if stop == dm.NULL_STOP:
          table_row.append(f'\n{base.BOLD}{base.RED}\u2717{base.NULL}')  # ✗
        else:
          table_row.append(
              f'{base.BOLD}{base.YELLOW}'
              f'{base.LIMITED_TEXT(self._gtfs.StopNameTranslator(stop.stop), 10)}{base.NULL}\n'
              f'{base.BOLD}'
              f'{stop.scheduled.times.arrival.ToHMS() if stop.scheduled.times.arrival else base.NULL_TEXT}'
              f'{dm.STOP_TYPE_STR[stop.dropoff]}{base.NULL}\n'
              f'{base.BOLD}'
              f'{stop.scheduled.times.departure.ToHMS() if stop.scheduled.times.departure else base.NULL_TEXT}'
              f'{dm.STOP_TYPE_STR[stop.pickup]}{base.NULL}')
      table.add_row(table_row)
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # type:ignore

  def PrettyPrintAllDatabase(self) -> Generator[str, None, None]:
    """Print everything in the database."""
    yield '██ ✿ CALENDAR ✿ ███████████████████████████████████████████████████████████████████'
    yield ''
    yield from self.PrettyPrintCalendar()
    yield ''
    yield '██ ✿ STOPS ✿ ██████████████████████████████████████████████████████████████████████'
    yield ''
    yield from self.PrettyPrintStops()
    yield ''
    yield '██ ✿ TRIPS ✿ ██████████████████████████████████████████████████████████████████████'
    yield ''
    for _, name, _ in self.WalkTrains():
      yield from self.PrettyPrintTrip(trip_name=name)
      yield ''
      yield '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      yield ''


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
  print_arg_subparsers.add_parser('calendars', help='Print Calendars/Services')
  print_arg_subparsers.add_parser('stops', help='Print Stops')
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
  _: argparse.ArgumentParser = print_arg_subparsers.add_parser(
      'all', help='Print All Data')
  # ALL commands
  parser.add_argument(
      '-v', '--verbose', action='count', default=0,
      help='Increase verbosity (use -v, -vv, -vvv, -vvvv for ERR/WARN/INFO/DEBUG output)')
  args: argparse.Namespace = parser.parse_args(argv)
  levels: list[int] = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
  logging.basicConfig(level=levels[min(args.verbose, len(levels) - 1)], format=base.LOG_FORMAT)  # type:ignore
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
        case 'calendars':
          for line in dart.PrettyPrintCalendar():
            print(line)
        case 'stops':
          for line in dart.PrettyPrintStops():
            print(line)
        case 'trips':
          # trips for a day
          for line in dart.PrettyDaySchedule(
              day=base.DATE_OBJ_GTFS(args.day) if args.day else datetime.date.today()):
            print(line)
        case 'station':
          # station chart for a day
          for line in dart.PrettyStationSchedule(
              stop_id=database.StopIDFromNameFragmentOrID(args.station),
              day=base.DATE_OBJ_GTFS(args.day) if args.day else datetime.date.today()):
            print(line)
        case 'trip':
          # DART trip
          for line in dart.PrettyPrintTrip(trip_name=args.code):
            print(line)
        case 'all':
          for line in dart.PrettyPrintAllDatabase():
            print(line)
        case _:
          raise NotImplementedError()
      print()
    case _:
      raise NotImplementedError()
  return 0


if __name__ == '__main__':
  sys.exit(main())
