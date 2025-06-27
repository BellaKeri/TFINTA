#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
# pyright: reportPrivateUsage=false
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
__version__: tuple[int, int] = (1, 3)


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
def test_GTFS_load_and_parse_from_net(
    deserialize: mock.MagicMock,
    serialize: mock.MagicMock,
    urlopen: mock.MagicMock,
    time: mock.MagicMock) -> None:
  """Test."""
  # empty path should raise
  with pytest.raises(gtfs.Error):
    gtfs.GTFS(' \t')  # some extra spaces...
  # mock
  db: gtfs.GTFS
  time.return_value = gtfs_data.ZIP_DB_1_TM
  with (mock.patch('src.tfinta.gtfs.os.path.isdir', autospec=True) as is_dir,
        mock.patch('src.tfinta.gtfs.os.mkdir', autospec=True) as mk_dir,
        mock.patch('src.tfinta.gtfs.os.path.exists', autospec=True) as exists):
    is_dir.return_value = False
    exists.return_value = False
    # create database
    db = gtfs.GTFS('\tdb/path ')  # some extra spaces...
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
        dm.IRISH_RAIL_OPERATOR, dm.IRISH_RAIL_LINK,
        allow_unknown_file=True, allow_unknown_field=True)
    exists.assert_called_once_with('db/path/https__www.transportforireland.ie_transitData_Data_GTFS_Irish_Rail.zip')
    get_time.assert_not_called()
    mock_open.assert_called_once_with('db/path/https__www.transportforireland.ie_transitData_Data_GTFS_Irish_Rail.zip', 'wb')
    handle = cache_file()  # same mock returned by open()
    handle.write.assert_called_once_with(zip_bytes)
  # check calls
  deserialize.assert_not_called()
  assert serialize.call_args_list == [
      mock.call(db._db, file_path='db/path/transit.db', compress=True)] * 2
  # check DB data
  assert db._db == gtfs_data.ZIP_DB_1
  # check other methods and corner cases for the loaded data
  assert db.FindRoute('none') is None
  assert db.FindTrip('none') == (None, None, None)
  assert db.StopName('none') == (None, None, None)
  assert db.StopName('8250IR0022') == ('0', 'Shankill', None)
  with pytest.raises(gtfs.Error):
    db.StopNameTranslator('none')
  with pytest.raises(gtfs.Error, match='empty station'):
    db.StopIDFromNameFragmentOrID(' \t')
  with pytest.raises(gtfs.Error, match=r'Killiney.*Shankill'):
    db.StopIDFromNameFragmentOrID('kill')
  with pytest.raises(gtfs.Error, match='No matches'):
    db.StopIDFromNameFragmentOrID('invalid')
  assert db.StopIDFromNameFragmentOrID('8350IR0122') == '8350IR0122'
  assert db.StopIDFromNameFragmentOrID('grey') == '8350IR0122'
  assert db.StopIDFromNameFragmentOrID('ceannt') == '8460IR0044'
  assert db.StopNameTranslator('8250IR0022') == 'Shankill'
  assert db.ServicesForDay(datetime.date(2025, 8, 4)) == {84}
  assert db.ServicesForDay(datetime.date(2025, 6, 2)) == set()
  assert db.ServicesForDay(datetime.date(2025, 6, 22)) == {83}
  assert db.ServicesForDay(datetime.date(2025, 6, 23)) == {87}
  assert db.ServicesForDay(datetime.date(2028, 7, 1)) == set()
  assert db.FindAgencyRoute('invalid', dm.RouteType.RAIL, 'none') == (None, None)
  agency, route = db.FindAgencyRoute(
      dm.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, 'none')
  assert agency and agency.id == 7778017
  assert route is None
  agency, route = db.FindAgencyRoute(
      dm.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, dm.DART_SHORT_NAME, long_name=dm.DART_LONG_NAME)
  assert agency and agency.id == 7778017
  agency, route = db.FindAgencyRoute(
      dm.IRISH_RAIL_OPERATOR, dm.RouteType.RAIL, dm.DART_SHORT_NAME)
  assert agency and agency.id == 7778017
  assert route and route.id == '4452_86289'
  with pytest.raises(gtfs.Error):
    list(db.PrettyPrintTrip('none'))
  assert gtfs_data.STRIP_ANSI('\n'.join(db.PrettyPrintTrip('4452_2655'))) == gtfs_data.TRIP_4452_2655
  # check corner cases for handlers
  # feed_info.txt
  loc = gtfs._TableLocation(
      operator='Iarnród Éireann / Irish Rail',
      link='https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip',
      file_name='baz.txt')
  info_row = dm.ExpectedFeedInfoCSVRowType(
      # this is the same data in the DB so it will clash
      feed_publisher_name='National Transport Authority',
      feed_publisher_url='https://www.nationaltransport.ie/',
      feed_lang='en',
      feed_start_date='20250530',
      feed_end_date='20240530',  # changed to be invalid
      feed_version='826FB35E-D58B-4FAB-92EC-C5D5CB697E68',
      feed_contact_email=None)
  with pytest.raises(gtfs.RowError, match='1 row'):
    db._HandleFeedInfoRow(loc, 1, info_row)
  with pytest.raises(gtfs.RowError, match='start/end dates'):
    db._HandleFeedInfoRow(loc, 0, info_row)
  info_row['feed_end_date'] = '20260530'  # the original
  with pytest.raises(gtfs.ParseIdenticalVersionError):
    db._HandleFeedInfoRow(loc, 0, info_row)
  # agency.txt - no raise to test
  # calendar.txt
  with pytest.raises(gtfs.RowError, match='inconsistent row'):
    db._HandleCalendarRow(loc, 1, dm.ExpectedCalendarCSVRowType(
        service_id=2, monday=True, tuesday=True, wednesday=True, thursday=True,
        friday=True, saturday=True, sunday=True,
        start_date='20250530', end_date='20240530'))
  # calendar_dates.txt - no raise to test
  # routes.txt - no raise to test
  # shapes.txt
  shape = dm.ExpectedShapesCSVRowType(
      shape_id='foo', shape_pt_sequence=2,
      shape_pt_lat=10.0, shape_pt_lon=10.0,
      shape_dist_traveled=-4.0)  # starts with only invalid distance
  with pytest.raises(gtfs.RowError, match='invalid row'):
    db._HandleShapesRow(loc, 1, shape)
  shape['shape_dist_traveled'] = 4.0  # fix distance
  shape['shape_pt_lat'] = 100.0       # latitude too big
  with pytest.raises(gtfs.RowError, match='invalid row'):
    db._HandleShapesRow(loc, 1, shape)
  shape['shape_pt_lat'] = -100.0  # still too big
  with pytest.raises(gtfs.RowError, match='invalid row'):
    db._HandleShapesRow(loc, 1, shape)
  shape['shape_pt_lat'] = 10.0   # fix latitude
  shape['shape_pt_lon'] = 185.0  # longitude too big
  with pytest.raises(gtfs.RowError, match='invalid row'):
    db._HandleShapesRow(loc, 1, shape)
  shape['shape_pt_lon'] = -185.0  # still too big
  with pytest.raises(gtfs.RowError, match='invalid row'):
    db._HandleShapesRow(loc, 1, shape)
  # trips.txt
  with pytest.raises(gtfs.RowError, match='agency in row was not found'):
    db._HandleTripsRow(loc, 1, dm.ExpectedTripsCSVRowType(
        trip_id='foo', route_id='bar', service_id=10, direction_id=True,
        shape_id=None, trip_headsign=None, block_id=None, trip_short_name=None))
  # stops.txt
  stop = dm.ExpectedStopsCSVRowType(
      stop_id='foo',
      parent_station='bar',  # parent station is invalid
      stop_code='baz', stop_name='STOP!',
      stop_lat=10.0, stop_lon=10.0,
      zone_id=None, stop_desc=None, stop_url=None, location_type=None)
  with pytest.raises(gtfs.RowError, match='parent_station in row was not found'):
    db._HandleStopsRow(loc, 1, stop)
  stop['parent_station'] = None  # fix parent
  stop['stop_lat'] = 100.0  # latitude too big
  with pytest.raises(gtfs.RowError, match='invalid latitude/longitude'):
    db._HandleStopsRow(loc, 1, stop)
  stop['stop_lat'] = -100.0  # still too big
  with pytest.raises(gtfs.RowError, match='invalid latitude/longitude'):
    db._HandleStopsRow(loc, 1, stop)
  stop['stop_lat'] = 100.0  # fix latitude
  stop['stop_lon'] = 185.0  # longitude too big
  with pytest.raises(gtfs.RowError, match='invalid latitude/longitude'):
    db._HandleStopsRow(loc, 1, stop)
  stop['stop_lon'] = -185.0  # still too big
  with pytest.raises(gtfs.RowError, match='invalid latitude/longitude'):
    db._HandleStopsRow(loc, 1, stop)
  # stop_times.txt
  stop_time = dm.ExpectedStopTimesCSVRowType(
      trip_id='4669_10288', stop_sequence=10, stop_id='8360IR0003',
      arrival_time='10:00:00', departure_time='09:00:00',  # departure before arrival!
      timepoint=True, stop_headsign=None, pickup_type=None, drop_off_type=None, dropoff_type=None)
  with pytest.raises(gtfs.RowError, match='invalid row'):
    db._HandleStopTimesRow(loc, 1, stop_time)
  stop_time['departure_time'] = '10:00:10'  # valid
  stop_time['stop_id'] = 'foo'              # invalid
  with pytest.raises(gtfs.RowError, match='stop_id in row was not found'):
    db._HandleStopTimesRow(loc, 1, stop_time)
  stop_time['stop_id'] = '8360IR0003'  # valid
  stop_time['trip_id'] = 'bar'         # invalid
  with pytest.raises(gtfs.RowError, match='trip_id in row was not found'):
    db._HandleStopTimesRow(loc, 1, stop_time)


@mock.patch('balparda_baselib.base.BinSerialize', autospec=True)
@mock.patch('balparda_baselib.base.BinDeSerialize', autospec=True)
def test_GTFS_load_existing(deserialize: mock.MagicMock, serialize: mock.MagicMock) -> None:
  """Test."""
  # mock
  deserialize.return_value = dm.GTFSData(
      tm=0.0, files=dm.OfficialFiles(tm=0.0, files={}),
      agencies={}, calendar={}, shapes={}, stops={})
  with (mock.patch('src.tfinta.gtfs.os.path.isdir', autospec=True) as is_dir,
        mock.patch('src.tfinta.gtfs.os.mkdir', autospec=True) as mk_dir,
        mock.patch('src.tfinta.gtfs.os.path.exists', autospec=True) as exists):
    is_dir.return_value = True
    exists.return_value = True
    # create database
    gtfs.GTFS(' db/path\t')  # some extra spaces...
    # check creation path
    is_dir.assert_called_once_with('db/path')
    mk_dir.assert_not_called()
    exists.assert_called_once_with('db/path/transit.db')
  deserialize.assert_called_once_with(file_path='db/path/transit.db', compress=True)
  serialize.assert_not_called()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_load(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  assert gtfs.main(['read']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_called_once_with(
      'Iarnród Éireann / Irish Rail',
      'https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip',
      freshness=10, allow_unknown_file=True, allow_unknown_field=False,
      force_replace=False, override=None)
  db_obj.PrettyPrintTrip.assert_not_called()


@mock.patch('src.tfinta.gtfs.GTFS', autospec=True)
def test_main_print(mock_gtfs: mock.MagicMock) -> None:
  """Test."""
  db_obj = mock.MagicMock()
  mock_gtfs.return_value = db_obj
  db_obj.PrettyPrintTrip.return_value = ['foo', 'bar']
  assert gtfs.main(['print', 'trip', '-i', 'tid']) == 0
  mock_gtfs.assert_called_once_with('/Users/balparda/py/TFINTA/src/tfinta/.tfinta-data')
  db_obj.LoadData.assert_not_called()
  db_obj.PrettyPrintTrip.assert_called_once_with('tid')


if __name__ == '__main__':
  # run only the tests in THIS file but pass through any extra CLI flags
  args: list[str] = sys.argv[1:] + [__file__]
  print(f'pytest {" ".join(args)}')
  sys.exit(pytest.main(sys.argv[1:] + [__file__]))
