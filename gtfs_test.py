#!/usr/bin/env python3
#
# Copyright 2025 Daniel Balparda (balparda@gmail.com)
# GNU General Public License v3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
# pylint: disable=invalid-name,protected-access
"""gtfs.py unittest."""

import logging
# import pdb
import unittest
# from unittest import mock

from baselib import base
import gtfs

__author__ = 'balparda@gmail.com (Daniel Balparda)'
__version__ = (1, 0)


class TestGTFS(unittest.TestCase):
  """Tests for gtfs.py."""

  def test_TODO(self) -> None:
    """Test."""


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  unittest.main()
