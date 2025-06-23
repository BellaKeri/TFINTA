#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
# pyright: reportPrivateUsage=false
"""dart.py unittest."""

import datetime
# import pdb
import sys
from typing import Generator
from unittest import mock

import pytest

from src.tfinta import dart
from src.tfinta import gtfs
# from src.tfinta import gtfs_data_model as dm

from . import gtfs_data


__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 2)


@pytest.fixture
def gtfs_object() -> Generator[gtfs.GTFS, None, None]:
  """A GTFS object with all gtfs_data.ZIP_DB_1 data loaded."""
  # create object with all the disk features disabled
  db: gtfs.GTFS
  with (mock.patch('src.tfinta.gtfs.time.time', autospec=True) as time,
        mock.patch('src.tfinta.gtfs.os.path.isdir', autospec=True) as is_dir,
        mock.patch('src.tfinta.gtfs.os.mkdir', autospec=True),
        mock.patch('src.tfinta.gtfs.os.path.exists', autospec=True) as exists,
        mock.patch('balparda_baselib.base.BinSerialize', autospec=True),
        mock.patch('balparda_baselib.base.BinDeSerialize', autospec=True)):
    time.return_value = gtfs_data.ZIP_DB_1_TM
    is_dir.return_value = False
    exists.return_value = False
    db = gtfs.GTFS('db/path')
  # monkey-patch the data into the object
  db._db = gtfs_data.ZIP_DB_1
  yield db


def test_DART(gtfs_object: gtfs.GTFS) -> None:  # pylint: disable=redefined-outer-name
  """Test."""
  with pytest.raises(gtfs.Error):
    dart.DART(None)  # type: ignore
  db = dart.DART(gtfs_object)
  assert db.Services() == {83, 84}
  assert db.ServicesForDay(datetime.date(2025, 8, 4)) == {84}
  assert db.ServicesForDay(datetime.date(2025, 6, 22)) == {83}
  assert db.ServicesForDay(datetime.date(2025, 6, 23)) == set()
  assert db._dart_trips == gtfs_data.DART_TRIPS_ZIP_1
  with pytest.raises(gtfs.Error):
    list(db.PrettyDaySchedule(None))  # type: ignore
  assert '\n'.join(db.PrettyDaySchedule(datetime.date(2025, 8, 4))) == gtfs_data.SCHEDULE_2025_08_04


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
