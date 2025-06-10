#!/usr/bin/python3 -O
#
# Copyright 2025 BellaKeri (BellaKeri@github.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
"""Running Trains Loader."""

# import logging
# import pdb(ativar quando for programmar, ajuda a ver os erros.)

import urllib.request
import xml.dom.minidom

__author__ = 'BellaKeri@github.com'
__version__ = (1, 0)


ALL_RUNNING_TRAINS_URL = 'http://api.irishrail.ie/realtime/realtime.asmx/getCurrentTrainsXML'

XMLType = xml.dom.minidom.Document
XMLElement = xml.dom.minidom.Element

# Get the Trains code.

def LoadTrains() -> [str]:
  pass 


def ConvertToXml(xml_data_trains: str) -> []:
  pass


def GetTrains(xml_trains_obj) ->[]:
  pass


def TrainsData(message_data) -> []:
  pass



def Main() -> None:
  """Main entry point."""
  xml_data = LoadTrains()
  xml_trains_obj = ConvertToXml(xml_data)
  message_data = GetTrains(xml_trains_obj)
  public_message = TrainsData(message_data)

  print()
  print()
  print()
  print()
  print()
  print()


if __name__ == '__main__':
  Main()
