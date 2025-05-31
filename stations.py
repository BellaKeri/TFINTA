#!/usr/bin/python3 -O
#
# Copyright 2025 BellaKeri (BellaKeri@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""Stations loader."""

# import logging
import pdb
import urllib.request
import xml.dom.minidom

__author__ = 'BellaKeri@github.com'
__version__ = (1, 0)

# The TfI URLs:
ALL_STATIONS_URL = 'http://api.irishrail.ie/realtime/realtime.asmx/getAllStationsXML'

XMLType = xml.dom.minidom.Document


def LoadStations() -> str:
  with urllib.request.urlopen(ALL_STATIONS_URL) as rail_data:
    return rail_data.read()
  # equivale a: return urllib.request.urlopen(ALL_STATIONS_URL).read()


def ConvertToXML(data_xml: str) -> XMLType:
  return xml.dom.minidom.parseString(data_xml)


def CountStations(xml: XMLType) -> int:
  all_stations = xml.getElementsByTagName('objStation')
  return len(all_stations)


def Main() -> None:
  """Main entry point."""
  data_xml = LoadStations()
  xml = ConvertToXML(data_xml)
  station_count = CountStations(xml)

  print(f'Ireland has {station_count} stations')


if __name__ == '__main__':
  Main()
