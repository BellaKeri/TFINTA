#!/usr/bin/python3 -O
#
# Copyright 2025 BellaKeri (BellaKeri@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""Stations loader."""

# import logging
import pdb
from typing import Optional
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
  # equivale a: return urllib.request.urlopen(ALL_STATIONS_URL).read()


def ConvertToXML(xml_data: str) -> XMLType:
  return xml.dom.minidom.parseString(xml_data)


def GetStations(xml_obj: XMLType) -> list[XMLElement]:
  return list(xml_obj.getElementsByTagName('objStation'))


def StationData(stations: list[XMLElement]) -> list[tuple[str, str, Optional[str], int]]:
  names: list[tuple[str, str, Optional[str], int]] = []
  for station in stations:
    desc = station.getElementsByTagName('StationDesc')[0].firstChild.nodeValue
    alias = station.getElementsByTagName('StationAlias')[0].firstChild
    code = station.getElementsByTagName('StationCode')[0].firstChild.nodeValue
    id = station.getElementsByTagName('StationId')[0].firstChild.nodeValue
    names.append(
        ('-' if code is None else code.upper().strip(),
         '-' if desc is None else desc.strip(),
         None if alias is None else alias.nodeValue,
         0 if id is None else int(id)))
  return sorted(names)



def Main() -> None:
  """Main entry point."""
  xml_data = LoadStations()
  xml_obj = ConvertToXML(xml_data)
  stations = GetStations(xml_obj)
  station_data = StationData(stations)

  print()
  print(f'Ireland has {len(stations)} stations')
  print()
  for i, (code, name, alias, id) in enumerate(station_data, start = 1):
    print(f'{i}: {code}/{id} - {name}{"" if alias is None else f" ({alias.strip()})"}')
  print()


if __name__ == '__main__':
  Main()
