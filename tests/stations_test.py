#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
"""stations.py unittest."""

# import pdb
import sys
# from unittest import mock

import pytest

from src.tfinta import stations

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 2)


def test_Soma() -> None:
  """Test."""
  # TODO: remove (just for learning)
  print('sum test start')
  assert stations.Sum(0, 0) == 0
  assert stations.Sum(0, 1) == 1
  assert stations.Sum(1, 0) == 1
  assert stations.Sum(-1, 1) == 0
  assert stations.Sum(666, 333) == 999
  assert stations.Sum(-2, -3) == -5
  assert stations.Sum(-5, 0) == -5
  print('sum test end')


def test_ConvertToXML() -> None:
  """Test XML"""
  xml_obj: stations.XMLType = stations.ConvertToXML(TEST_XML_1)
  assert xml_obj.getElementsByTagName('xml_data')[0].firstChild.nodeValue == 'convert'


def test_GetStations() -> None:
  """Test Stations"""
  xml_obj: stations.XMLType = stations.ConvertToXML(TEST_STATIONS_1)
  test_station: list[stations.XMLElement] = stations.GetStations(xml_obj)
  assert len(test_station) == 1
  station = test_station[0]
  assert station.firstChild.nodeValue == 'getstations'


TEST_XML_1 = """
<xml>
  <xml_data>convert</xml_data>
</xml>
"""

TEST_STATIONS_1 = """
<stations>
  <objStation>getstations</objStation>
</stations>
"""


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
