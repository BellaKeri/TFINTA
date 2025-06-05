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
from typing import Callable, Generator, IO, Optional, TypedDict
import urllib.request
import zipfile

from baselib import base

__author__ = 'balparda@github.com'
__version__ = (1, 0)


# defaults
_DEFAULT_DAYS_FRESHNESS = 1
_SECONDS_IN_DAY = 60 * 60 * 24
_DAYS_OLD: Callable[[float], float] = lambda t: (time.time() - t) / _SECONDS_IN_DAY
_DATA_DIR: str = base.MODULE_PRIVATE_DIR(__file__, '.data')
_DEFAULT_DB_FILE: str = os.path.join(_DATA_DIR, 'transit.db')
_REQUIRED_FILES: set[str] = {
    'feed_info.txt',  # required because it has the date ranges and the version info
}

# URLs
_OFFICIAL_GTFS_CSV = 'https://www.transportforireland.ie/transitData/Data/GTFS%20Operator%20Files.csv'
_KNOWN_OPERATORS: set[str] = {
    # the operators we care about and will load GTFS for
    'Iarnród Éireann / Irish Rail',
}


class Error(Exception):
  """GTFS exception."""


class ParseError(Error):
  """Exception parsing a GTFS file."""


class ParseImplementationError(ParseError):
  """Exception parsing a GTFS row."""


class RowError(ParseError):
  """Exception parsing a GTFS row."""


class _TableLocation(TypedDict):
  """GTFS table coordinates (just for parsing use for now)."""
  operator: str   # GTFS Operator, from CSV Official Sources
  link: str       # GTFS ZIP file URL location
  file_name: str  # file name (ex: 'feed_info.txt')


class FileMetadata(TypedDict):
  """GTFS file metadata (mostly from loading feed_info.txt tables)."""
  tm: float       # timestamp of last load of this GTFS ZIP file
  publisher: str  # feed_info.txt/feed_publisher_name (required)
  url: str        # feed_info.txt/feed_publisher_url  (required)
  language: str   # feed_info.txt/feed_lang           (required)
  start: int      # feed_info.txt/feed_start_date     (required)
  end: int        # feed_info.txt/feed_end_date       (required)
  version: str    # feed_info.txt/feed_version        (required)


class OfficialFiles(TypedDict):
  """Official GTFS files."""
  tm: float  # timestamp of last pull of the official CSV
  files: dict[str, dict[str, Optional[FileMetadata]]]  # {provider: {url: FileMetadata}}


class GTFSData(TypedDict):
  """GTFS data."""
  tm: float              # timestamp of last DB save
  files: OfficialFiles  # the available GTFS files


# useful aliases
_GTFSRowHandler = Callable[[_TableLocation, int, dict[str, Optional[str]]], None]


class GTFS:
  """GTFS database."""

  def __init__(self, db_path: str) -> None:
    """Constructor.

    Args:
      db_path: Complete path to save DB to
    """
    # save the path
    if not db_path:
      raise Error('DB path cannot be empty')
    self._db_path: str = db_path.strip()
    self._db: GTFSData
    self._changed = False
    # load DB, or create if new
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
    # create file handlers structure
    self._file_handlers: dict[str, tuple[_GTFSRowHandler, set[str]]] = {
        # file_name: (handler, {field1, field2, ...})
        'feed_info.txt': (
            self._HandleFeedInfoRow,
            {
                'feed_publisher_name',
                'feed_publisher_url',
                'feed_lang',
                'feed_start_date',
                'feed_end_date',
                'feed_version',
            }),
    }

  def Save(self, force: bool = False) -> None:
    """Save DB to file.

    Args:
      force: (default False) Saves even if no changes to data were detected
    """
    if force or self._changed:
      with base.Timer() as tm_save:
        # (compressing is responsible for ~95% of save time)
        self._db['tm'] = time.time()
        base.BinSerialize(self._db, file_path=self._db_path, compress=True)
      self._changed = False
      logging.info('Saved DB to %r (%s)', self._db_path, tm_save.readable)

  @property
  def _files(self) -> OfficialFiles:
    """Official index of GTFS files available for download."""
    return self._db['files']

  def _LoadCSVSources(self) -> None:
    """Loads GTFS official sources from CSV."""
    # get the file and parse it
    new_files: dict[str, dict[str, Optional[FileMetadata]]] = {}
    with urllib.request.urlopen(_OFFICIAL_GTFS_CSV) as gtfs_csv:
      text_csv = io.TextIOWrapper(gtfs_csv, encoding='utf-8')
      for i, row in enumerate(csv.reader(text_csv)):
        if len(row) != 2:
          raise Error(f'Unexpected row in GTFS CSV list: {row!r}')
        if not i:
          if row != ['Operator', 'Link']:
            raise Error(f'Unexpected start of GTFS CSV list: {row!r}')
          continue  # first row is as expected: skip it
        # we have a row
        new_files.setdefault(row[0], {})[row[1]] = None
    # check the operators we care about are included!
    for operator in _KNOWN_OPERATORS:
      if operator not in new_files:
        raise Error(f'Operator {operator!r} not in loaded CSV!')
    # we have the file loaded
    self._files['files'] = new_files
    self._files['tm'] = time.time()
    self._changed = True
    logging.info(
        'Loaded GTFS official sources with %d operators and %d links',
        len(new_files), sum(len(urls) for urls in new_files.values()))

  def _LoadGTFSSource(
      self, operator: str, link: str,
      allow_unknown_file: bool = True, allow_unknown_field: bool = False) -> None:
    """Loads a single GTFS ZIP file and parses all inner data files.

    Args:
      operator: Operator for GTFS file
      link: URL for GTFS file
      allow_unknown_file: (default True) If False will raise on unknown GTFS file
      allow_unknown_field: (default False) If False will raise on unknown field in file

    Raises:
      ParseError: missing files or fields
      ParseImplementationError: unknown file or field (if "allow" is False)
    """
    # check that we are asking for a valid and known source
    operator, link = operator.strip(), link.strip()
    if not operator or operator not in self._files['files']:
      raise Error(f'invalid operator {operator!r}')
    operator_files: dict[str, Optional[FileMetadata]] = self._files['files'][operator]
    if not link or link not in operator_files:
      raise Error(f'invalid URL {link!r}')
    # load ZIP from URL
    done_files: set[str] = set()
    file_name: str
    with urllib.request.urlopen(link) as gtfs_zip:
      # extract files from ZIP
      gtfs_zip_bytes: bytes = gtfs_zip.read()
      logging.info(
          'Loading %r data, %s,from %r',
          operator, base.HumanizedBytes(len(gtfs_zip_bytes)), link)
      for file_name, file_data in _UnzipFiles(io.BytesIO(gtfs_zip_bytes)):
        file_name = file_name.strip()
        location: _TableLocation = {
            'operator': operator,
            'link': link,
            'file_name': file_name,
        }
        self._LoadGTFSFile(location, file_data, allow_unknown_file, allow_unknown_field)
        done_files.add(file_name)
    # finished loading the files, check that we loaded all required files
    if (missing_files := _REQUIRED_FILES - done_files):
      raise ParseError(f'Missing required files: {operator} {missing_files!r}')
    self._changed = True

  def _LoadGTFSFile(
      self, location: _TableLocation, file_data: bytes,
      allow_unknown_file: bool, allow_unknown_field: bool) -> None:
    """Loads a single txt (actually CSV) file and parses all fields, sending rows to handlers.

    Args:
      location: (operator, link, file_name)
      file_data: File bytes
      allow_unknown_file: If False will raise on unknown GTFS file
      allow_unknown_field: If False will raise on unknown field in file

    Raises:
      ParseError: missing fields
      ParseImplementationError: unknown file or field (if "allow" is False)
    """
    # check if we know how to process this file
    file_name: str = location['file_name']
    if file_name not in self._file_handlers or not file_data:
      message: str = (
          f'Unsupported GTFS file: {file_name if file_name else "<empty>"} '
          f'({base.HumanizedBytes(len(file_data))})')
      if allow_unknown_file:
        logging.warning(message)
        return
      raise ParseImplementationError(message)
    # supported type of GTFS file, so process the data into the DB
    logging.info('Processing: %s (%s)', file_name, base.HumanizedBytes(len(file_data)))
    file_handler, file_fields = self._file_handlers[file_name]
    i: int = 0
    actual_fields: list[str] = []
    for i, row in enumerate(csv.reader(
        io.TextIOWrapper(io.BytesIO(file_data), encoding='utf-8'))):
      # check for 1st row
      if not i:
        # should be the fields: check them
        actual_fields = row  # save for later: we need the order of fields
        # find missing fields (TODO in future: optional fields)
        if (missing_fields := file_fields - set(actual_fields)):
          raise ParseError(f'Missing fields found: {file_name} {missing_fields!r}')
        # find unknown/unimplemented fields
        if (extra_fields := set(actual_fields) - file_fields):
          message = f'Extra fields found: {file_name} {extra_fields!r}'
          if allow_unknown_field:
            logging.warning(message)
          else:
            raise ParseImplementationError(message)
        continue  # first row is as expected: skip it
      # we have a row that is not the 1st, should be data
      file_handler(
          location, i,
          dict(zip(actual_fields,
                   [(k if k else None) for k in (j.strip() for j in row)])))
    self._changed = True
    logging.info('Read %d records from %s', i, file_name)  # 1st row of CSV is not a record

  # HANDLER TEMPLATE (copy and uncomment)
  # def _HandleTABLENAMERow(
  #     self, location: _TableLocation, count: int, row: dict[str, Optional[str]]) -> None:
  #   """Handler: "FILENAME.txt" DESCRIPTION.
  #
  #   Args:
  #     location: _TableLocation info on current GTFS table
  #     count: row count, starting on 1
  #     row: the row as a dict {field_name: Optional[field_data]}
  #
  #   Raises:
  #     RowError: error parsing this record
  #   """

  def _HandleFeedInfoRow(
      self, location: _TableLocation, count: int, row: dict[str, Optional[str]]) -> None:
    """Handler: "feed_info.txt" Information on the GTFS ZIP file being processed.

    Args:
      location: _TableLocation info on current GTFS table
      count: row count, starting on 1
      row: the row as a dict {field_name: Optional[field_data]}

    Raises:
      RowError: error parsing this record
    """
    if count != 1:
      raise RowError('feed_info.txt table is only supported to have 1 row')
    print(location)
    print(row)

  def LoadData(self, freshness: int = _DEFAULT_DAYS_FRESHNESS) -> None:
    """Downloads and parses GTFS data.

    Args:
      freshness: (default 1) Number of days before data is not fresh anymore and
          has to be reloaded from source
    """
    # first load the list of GTFS, if needed
    if (age := _DAYS_OLD(self._files['tm'])) > freshness:
      logging.info('Loading stations (%0.1f days old)', age)
      self._LoadCSVSources()
    else:
      logging.info('Stations are fresh (%0.1f days old) - SKIP', age)
    # load GTFS data we are interested in
    self._LoadGTFSSource(
        'Iarnród Éireann / Irish Rail',
        'https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip')


def _UnzipFiles(in_file: IO[bytes]) -> Generator[tuple[str, bytes], None, None]:
  """Unzips `in_file` bytes buffer. Manages multiple files.

  Args:
    in_file: bytes buffer (io.BytesIO for example) with ZIP data

  Yields:
    (file_name, file_data_bytes)

  Raises:
    BadZipFile: ZIP error
  """
  with zipfile.ZipFile(in_file, 'r') as zip_ref:
    for file_name in sorted(zip_ref.namelist()):
      with zip_ref.open(file_name) as file_data:
        yield (file_name, file_data.read())


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
