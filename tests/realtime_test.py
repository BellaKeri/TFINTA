#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
# pyright: reportPrivateUsage=false
"""realtime.py unittest."""

# import pdb
import sys
# from unittest import mock

import pytest

# from src.tfinta import realtime
# from src.tfinta import realtime_data_model as dm

# from . import realtime_data


__author__ = 'BellaKeri@github.com , balparda@github.com'


def test_TODO() -> None:
  """Test."""


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
