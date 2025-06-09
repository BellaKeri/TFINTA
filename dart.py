#!/usr/bin/python3 -O
#
# Copyright 2025 Balparda (balparda@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""Dublin DART: data and extensible tables."""

import argparse
import logging
# import pdb

from baselib import base

from TFINTA import gtfs_data_model as dm
from TFINTA import gtfs

__author__ = 'balparda@github.com'
__version__ = (1, 0)


# defaults
_DEFAULT_DAYS_FRESHNESS = 10


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
  _: argparse.ArgumentParser = command_arg_subparsers.add_parser(
      'print', help='Print DB')
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
      # "read" command
      if command == 'read':
        database.LoadData(
            gtfs.IRISH_RAIL_OPERATOR, gtfs.IRISH_RAIL_LINK,
            freshness=args.freshness, force_replace=bool(args.replace))
      # "print" command
      elif command == 'print':
        print()
        dart_agency, dart_route = database.FindAgencyRoute(
            gtfs.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, 'DART', long_name='Bray - Howth')
        if not dart_agency or not dart_route:
          raise gtfs.Error('Database does not have the DART route: maybe run `read` command?')
        print(f'  DART TRIPS - {dart_route.id}')
        print()
        for trip in dart_route.trips.values():
          print(f'{trip.id}: {trip.headsign}/{trip.name} {trip.service} {trip.direction} {len(trip.stops)}')
        print()
        # 4452_980: Bray (Daly)/E227 83 True 27
        # 4452_986: Bray (Daly)/E227 84 True 27
        # 4452_987: Greystones/E111 82 True 28
        # 4452_995: Bray (Daly)/E250 81 True 27
      # no valid command
      else:
        parser.print_help()
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
