#!/usr/bin/env python3
#
# Copyright 2025 Daniel Balparda (balparda@gmail.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
# pylint: disable=invalid-name,protected-access
"""stations.py unittest."""

import logging
# import pdb
import unittest
# from unittest import mock

from baselib import base
from TFINTA import stations

__author__ = 'balparda@gmail.com (Daniel Balparda)'
__version__ = (1, 0)


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
    """Test."""
    xml_obj: stations.XMLType = stations.ConvertToXML(TEST_XML_1)
    self.assertEqual(xml_obj.getElementsByTagName('aaa')[0].firstChild.nodeValue, 'fg')


TEST_XML_1 = """
<xml>
  <aaa>fg</aaa>
</xml>
"""


SUITE: unittest.TestSuite = unittest.TestLoader().loadTestsFromTestCase(TestStations)


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  unittest.main()
