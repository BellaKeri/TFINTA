#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
"""Running Trains Loader. DO NOT USE - OLD CODE."""

# import logging
# import pdb
import urllib.request
import xml.dom.minidom
import dataclasses
import sys

from . import tfinta_base as base

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = base.__version__


ALL_RUNNING_TRAINS_URL = 'http://api.irishrail.ie/realtime/realtime.asmx/getCurrentTrainsXML'

XMLType = xml.dom.minidom.Document
XMLElement = xml.dom.minidom.Element


@dataclasses.dataclass
class Trains:
  """Stations data."""
  trains_status: str
  trains_direct: str
  trains_lat: float
  trains_long: float
  trains_code: str
  trains_date: str
  trains_public_mss: str


def LoadTrains() -> str:
  return urllib.request.urlopen(ALL_RUNNING_TRAINS_URL).read()


def ConvertToXML(xml_data_trains: str, /) -> XMLType:
  return xml.dom.minidom.parseString(xml_data_trains)


def GetTrains(xml_trains_obj: XMLType, /) -> list[XMLElement]:
  return list(xml_trains_obj.getElementsByTagName('objTrainPositions'))


def TrainsData(trains_data : list[XMLElement], /) -> list[tuple[str, str, str]]:
  trains_information: list[tuple[str, str, str]] = []
  for data_type in trains_data:
    code = data_type.getElementsByTagName('TrainCode')[0].firstChild.nodeValue
    direct = data_type.getElementsByTagName('Direction')[0].firstChild.nodeValue
    public_mss = data_type.getElementsByTagName('PublicMessage')[0].firstChild.nodeValue
    trains_information.append(
      ('-' if code is None else code.upper().strip(),
       '-' if direct is None else direct.strip(),
       '-' if public_mss is None else public_mss))
  return sorted(trains_information)


def TrainsDict(trains_data: list[XMLElement], /) -> dict[int, Trains]:
  dict_trains_information: dict[int, Trains] = {}
  for data_type in trains_data:
    status = data_type.getElementsByTagName('TrainStatus')[0].firstChild.nodeValue
    direct = data_type.getElementsByTagName('Direction')[0].firstChild
    date = data_type.getElementsByTagName('TrainDate')[0].firstChild
    lat = data_type.getElementsByTagName('TrainLatitude')[0].firstChild.nodeValue
    long = data_type.getElementsByTagName('TrainLongitude')[0].firstChild.nodeValue
    code = data_type.getElementsByTagName('TrainCode')[0].firstChild.nodeValue
    public = data_type.getElementsByTagName('PublicMessage')[0].firstChild.nodeValue
    dict_trains_information[str(date)] = Trains(
        trains_status=str(status), trains_direct=str(direct), trains_code=str(code),
        trains_date=str(date), trains_lat=float(lat), trains_long=float(long), trains_public_mss=str(public))
  return dict_trains_information


def main(unused_argv: list[str] | None = None) -> int:  # pylint: disable=invalid-name
  """Main entry point."""
  xml_data = LoadTrains()
  xml_trains_obj = ConvertToXML(xml_data)
  trains_data = GetTrains(xml_trains_obj)
  parsed_data = TrainsData(trains_data)
  station_dict = TrainsDict(trains_data)

  print()
  print()
  print()
  for i, (code, direct, public_mss) in enumerate(parsed_data, start=1):
    print(f'{i}: {code}, {direct} : {public_mss.strip()}')
  print()
  print()
  print(station_dict)
  print()
  return 0


if __name__ == '__main__':
  sys.exit(main())
