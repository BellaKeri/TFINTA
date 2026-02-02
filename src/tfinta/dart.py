# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Dublin DART: data and extensible tables."""

from __future__ import annotations

import collections
import copy
import dataclasses
import datetime
import operator
from collections.abc import Generator

import click
import prettytable
import typer
from rich import console as rich_console
from transcrypto.cli import clibase
from transcrypto.utils import logging as tc_logging

from . import __version__, gtfs
from . import gtfs_data_model as dm
from . import tfinta_base as base


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DARTConfig(clibase.CLIConfig):
  """CLI global context, storing the configuration."""


# defaults
_DEFAULT_DAYS_FRESHNESS = 10
_TODAY: datetime.date = datetime.datetime.now(tz=datetime.UTC).date()
_TODAY_INT = int(_TODAY.strftime('%Y%m%d'))
_MIN_DATE = 20000101
_MAX_DATE = 21991231


class Error(gtfs.Error):
  """DART exception."""


class DART:
  """Dublin DART."""

  def __init__(self, gtfs_obj: gtfs.GTFS, /) -> None:
    """Construct.

    Args:
        gtfs_obj: GTFS database object

    Raises:
        Error: if the GTFS object is invalid or missing DART route

    """
    # get DB
    if not gtfs_obj:
      raise Error('Empty GTFS object (database)')
    self._gtfs: gtfs.GTFS = gtfs_obj
    # get DART Agency/Route or die
    dart_agency, dart_route = self._gtfs.FindAgencyRoute(
      dm.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, dm.DART_SHORT_NAME, long_name=dm.DART_LONG_NAME
    )
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
      if (n_stops := len(schedule.stops)) < 2 or len(schedule.times) < 2:  # noqa: PLR2004
        raise Error(f'trip {trip.id} has fewer than 2 stops: {n_stops}')
      trains.setdefault(trip.name, []).append((trip.service, schedule, trip))
    # get train code names and find an ordering
    trip_names: list[tuple[dm.Schedule, str]] = [
      (min(s for _, s, _ in tr), n) for n, tr in trains.items()
    ]
    trip_names.sort()
    # create ordered dict to preserve sorted train codes
    self._dart_trips: collections.OrderedDict[str, list[tuple[int, dm.Schedule, dm.Trip]]] = (
      collections.OrderedDict()
    )
    for _, name in trip_names:
      self._dart_trips[name] = sorted(trains[name], key=operator.itemgetter(1, 0))  # also sort!

  def ScheduleFromTrip(self, trip: dm.Trip, /) -> dm.Schedule:
    """Build a schedule object from this particular trip.

    Args:
        trip: trip to build schedule from

    Returns:
        schedule object for this trip

    """
    stops: tuple[dm.TrackStop] = tuple(
      dm.TrackStop(  # type:ignore
        stop=trip.stops[i].stop,
        name=self._gtfs.StopNameTranslator(trip.stops[i].stop),  # needs this for sorting later!!
        headsign=trip.stops[i].headsign,
        pickup=trip.stops[i].pickup,
        dropoff=trip.stops[i].dropoff,
      )
      for i in range(1, len(trip.stops) + 1)
    )  # this way guarantees we hit every int (seq)
    return dm.Schedule(
      direction=trip.direction,
      stops=stops,
      times=tuple(
        # this way guarantees we hit every int (seq)
        trip.stops[i].scheduled
        for i in range(1, len(trip.stops) + 1)
      ),
    )

  def Services(self) -> set[int]:
    """Set of all DART services.

    Returns:
        set of all service IDs

    """
    return {t.service for t in self._dart_route.trips.values()}

  def ServicesForDay(self, day: datetime.date, /) -> set[int]:
    """Set of DART services for a single day.

    Args:
        day: day to get services for

    Returns:
        set of service IDs for this day

    """
    return self._gtfs.ServicesForDay(day).intersection(self.Services())

  def WalkTrains(
    self, /, *, filter_services: set[int] | None = None
  ) -> Generator[tuple[dm.Schedule, str, list[tuple[int, dm.Schedule, dm.Trip]]], None, None]:
    """Iterate over actual physical DART trains in a sensible order.

    DART behaves oddly:
    (1) After you group by the obvious things a single train will do (agnostic, endpoint, track)
        a single DART train can only be unique looking at Trip.name (trips.txt/trip_short_name);
        the documentation for GTFS states "a trip_short_name value, if provided, should uniquely
        identify a trip within a service day" and DART seems to use this a lot;
    (2) Two physically identical "trips" (i.e. a single "train") can have 2 slightly diverging
        Schedules (i.e. timetables); they may start the same and diverge (usually by 2 to 10 min)
        or they may start diverged and converge; this is why the "canonical" Schedule will be
        the "min()" of the schedules, i.e. the first to depart, the "smaller" in time

    Args:
        filter_services: set of service IDs to filter to (None == all)

    Yields:
        tuple of
        (canonical Schedule, train code name, list of (service ID, Schedule, Trip) in this train)

    """
    # collect the trains that are actually running today
    filtered_trains: list[tuple[dm.Schedule, str, list[tuple[int, dm.Schedule, dm.Trip]]]] = []
    for name, trips in self._dart_trips.items():
      filtered_trips: list[tuple[int, dm.Schedule, dm.Trip]] = [
        t for t in trips if (filter_services is None or t[0] in filter_services)
      ]
      if not filtered_trips:
        continue  # this train code has no trip today
      filtered_trains.append(
        (
          min(s for _, s, _ in filtered_trips),
          name,
          sorted(filtered_trips, key=operator.itemgetter(1, 0)),
        )
      )
    yield from sorted(
      filtered_trains,
      key=lambda t: (  # re-sort by:
        t[0].direction,  # North/South
        t[0].stops[0].name,  # start stop
        t[0].stops[-1].name,  # destination stop
        t[0].times[0].times.departure,  # HH:MM:SS as seconds
        t[1],  # tie-break with the train code (E800, ...)
      ),
    )

  def StationSchedule(
    self, stop_id: str, day: datetime.date, /
  ) -> dict[
    tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[tuple[int, dm.Schedule, dm.Trip]]]
  ]:
    """Get data for trains in a `stop` for a specific `day`.

    Args:
        stop_id: stop ID to get schedule for
        day: day to get schedule for

    Returns:
        dictionary keyed by (destination stop ID, ScheduleStop) with values of
        (train code name, Schedule, list of (service ID, Schedule, Trip) in this train)

    Raises:
        Error: if the stop ID is invalid

    """
    station: dict[
      tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[tuple[int, dm.Schedule, dm.Trip]]]
    ] = {}
    for schedule, name, trips_in_train in self.WalkTrains(filter_services=self.ServicesForDay(day)):
      for i, stop in enumerate(schedule.stops):
        if stop.stop == stop_id:
          new_key: tuple[str, dm.ScheduleStop] = (schedule.stops[-1].stop, schedule.times[i])
          if new_key in station:
            raise Error(
              f'Duplicate stop/time {new_key}: NEW {trips_in_train} OLD {station[new_key][1]}'
            )
          station[new_key] = (name, schedule, trips_in_train)
    return station

  ##################################################################################################
  # DART PRETTY PRINTS
  ##################################################################################################

  def PrettyPrintCalendar(self) -> Generator[str, None, None]:
    """Generate a pretty version of calendar data.

    Yields:
        lines of the pretty-printed results

    """
    yield from self._gtfs.PrettyPrintCalendar(filter_to=self.Services())

  def PrettyPrintStops(self) -> Generator[str, None, None]:
    """Generate a pretty version of the stops.

    Yields:
        lines of the pretty-printed results

    """
    all_stops: set[str] = {
      stop.stop
      for _, _, trips in self.WalkTrains()
      for _, _, trip in trips
      for stop in trip.stops.values()
    }
    yield from self._gtfs.PrettyPrintStops(filter_to=all_stops)

  def PrettyDaySchedule(self, /, *, day: datetime.date) -> Generator[str, None, None]:
    """Generate a pretty version of a DART day's schedule.

    Args:
        day: day to get schedule for

    Yields:
        lines of the pretty-printed results

    Raises:
        Error: if the day is invalid

    """
    if not day:
      raise Error('empty day')
    yield '[bold magenta]DART Schedule[/]'
    yield ''
    yield (f'Day:      [bold yellow]{day}[/] [bold]({base.DAY_NAME[day.weekday()]})[/]')
    day_services: set[int] = self.ServicesForDay(day)
    yield (f'Services: [bold yellow]{", ".join(str(s) for s in sorted(day_services))}[/]')
    yield ''
    table = prettytable.PrettyTable(
      [
        '[bold cyan]N/S[/]',
        '[bold cyan]Train[/]',
        '[bold cyan]Start[/]',
        '[bold cyan]End[/]',
        '[bold cyan]Depart Time[/]',
        '[bold cyan]Service/Trip Codes/[/][red][★Alt.Times][/]',
      ]
    )  # ★
    for schedule, name, trips_in_train in self.WalkTrains(filter_services=day_services):
      trip_codes: str = ', '.join(
        f'{s}/{t.id}{"" if sc == schedule else "/[red][★][/][bold]"}' for s, sc, t in trips_in_train
      )
      table.add_row(
        [
          f'[bold]{dm.DART_DIRECTION(schedule)}[/]',
          f'[bold yellow]{name}[/]',
          f'[bold]{schedule.stops[0].name}[/]',
          f'[bold]{schedule.stops[-1].name}[/]',
          (
            '[bold yellow]'
            f'{
              schedule.times[0].times.departure.ToHMS()
              if schedule.times[0].times.departure
              else "∅"
            }'
            f'[/][bold]{trip_codes}[/]'
          ),
        ]
      )
    yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]

  def PrettyStationSchedule(
    self, /, *, stop_id: str, day: datetime.date
  ) -> Generator[str, None, None]:
    """Generate a pretty version of a DART station (stop) day's schedule.

    Args:
        stop_id: stop ID to get schedule for
        day: day to get schedule for

    Yields:
        lines of the pretty-printed results

    Raises:
        Error: if the stop ID is invalid

    """
    stop_id = stop_id.strip()
    if not day or not stop_id:
      raise Error('empty stop/day')
    stop_name: str = self._gtfs.StopNameTranslator(stop_id)
    yield (f'[magenta]DART Schedule for Station [bold]{stop_name} - {stop_id}[/]')
    yield ''
    yield (f'Day:          [bold yellow]{day}[/] [bold]({base.DAY_NAME[day.weekday()]})[/]')
    day_services: set[int] = self.ServicesForDay(day)
    yield (f'Services:     [bold yellow]{", ".join(str(s) for s in sorted(day_services))}[/]')
    day_dart_schedule: dict[
      tuple[str, dm.ScheduleStop], tuple[str, dm.Schedule, list[tuple[int, dm.Schedule, dm.Trip]]]
    ] = self.StationSchedule(stop_id, day)
    destinations: set[str] = {self._gtfs.StopNameTranslator(k[0]) for k in day_dart_schedule}
    yield f'Destinations: [bold yellow]{", ".join(sorted(destinations))}[/]'
    yield ''
    table = prettytable.PrettyTable(
      [
        '[bold cyan]N/S[/]',
        '[bold cyan]Train[/]',
        '[bold cyan]Destination[/]',
        '[bold cyan]Arrival[/]',
        '[bold cyan]Departure[/]',
        '[bold cyan]Service/Trip Codes/[/][red][★Alt.Times][/]',
      ]
    )  # ★
    last_arrival: int = 0
    last_departure: int = 0
    for dest, tm in sorted(day_dart_schedule.keys(), key=operator.itemgetter(1, 0)):
      name, schedule, trips_in_train = day_dart_schedule[dest, tm]
      if (tm.times.arrival and tm.times.arrival.time < last_arrival) or (
        tm.times.departure and tm.times.departure.time < last_departure
      ):
        # make sure both arrival and departures are strictly moving forward
        raise Error(f'time moved backwards in schedule @ {dest} / {tm}')
      trip_codes: str = ', '.join(
        f'{s}/{t.id}{"" if sc == schedule else "/[red][★][/][bold]"}'
        for s, sc, t in sorted(trips_in_train)
      )
      table.add_row(
        [
          f'[bold]{dm.DART_DIRECTION(trips_in_train[0][2])}[/]',
          f'[bold yellow]{name}[/]',
          f'[bold yellow]{schedule.stops[-1].name}[/]',
          f'[bold]{tm.times.arrival.ToHMS() if tm.times.arrival else "∅"}[/]',
          f'[bold yellow]{tm.times.departure.ToHMS() if tm.times.departure else "∅"}[/]',
          f'[bold]{trip_codes}[/]',
        ]
      )
      last_arrival = tm.times.arrival.time if tm.times.arrival else 0
      last_departure = tm.times.departure.time if tm.times.departure else 0
    yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]

  def PrettyPrintTrip(self, /, *, trip_name: str) -> Generator[str, None, None]:  # noqa: C901, PLR0912, PLR0915
    """Generate a pretty version of a train (physical) trip, may be 2 Trips.

    Args:
        trip_name: trip name/code to pretty print

    Yields:
        lines of the pretty-printed results

    Raises:
        Error: if the trip name is invalid

    """
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
    yield f'[magenta]DART Trip [bold]{trip_name}[/]'
    yield ''
    # check for unexpected things that should not happen and pad trips that are shorter
    padded_trips: list[dm.Trip] = []
    for trip in trips:
      if (
        trips[0].route != trip.route
        or trips[0].agency != trip.agency
        or trips[0].headsign != trip.headsign
        or trips[0].name != trip.name
      ):
        raise Error(
          f'route/agency/headsign/name should be consistent {trip_name!r}: {trips[0]} versus {trip}'
        )
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
            f'/{max_stop=}: {[s.stop for s in trip.stops.values()]}'
          )
        padded_trips.append(new_trip)
      else:
        # size is already max, we just copy
        padded_trips.append(trip)
    trips = padded_trips
    # print the static stuff
    agency, route, _ = self._gtfs.FindTrip(trips[0].id)
    if not agency or not route:
      raise Error(f'trip id {trips[0].id!r} was not found ({trip_name!r})')
    yield f'Agency:        [bold yellow]{agency.name}[/]'
    yield f'Route:         [bold yellow]{route.id}[/]'
    yield f'  Short name:  [bold yellow]{route.short_name}[/]'
    yield f'  Long name:   [bold yellow]{route.long_name}[/]'
    yield (f'  Description: [bold]{route.description or "∅"}[/]')
    yield (f'Headsign:      [bold]{trips[0].headsign or "∅"}[/]')
    yield ''
    table = prettytable.PrettyTable(
      ['[bold cyan]Trip ID[/]'] + [f'[bold magenta]{t.id}[/]' for t in trips]
    )
    # add the properties that are variable
    table.add_row(['[bold cyan]Service[/]'] + [f'[bold yellow]{trip.service}[/]' for trip in trips])
    table.add_row(
      # direction can vary, example 'E725'
      ['[bold cyan]N/S[/]'] + [f'[bold]{dm.DART_DIRECTION(trip)}[/]' for trip in trips]
    )
    table.add_row(
      ['[bold cyan]Shape[/]']
      + [(f'[bold]{trip.shape}[/]' if trip.shape else '∅') for trip in trips]
    )
    table.add_row(
      ['[bold cyan]Block[/]']
      + [(f'[bold]{base.LIMITED_TEXT(trip.block, 10)}[/]' if trip.block else '∅') for trip in trips]
    )
    table.add_row(
      ['[bold cyan]#[/]']
      + ['[bold cyan]Stop[/]\n[bold cyan]Dropoff[/]\n[bold cyan]Pickup[/]'] * len(trips)
    )
    # add the stops
    for seq in range(1, n_stops + 1):
      table_row: list[str] = [f'[bold cyan]{seq}[/]']
      for trip in trips:
        stop: dm.Stop = trip.stops[seq]
        if stop == dm.NULL_STOP:
          table_row.append('\n[bold red]\u2717[/]')  # ✗
        else:
          table_row.append(
            f'[bold yellow]'
            f'{base.LIMITED_TEXT(self._gtfs.StopNameTranslator(stop.stop), 10)}[/]\n'
            f'[bold]'
            f'{stop.scheduled.times.arrival.ToHMS() if stop.scheduled.times.arrival else "∅"}'
            f'{dm.STOP_TYPE_STR[stop.dropoff]}[/]\n'
            f'[bold]'
            f'{stop.scheduled.times.departure.ToHMS() if stop.scheduled.times.departure else "∅"}'
            f'{dm.STOP_TYPE_STR[stop.pickup]}[/]'
          )
      table.add_row(table_row)
    table.hrules = prettytable.HRuleStyle.ALL
    yield from table.get_string().splitlines()  # pyright: ignore[reportUnknownMemberType]

  def PrettyPrintAllDatabase(self) -> Generator[str, None, None]:
    """Print everything in the database.

    Yields:
        lines of the pretty-printed results

    """
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


# CLI app setup, this is an important object and can be imported elsewhere and called
app = typer.Typer(
  add_completion=True,
  no_args_is_help=True,
  help='dart: CLI for Dublin DART rail services.',  # keep in sync with Main().help
  epilog=(
    'Example:\n\n\n\n'
    '# --- Read DART data ---\n\n'
    'poetry run dart read\n\n\n\n'
    '# --- Print schedules ---\n\n'
    'poetry run dart print trips 20260201\n\n'
    'poetry run dart print station Tara 20260201\n\n'
    'poetry run dart print trip E108\n\n\n\n'
    '# --- Generate documentation ---\n\n'
    'poetry run dart markdown > dart.md\n\n'
  ),
)


def Run() -> None:
  """Run the CLI."""
  app()


@app.callback(
  invoke_without_command=True,  # have only one; this is the "constructor"
  help='dart: CLI for Dublin DART rail services.',  # keep message in sync with app.help
)
@clibase.CLIErrorGuard
def Main(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: click.Context,  # global context
  version: bool = typer.Option(False, '--version', help='Show version and exit.'),
  verbose: int = typer.Option(
    0,
    '-v',
    '--verbose',
    count=True,
    help='Verbosity (nothing=ERROR, -v=WARNING, -vv=INFO, -vvv=DEBUG).',
    min=0,
    max=3,
  ),
  color: bool | None = typer.Option(
    None,
    '--color/--no-color',
    help=(
      'Force enable/disable colored output (respects NO_COLOR env var if not provided). '
      'Defaults to having colors.'  # state default because None default means docs don't show it
    ),
  ),
) -> None:
  if version:
    typer.echo(__version__)
    raise typer.Exit(0)
  # initialize logging and get console
  console: rich_console.Console
  console, verbose, color = tc_logging.InitLogging(
    verbose,
    color=color,
    include_process=False,
  )
  # check a few things
  if not (_MIN_DATE < _TODAY_INT < _MAX_DATE):
    raise Error(f'invalid TODAY date {_TODAY_INT}: not in {_MIN_DATE}..{_MAX_DATE}')
  # create context with the arguments we received.
  ctx.obj = DARTConfig(
    console=console,
    verbose=verbose,
    color=color,
  )


@app.command(
  'read',
  help='Read DB from official sources',
  epilog=('Example:\n\n\n\n$ poetry run dart read\n\n<<loads latest DART data>>'),
)
@clibase.CLIErrorGuard
def ReadCommand(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: typer.Context,
  freshness: int = typer.Option(
    _DEFAULT_DAYS_FRESHNESS,
    '-f',
    '--freshness',
    min=0,
    help='Number of days to cache; 0 == always load',
  ),
  replace: bool = typer.Option(
    False,
    '--replace/--no-replace',
    help='Force replace DB version. Defaults to not loading the same version again.',
  ),
) -> None:
  config: DARTConfig = ctx.obj
  database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
  database.LoadData(
    dm.IRISH_RAIL_OPERATOR,
    dm.IRISH_RAIL_LINK,
    allow_unknown_file=True,
    allow_unknown_field=False,
    freshness=freshness,
    force_replace=replace,
    override=None,
  )
  config.console.print('[bold green]DART database loaded successfully[/]')


print_app = typer.Typer(
  no_args_is_help=True,
  help='Print DB',
)
app.add_typer(print_app, name='print')


@print_app.command(
  'all',
  help='Print all database information.',
  epilog=('Example:\n\n\n\n$ poetry run dart print all\n\n<<prints all DART data>>'),
)
@clibase.CLIErrorGuard
def PrintAll(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: DARTConfig = ctx.obj
  database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
  for line in DART(database).PrettyPrintAllDatabase():
    config.console.print(line)


@print_app.command(
  'calendars',
  help='Print Calendars/Services.',
  epilog=('Example:\n\n\n\n$ poetry run dart print calendars\n\n<<prints DART service calendars>>'),
)
@clibase.CLIErrorGuard
def PrintCalendars(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: DARTConfig = ctx.obj
  database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
  for line in DART(database).PrettyPrintCalendar():
    config.console.print(line)


@print_app.command(
  'stops',
  help='Print Stops.',
  epilog=('Example:\n\n\n\n$ poetry run dart print stops\n\n<<prints all DART stations>>'),
)
@clibase.CLIErrorGuard
def PrintStops(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: DARTConfig = ctx.obj
  database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
  for line in DART(database).PrettyPrintStops():
    config.console.print(line)


@print_app.command(
  'trips',
  help='Print Trips.',
  epilog=(
    'Example:\n\n\n\n$ poetry run dart print trips 20260201\n\n<<prints all trips for 2026-02-01>>'
  ),
)
@clibase.CLIErrorGuard
def PrintTrips(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: typer.Context,
  day: int = typer.Argument(
    _TODAY_INT,
    min=_MIN_DATE,
    max=_MAX_DATE,
    help='Day to consider in "YYYYMMDD" format (default: TODAY/NOW).',
  ),
) -> None:
  config: DARTConfig = ctx.obj
  database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
  for line in DART(database).PrettyDaySchedule(day=base.DATE_OBJ_GTFS(str(day))):
    config.console.print(line)


@print_app.command(
  'station',
  help='Print Station Chart.',
  epilog=(
    'Example:\n\n\n\n'
    '$ poetry run dart print station Tara 20260201\n\n'
    '<<prints Tara Street station schedule>>'
  ),
)
@clibase.CLIErrorGuard
def PrintStation(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: typer.Context,
  station: str = typer.Argument(
    ..., help='Station to print chart for; finds by ID (stops.txt/stop_id) or by name (stop_name)'
  ),
  day: int = typer.Argument(
    _TODAY_INT,
    min=_MIN_DATE,
    max=_MAX_DATE,
    help='Day to consider in "YYYYMMDD" format (default: TODAY/NOW).',
  ),
) -> None:
  config: DARTConfig = ctx.obj
  database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
  for line in DART(database).PrettyStationSchedule(
    stop_id=database.StopIDFromNameFragmentOrID(station),
    day=base.DATE_OBJ_GTFS(str(day)),
  ):
    config.console.print(line)


@print_app.command(
  'trip',
  help='Print DART Trip.',
  epilog=('Example:\n\n\n\n$ poetry run dart print trip E108\n\n<<prints details for train E108>>'),
)
@clibase.CLIErrorGuard
def PrintTrip(  # documentation is help/epilog/args # noqa: D103
  *,
  ctx: typer.Context,
  train: str = typer.Argument(..., help='DART train code, like "E108" for example'),
) -> None:
  config: DARTConfig = ctx.obj
  database = gtfs.GTFS(gtfs.DEFAULT_DATA_DIR)
  for line in DART(database).PrettyPrintTrip(trip_name=train):
    config.console.print(line)


@app.command(
  'markdown',
  help='Emit Markdown docs for the CLI (see README.md section "Creating a New Version").',
  epilog=('Example:\n\n\n\n$ poetry run dart markdown > dart.md\n\n<<saves CLI doc>>'),
)
@clibase.CLIErrorGuard
def Markdown(*, ctx: typer.Context) -> None:  # documentation is help/epilog/args # noqa: D103
  config: DARTConfig = ctx.obj
  config.console.print(clibase.GenerateTyperHelpMarkdown(app, prog_name='dart'))
