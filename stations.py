#!/usr/bin/python3 -O
#
# Copyright 2025 BellaKeri (BellaKeri@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""Stations loader."""

# import logging
# import pdb

__author__ = 'BellaKeri@github.com'
__version__ = (1, 0)


def LoadStations() -> str:
  return '<xml>'


def ConvertToXML(data_xml: str) -> str:  # xml
  return 'obj'


def CountStations(xml: str) -> int:
  return 10


def Main() -> None:
  """Main entry point."""
  data_xml = LoadStations()
  xml = ConvertToXML(data_xml)
  station_count = CountStations(xml)

  print(f'Ireland has {station_count} stations')


if __name__ == '__main__':
  Main()
