#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
"""gtfs.py unittest."""

import datetime
import pathlib
# import pdb
import sys
from unittest import mock

import pytest

from src.tfinta import gtfs
from src.tfinta import gtfs_data_model as dm

from . import gtfs_data


__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 2)


@pytest.mark.parametrize('hms', [
    '01', '01:01', '01:01:aa', '00:-1:00', '00:00:-1', '00:60:00', '00:00:60',
])
def test_HMSToSeconds_fail(hms: str) -> None:
  """Test."""
  with pytest.raises(ValueError):
    gtfs.HMSToSeconds(hms)


@pytest.mark.parametrize('hms, sec', [
    ('00:00:00', 0),
    ('00:00:01', 1),
    ('00:00:10', 10),
    ('00:01:00', 60),
    ('00:10:00', 600),
    ('01:00:00', 3600),
    ('10:00:00', 36000),
    ('23:59:59', 86399),
    ('24:00:00', 86400),
    ('24:01:01', 86461),
    ('240:33:11', 865991),
    ('666:33:11', 2399591),
])
def test_HMSToSeconds(hms: str, sec: int) -> None:
  """Test."""
  assert gtfs.HMSToSeconds(hms) == sec


@pytest.mark.parametrize('sec, hms', [
    (0, '00:00:00'),
    (1, '00:00:01'),
    (60, '00:01:00'),
    (3600, '01:00:00'),
    (86399, '23:59:59'),
    (86400, '24:00:00'),
    (2399591, '666:33:11'),
])
def test_SecondsToHMS(sec: int, hms: str) -> None:
  """Test."""
  assert gtfs.SecondsToHMS(sec) == hms
  if sec:
    with pytest.raises(ValueError):
      gtfs.SecondsToHMS(-sec)  # if not zero, negative values should always fail


@mock.patch('src.tfinta.gtfs.time.time', autospec=True)
@mock.patch('src.tfinta.gtfs.urllib.request.urlopen', autospec=True)
@mock.patch('balparda_baselib.base.BinSerialize', autospec=True)
@mock.patch('balparda_baselib.base.BinDeSerialize', autospec=True)
def test_GTFS(
    deserialize: mock.MagicMock,
    serialize: mock.MagicMock,
    urlopen: mock.MagicMock,
    time: mock.MagicMock) -> None:
  """Test."""
  # empty path should raise
  with pytest.raises(gtfs.Error):
    gtfs.GTFS(' \t')
  # mock
  db: gtfs.GTFS
  time.return_value = 1750446841.939905
  with (mock.patch('src.tfinta.gtfs.os.path.isdir', autospec=True) as is_dir,
        mock.patch('src.tfinta.gtfs.os.mkdir', autospec=True) as mk_dir,
        mock.patch('src.tfinta.gtfs.os.path.exists', autospec=True) as exists):
    is_dir.return_value = False
    exists.return_value = False
    # create database
    db = gtfs.GTFS('\tdb/path ')
    # check creation path
    is_dir.assert_called_once_with('db/path')
    mk_dir.assert_called_once_with('db/path')
    exists.assert_called_once_with('db/path/transit.db')
  # load the GTFS data into database: do it BEFORE we mock open()!
  cache_file = mock.mock_open()
  fake_csv = gtfs_data.FakeHTTPFile(gtfs_data.OPERATOR_CSV_PATH)
  zip_bytes: bytes = gtfs_data.ZipDirBytes(pathlib.Path(gtfs_data.ZIP_DIR_1))
  fake_zip = gtfs_data.FakeHTTPStream(zip_bytes)
  with (mock.patch('src.tfinta.gtfs.os.path.exists', autospec=True) as exists,
        mock.patch('src.tfinta.gtfs.os.path.getmtime', autospec=True) as get_time,
        mock.patch('builtins.open', cache_file) as mock_open):
    exists.return_value = False
    urlopen.side_effect = [fake_csv, fake_zip]
    db.LoadData(
        gtfs.IRISH_RAIL_OPERATOR, gtfs.IRISH_RAIL_LINK,
        allow_unknown_file=True, allow_unknown_field=True)
    exists.assert_called_once_with('db/path/https__www.transportforireland.ie_transitData_Data_GTFS_Irish_Rail.zip')
    get_time.assert_not_called()
    mock_open.assert_called_once_with('db/path/https__www.transportforireland.ie_transitData_Data_GTFS_Irish_Rail.zip', 'wb')
    handle = cache_file()  # same mock returned by open()
    handle.write.assert_called_once_with(zip_bytes)
  # check calls
  deserialize.assert_not_called()
  assert serialize.call_args_list == [
      mock.call(db._db, file_path='db/path/transit.db', compress=True)] * 2  # type:ignore
  # check DB data
  assert db._db == gtfs_data.ZIP_DB_1  # type:ignore
  # check other methods and corner cases for the loaded data
  assert db.FindRoute('none') is None
  assert db.FindTrip('none') == (None, None, None)
  assert db.StopName('none') == (None, None, None)
  assert db.StopName('8250IR0022') == ('0', 'Shankill', None)
  assert db.ServicesForDay(datetime.date(2025, 8, 4)) == {84}
  assert db.ServicesForDay(datetime.date(2025, 6, 2)) == set()
  assert db.ServicesForDay(datetime.date(2025, 6, 22)) == {83}
  assert db.ServicesForDay(datetime.date(2025, 6, 23)) == {87}
  assert db.ServicesForDay(datetime.date(2028, 7, 1)) == set()
  assert db.FindAgencyRoute('invalid', dm.RouteType.RAIL, 'none') == (None, None)
  agency, route = db.FindAgencyRoute(
      gtfs.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, 'none')
  assert agency and agency.id == 7778017
  assert route is None
  agency, route = db.FindAgencyRoute(
      gtfs.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, 'DART', long_name='Bray - Howth')
  assert agency and agency.id == 7778017
  assert route and route.id == '4452_86289'
  assert '\n'.join(db.PrettyPrintTrip('4452_2655')) == gtfs_data.TRIP_4452_2655


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
