#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""Running Trains Loader."""

# import logging
import pdb
from typing import Optional
import urllib.request
import xml.dom.minidom

__author__ = 'BellaKeri@github.com'
__version__ = (1, 0)


ALL_RUNNING_TRAINS_URL = 'http://api.irishrail.ie/realtime/realtime.asmx/getCurrentTrainsXML'

XMLType = xml.dom.minidom.Document
XMLElement = xml.dom.minidom.Element


def LoadTrains() -> str:
  return urllib.request.urlopen(ALL_RUNNING_TRAINS_URL).read()


def ConvertToXML(xml_data_trains: str) -> XMLType:
  return xml.dom.minidom.parseString(xml_data_trains)


def GetTrains(xml_trains_obj: XMLType) -> list[XMLElement]:
  return list(xml_trains_obj.getElementsByTagName('objTrainPositions'))


def TrainsData(message_data : list[XMLElement]) -> list[tuple[str, str, str]]:
  names: list[tuple[str, str, str]] = []
  for message in message_data:
    code = message.getElementsByTagName('TrainCode')[0].firstChild.nodeValue
    direct = message.getElementsByTagName('Direction')[0].firstChild.nodeValue
    public_mss = message.getElementsByTagName('PublicMessage')[0].firstChild.nodeValue
    names.append(
      ('-' if code is None else code.upper().strip(),
       '-' if direct is None else direct.strip(),
       '-' if public_mss is None else public_mss))
  return sorted(names)


def Main() -> None:
  """Main entry point."""
  xml_data = LoadTrains()
  xml_trains_obj = ConvertToXML(xml_data)
  message_data = GetTrains(xml_trains_obj)
  parsed_data = TrainsData(message_data)

  print()
  print()
  print()
  for i, (code, direct, public_mss) in enumerate(parsed_data, start=1):
    print(f'{i}: {code}, {direct} : {public_mss.strip()}')
  print()
  print()
  print()


if __name__ == '__main__':
  Main()
