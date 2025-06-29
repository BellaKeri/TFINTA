#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
"""Irish Rail Realtime."""

import argparse
import logging
# import pdb
import sys

from balparda_baselib import base
# import prettytable

# from . import realtime_data_model as dm

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 4)  # v1.4 - 2025/06/28


class Error(Exception):
  """Realtime exception."""


class RealtimeRail:
  """Irish Rail Realtime."""

  def __init__(self) -> None:
    """Constructor."""


def main(argv: list[str] | None = None) -> int:  # pylint: disable=invalid-name,too-many-locals
  """Main entry point."""
  # parse the input arguments, add subparser for `command`
  parser: argparse.ArgumentParser = argparse.ArgumentParser()
  command_arg_subparsers = parser.add_subparsers(dest='command')
  # ALL commands
  parser.add_argument(
      '-v', '--verbose', action='count', default=0,
      help='Increase verbosity (use -v, -vv, -vvv, -vvvv for ERR/WARN/INFO/DEBUG output)')
  args: argparse.Namespace = parser.parse_args(argv)
  levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
  logging.basicConfig(level=levels[min(args.verbose, len(levels) - 1)], format=base.LOG_FORMAT)
  command = args.command.lower().strip() if args.command else ''
  # realtime = RealtimeRail()
  # look at main command
  match command:
    case 'read':
      pass
    case 'print':
      # look at sub-command for print
      # print_command = args.print_command.lower().strip() if args.print_command else ''
      print()
      #
      print()
    case _:
      raise NotImplementedError()
  return 0


if __name__ == '__main__':
  sys.exit(main())
