#!/usr/bin/python3 -O
#
# Copyright 2025 Balparda (balparda@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""GTFS: Loading, parsing, etc.

See: https://gtfs.org/documentation/schedule/reference/
"""

import argparse
import csv
import io
import logging
import os
import os.path
# import pdb
import time
from typing import Callable, Optional, TypedDict
import urllib.request

from baselib import base

__author__ = 'balparda@github.com'
__version__ = (1, 0)


# defaults
_DEFAULT_DAYS_FRESHNESS = 1
_SECONDS_IN_DAY = 60 * 60 * 24
_DAYS_OLD: Callable[[float], float] = lambda t: (time.time() - t) / _SECONDS_IN_DAY
_DATA_DIR: str = base.MODULE_PRIVATE_DIR(__file__, '.data')
_DEFAULT_DB_FILE: str = os.path.join(_DATA_DIR, 'transit.db')

# URLs
_OFFICIAL_GTFS_CSV = 'https://www.transportforireland.ie/transitData/Data/GTFS%20Operator%20Files.csv'
_KNOWN_OPERATORS: set[str] = {
    # the operators we care about and will load GTFS for
    'Iarnród Éireann / Irish Rail',
}


class _OfficialFiles(TypedDict):
  """Official GTFS files."""

  tm: float                                   # timestamp of last pull of the official CSV
  files: dict[str, dict[str, Optional[int]]]  # {provider: {url: timestamp}}


class _GTFSData(TypedDict):
  """Official GTFS files."""

  tm: float              # timestamp of last DB save
  files: _OfficialFiles  # the available GTFS files


class GTFS:
  """GTFS database."""

  def __init__(self, db_path: str) -> None:
    if not db_path:
      raise AttributeError('DB path cannot be empty')
    self._db_path: str = db_path.strip()
    self._db: _GTFSData
    self._changed = False
    if os.path.exists(self._db_path):
      # DB exists: load
      with base.Timer() as tm_load:
        self._db = base.BinDeSerialize(file_path=self._db_path, compress=True)
      logging.info('Loaded DB from %r (%s)', self._db_path, tm_load.readable)
      logging.info('DB freshness: %s', base.STD_TIME_STRING(self._db['tm']))
    else:
      # DB does not exist: create empty
      self._db = {  # empty DB
          'tm': 0.0,
          'files': {
              'tm': 0.0,
              'files': {},
          },
      }
      self.Save(force=True)

  def Save(self, force: bool = False) -> None:
    """Save DB to file."""
    if force or self._changed:
      with base.Timer() as tm_save:
        # (compressing is responsible for ~95% of save time)
        self._db['tm'] = time.time()
        base.BinSerialize(self._db, file_path=self._db_path, compress=True)
      self._changed = False
      logging.info('Saved DB to %r (%s)', self._db_path, tm_save.readable)

  @property
  def _files(self) -> _OfficialFiles:
    """Official index of GTFS files available for download."""
    return self._db['files']

  def _LoadCSVSources(self) -> None:
    # get the file and parse it
    new_files: dict[str, dict[str, Optional[int]]] = {}
    with urllib.request.urlopen(_OFFICIAL_GTFS_CSV) as gtfs_csv:
      text_csv = io.TextIOWrapper(gtfs_csv, encoding='utf-8')
      for i, row in enumerate(csv.reader(text_csv)):
        if len(row) != 2:
          raise AttributeError(f'Unexpected row in GTFS CSV list: {row!r}')
        if not i:
          if row != ['Operator', 'Link']:
            raise AttributeError(f'Unexpected start of GTFS CSV list: {row!r}')
          continue  # first row is as expected: skip it
        # we have a row
        new_files.setdefault(row[0], {})[row[1]] = None
    # check the operators we care about are included!
    for operator in _KNOWN_OPERATORS:
      if operator not in new_files:
        raise AttributeError(f'Operator {operator!r} not in loaded CSV!')
    # we have the file loaded
    self._files['files'] = new_files
    self._files['tm'] = time.time()
    self._changed = True
    logging.info(
        'Loaded GTFS official sources with %d operators and %d links',
        len(new_files), sum(len(urls) for urls in new_files.values()))

  def LoadData(self, freshness: int = _DEFAULT_DAYS_FRESHNESS) -> None:
    """Downloads and parses GTFS data."""
    # first load the list of GTFS, if needed
    if (age := _DAYS_OLD(self._files['tm'])) > freshness:
      logging.info('Loading stations (%0.1f days old)', age)
      self._LoadCSVSources()
    else:
      logging.info('Stations are fresh (%0.1f days old) - SKIP', age)


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
  print(f'**                 {base.TERM_LIGHT_RED}GTFS DB{base.TERM_BLUE}                   **')
  print('**   balparda@gmail.com (Daniel Balparda)    **')
  print(f'***********************************************{base.TERM_END}')
  success_message: str = f'{base.TERM_WARNING}premature end? user paused?'
  try:
    # open DB, create directory if needed
    if not os.path.isdir(_DATA_DIR):
      os.mkdir(_DATA_DIR)
      logging.info('Created data directory: %s', _DATA_DIR)
    database = GTFS(_DEFAULT_DB_FILE)
    # execute the command
    print()
    with base.Timer() as op_timer:
      # "read" command
      if command == 'read':
        try:
          database.LoadData(freshness=args.freshness)
        finally:
          database.Save()
      # "print" command
      elif command == 'print':
        raise NotImplementedError()
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
