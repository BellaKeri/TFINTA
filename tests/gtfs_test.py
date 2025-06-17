#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
"""gtfs.py unittest."""

import logging
# import pdb
import unittest
# from unittest import mock

from balparda_baselib import base  # pylint: disable=import-error
# TODO: fix import errors
from src.tfinta import gtfs

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__ = (1, 1)


class TestGTFS(unittest.TestCase):
  """Tests for gtfs.py."""

  def test_TODO(self) -> None:
    """Test."""


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format=base.LOG_FORMAT)  # set this as default
  unittest.main(verbosity=2)
