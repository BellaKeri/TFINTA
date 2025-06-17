#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
"""stations.py unittest."""

import logging
# import pdb
import unittest
# from unittest import mock

from balparda_baselib import base  # pylint: disable=import-error
# TODO: fix import errors
from src.tfinta import stations

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__ = (1, 1)


class TestStations(unittest.TestCase):
  """Tests for stations.py."""

  def test_TODO(self) -> None:  # copy and rename
    """Test."""
    print('ok')  # do the test here

  def test_Soma(self) -> None:
    """Test."""
    # TODO: remove (just for learning)
    print('sum test start')
    self.assertEqual(stations.Sum(0, 0), 0)
    self.assertEqual(stations.Sum(0, 1), 1)
    self.assertEqual(stations.Sum(1, 0), 1)
    self.assertEqual(stations.Sum(-1, 1), 0)
    self.assertEqual(stations.Sum(666, 333), 999)
    self.assertEqual(stations.Sum(-2, -3), -5)
    self.assertEqual(stations.Sum(-5, 0), -5)
    print('sum test end')

  def test_ConvertToXML(self) -> None:
    """Test XML"""
    xml_obj: stations.XMLType = stations.ConvertToXML(TEST_XML_1)
    self.assertEqual(xml_obj.getElementsByTagName('xml_data')[0].firstChild.nodeValue, 'convert')

  def test_GetStations(self) -> None:
    """Test Stations"""
    xml_obj: stations.XMLType = stations.ConvertToXML(TEST_STATIONS_1)
    test_station: list[stations.XMLElement] = stations.GetStations(xml_obj)
    self.assertEqual(len(test_station), 1)
    station = test_station[0]
    self.assertEqual(station.firstChild.nodeValue, 'getstations')


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
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  unittest.main()
