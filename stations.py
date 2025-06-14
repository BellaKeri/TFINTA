#!/usr/bin/env python3
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
import dataclasses

__author__ = 'BellaKeri@github.com'
__version__ = (1, 0)

# The TfI URLs:
ALL_STATIONS_URL = 'http://api.irishrail.ie/realtime/realtime.asmx/getAllStationsXML'

XMLType = xml.dom.minidom.Document
XMLElement = xml.dom.minidom.Element


@dataclasses.dataclass
class Station:
  """Stations data."""
  station_des: str
  station_alias: Optional[str]
  station_lat: float
  station_long: float
  station_code: str
  station_id: int


def Sum(a: int, b: int) -> int:
  # TODO: remove (just for learning)
  g: int = a + b
  return g


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


def StationDict(stations: list[XMLElement]) -> dict[int, Station]:
  dict_names: dict[int, Station] = {}
  for station in stations:
    desc = station.getElementsByTagName('StationDesc')[0].firstChild.nodeValue
    alias = station.getElementsByTagName('StationAlias')[0].firstChild
    alias_child = None if alias is None else alias.firstChild
    lat = station.getElementsByTagName('StationLatitude')[0].firstChild.nodeValue
    long = station.getElementsByTagName('StationLongitude')[0].firstChild.nodeValue
    code = station.getElementsByTagName('StationCode')[0].firstChild.nodeValue
    id = station.getElementsByTagName('StationId')[0].firstChild.nodeValue
    dict_names[int(id)] = Station(
        station_alias=None if alias_child is None else alias_child.nodeValue, station_code=str(code),
        station_des=str(desc), station_lat=float(lat), station_long=float(long), station_id=int(id))
  return dict_names


def Main() -> None:
  """Main entry point."""
  xml_data = LoadStations()
  xml_obj = ConvertToXML(xml_data)
  stations = GetStations(xml_obj)
  station_data = StationData(stations)
  station_dict = StationDict(stations)

  print()
  print(f'Ireland has {len(stations)} stations')
  print()
#   for i, (code, name, alias, id) in enumerate(station_data, start = 1):
#     print(f'{i}: {code}/{id} - {name}{"" if alias is None else f" ({alias.strip()})"}')
  print(station_dict)


if __name__ == '__main__':
  Main()
