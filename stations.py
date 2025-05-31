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
XMLElement = xml.dom.minidom.Element


def LoadStations() -> str:
  with urllib.request.urlopen(ALL_STATIONS_URL) as rail_data:
    return rail_data.read()


def ConvertToXML(xml_data: str) -> XMLType:
  return xml.dom.minidom.parseString(xml_data)


def GetStations(xml_obj: XMLType) -> list[XMLElement]:
  return list(xml_obj.getElementsByTagName('objStation'))


def StationNames(stations: list[XMLElement]) -> list[str]:
  return ['empty']


def Main() -> None:
  """Main entry point."""
  xml_data = LoadStations()
  xml_obj = ConvertToXML(xml_data)
  stations = GetStations(xml_obj)
  names = StationNames(stations)

  print()
  print(f'Ireland has {len(stations)} stations')
  print()
  print('Names: TODO')
  print()


if __name__ == '__main__':
  Main()
