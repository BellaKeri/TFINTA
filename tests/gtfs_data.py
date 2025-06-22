#!/usr/bin/env python3
#
# Copyright 2025 BellaKeri (BellaKeri@github.com) & Daniel Balparda (balparda@github.com)
# Apache-2.0 license
#
# pylint: disable=invalid-name,protected-access
"""gtfs.py unittest."""

import datetime
import io
import os.path
import pathlib
# import pdb
from typing import Any, Self
import zipfile
import zoneinfo

from src.tfinta import gtfs_data_model as dm

__author__ = 'BellaKeri@github.com , balparda@github.com'
__version__: tuple[int, int] = (1, 2)


# test dir
_TEST_DIR: str = os.path.split(__file__)[0]
_DATA_DIR: str = os.path.join(_TEST_DIR, 'data')

# mock test files
OPERATOR_CSV_PATH: str = os.path.join(_DATA_DIR, 'GTFS Operator Files - 20250621.csv')
# the zip directory has a very reduced version of the real data in 202506
ZIP_DIR_1: str = os.path.join(_DATA_DIR, 'zip_1')


def ZipDirBytes(src_dir: pathlib.Path) -> bytes:
  """Create an in-memory ZIP from every *.txt file under `src_dir` (non-recursive)."""
  buf = io.BytesIO()
  with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for txt in src_dir.glob('*.txt'):
      zf.writestr(txt.name, txt.read_text(encoding='utf-8'))
  return buf.getvalue()


class FakeHTTPStream(io.BytesIO):
  """Minimal wrapper that mimics the object returned by urllib.request.urlopen
  (context-manager & read() method).  Accepts *bytes* at construction.
  """

  def __init__(self, payload: bytes) -> None:
    super().__init__(payload)

  def __enter__(self) -> Self:
    return self

  def __exit__(self, unused_exc_type: Any, unused_exc_val: Any, unused_exc_tb: Any):  # type:ignore
    self.close()
    return False  # propagate exceptions


class FakeHTTPFile(FakeHTTPStream):
  """Minimal wrapper that mimics the object returned by urllib.request.urlopen
  (context-manager & read() method).  Accepts *a file path* at construction.
  """

  def __init__(self, payload_path: str) -> None:
    with open(payload_path, 'rb') as payload:
      super().__init__(payload.read())


# this is the data in OPERATOR_CSV_PATH and in ZIP_DIR_1
ZIP_DB_1 = dm.GTFSData(
    tm=1750446841.939905,
    files=dm.OfficialFiles(
        tm=1750446841.939905,
        files={
            "Allen's Bus Hire": {
                'https://www.transportforireland.ie/transitData/Data/GTFS_All.zip': None,
                'https://www.transportforireland.ie/transitData/Data/GTFS_Small_Operators.zip': None,
            },
            'Iarnród Éireann / Irish Rail': {
                'https://www.transportforireland.ie/transitData/Data/GTFS_All.zip': None,
                'https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip': dm.FileMetadata(
                    tm=1750446841.939905,
                    publisher='National Transport Authority',
                    url='https://www.nationaltransport.ie/',
                    language='en',
                    start=datetime.date(2025, 5, 30),
                    end=datetime.date(2026, 5, 30),
                    version='826FB35E-D58B-4FAB-92EC-C5D5CB697E68',
                    email=None,
                ),
                'https://www.transportforireland.ie/transitData/Data/GTFS_Realtime.zip': None,
            },
            'Wexford Bus': {
                'https://www.transportforireland.ie/transitData/Data/GTFS_All.zip': None,
                'https://www.transportforireland.ie/transitData/Data/GTFS_Wexford_Bus.zip': None,
            },
        },
    ),
    stops={
        '8250IR0014': dm.BaseStop(
            id='8250IR0014',
            parent=None,
            code='0',
            name='Dalkey',
            latitude=53.275854,
            longitude=-6.103358,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8250IR0021': dm.BaseStop(
            id='8250IR0021',
            parent=None,
            code='0',
            name='Killiney',
            latitude=53.25571,
            longitude=-6.113167,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8250IR0022': dm.BaseStop(
            id='8250IR0022',
            parent=None,
            code='0',
            name='Shankill',
            latitude=53.236522,
            longitude=-6.117228,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8350IR0122': dm.BaseStop(
            id='8350IR0122',
            parent=None,
            code='0',
            name='Greystones',
            latitude=53.144026,
            longitude=-6.061128,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8350IR0123': dm.BaseStop(
            id='8350IR0123',
            parent=None,
            code='0',
            name='Bray (Daly)',
            latitude=53.203712,
            longitude=-6.100194,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8360IR0003': dm.BaseStop(
            id='8360IR0003',
            parent=None,
            code='0',
            name='Ennis',
            latitude=52.839215,
            longitude=-8.97545,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8360IR0010': dm.BaseStop(
            id='8360IR0010',
            parent=None,
            code='0',
            name='Sixmilebridge',
            latitude=52.738061,
            longitude=-8.785265,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8400IR0127': dm.BaseStop(
            id='8400IR0127',
            parent=None,
            code='0',
            name='Limerick (Colbert)',
            latitude=52.658909,
            longitude=-8.624813,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8460IR0044': dm.BaseStop(
            id='8460IR0044',
            parent=None,
            code='0',
            name='Galway (Ceannt)',
            latitude=53.273766,
            longitude=-9.047075,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8470IR0042': dm.BaseStop(
            id='8470IR0042',
            parent=None,
            code='0',
            name='Ardrahan',
            latitude=53.157044,
            longitude=-8.814752,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8470IR0043': dm.BaseStop(
            id='8470IR0043',
            parent=None,
            code='0',
            name='Athenry',
            latitude=53.30153,
            longitude=-8.748547,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8470IR0049': dm.BaseStop(
            id='8470IR0049',
            parent=None,
            code='0',
            name='Craughwell',
            latitude=53.225817,
            longitude=-8.73576,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
        '8470IR050': dm.BaseStop(
            id='8470IR050',
            parent=None,
            code='0',
            name='Oranmore',
            latitude=53.27558,
            longitude=-8.946804,
            zone=None,
            description=None,
            url=None,
            location=dm.LocationType.STOP,
        ),
    },
    calendar={
        83: dm.CalendarService(
            id=83,
            week=(False, False, False, False, False, False, True),
            start=datetime.date(2025, 6, 1),
            end=datetime.date(2025, 12, 7),
            exceptions={},
        ),
        84: dm.CalendarService(
            id=84,
            week=(False, False, False, False, False, False, False),
            start=datetime.date(2025, 8, 4),
            end=datetime.date(2025, 8, 4),
            exceptions={
                datetime.date(2025, 8, 4): True,
            },
        ),
        87: dm.CalendarService(
            id=87,
            week=(True, True, True, True, True, True, False),
            start=datetime.date(2025, 5, 29),
            end=datetime.date(2025, 12, 13),
            exceptions={
                datetime.date(2025, 6, 2): False,
                datetime.date(2025, 8, 4): False,
                datetime.date(2025, 10, 27): False,
            },
        ),
    },
    shapes={
        '4452_42': dm.Shape(
            id='4452_42',
            points={
                1: dm.ShapePoint(
                    id='4452_42',
                    seq=1,
                    latitude=53.1441008463399,
                    longitude=-6.06088487517706,
                    distance=0.0,
                ),
                2: dm.ShapePoint(
                    id='4452_42',
                    seq=2,
                    latitude=53.1441497,
                    longitude=-6.0608973,
                    distance=5.5,
                ),
                3: dm.ShapePoint(
                    id='4452_42',
                    seq=3,
                    latitude=53.1443514,
                    longitude=-6.0610831,
                    distance=31.16,
                ),
                4: dm.ShapePoint(
                    id='4452_42',
                    seq=4,
                    latitude=53.1446195,
                    longitude=-6.0613355,
                    distance=65.446,
                ),
                5: dm.ShapePoint(
                    id='4452_42',
                    seq=5,
                    latitude=53.1448083,
                    longitude=-6.0615225,
                    distance=89.901,
                ),
                6: dm.ShapePoint(
                    id='4452_42',
                    seq=6,
                    latitude=53.1450306,
                    longitude=-6.061775,
                    distance=119.86,
                ),
                7: dm.ShapePoint(
                    id='4452_42',
                    seq=7,
                    latitude=53.1451908304815,
                    longitude=-6.06195374788812,
                    distance=141.332,
                ),
            },
        ),
        '4669_657': dm.Shape(
            id='4669_657',
            points={
                1: dm.ShapePoint(
                    id='4669_657',
                    seq=1,
                    latitude=52.8392692317831,
                    longitude=-8.97518166525509,
                    distance=0.0,
                ),
                2: dm.ShapePoint(
                    id='4669_657',
                    seq=2,
                    latitude=52.8392347714337,
                    longitude=-8.97516263086331,
                    distance=4.044,
                ),
                3: dm.ShapePoint(
                    id='4669_657',
                    seq=3,
                    latitude=52.8379474,
                    longitude=-8.9744517,
                    distance=155.106,
                ),
                4: dm.ShapePoint(
                    id='4669_657',
                    seq=4,
                    latitude=52.8375,
                    longitude=-8.9742651,
                    distance=206.458,
                ),
                5: dm.ShapePoint(
                    id='4669_657',
                    seq=5,
                    latitude=52.8371903,
                    longitude=-8.9740986,
                    distance=242.704,
                ),
            },
        ),
        '4669_658': dm.Shape(
            id='4669_658',
            points={
                1: dm.ShapePoint(
                    id='4669_658',
                    seq=1,
                    latitude=53.273610484269,
                    longitude=-9.04721964060696,
                    distance=0.0,
                ),
                2: dm.ShapePoint(
                    id='4669_658',
                    seq=2,
                    latitude=53.2735839,
                    longitude=-9.0471444,
                    distance=5.827,
                ),
                3: dm.ShapePoint(
                    id='4669_658',
                    seq=3,
                    latitude=53.2732581,
                    longitude=-9.0461686,
                    distance=80.343,
                ),
                4: dm.ShapePoint(
                    id='4669_658',
                    seq=4,
                    latitude=53.2730648,
                    longitude=-9.0456231,
                    distance=122.619,
                ),
                5: dm.ShapePoint(
                    id='4669_658',
                    seq=5,
                    latitude=53.2727663,
                    longitude=-9.0447944,
                    distance=187.119,
                ),
            },
        ),
    },
    agencies={
        7778017: dm.Agency(
            id=7778017,
            name='Iarnród Éireann / Irish Rail',
            url='https://www.irishrail.ie/en-ie/',
            zone=zoneinfo.ZoneInfo(key='Europe/London'),
            routes={
                '4452_86269': dm.Route(
                    id='4452_86269',
                    agency=7778017,
                    short_name='rail',
                    long_name='Limerick - Galway',
                    route_type=dm.RouteType.RAIL,
                    description=None,
                    url=None,
                    color=None,
                    text_color=None,
                    trips={
                        '4669_10287': dm.Trip(
                            id='4669_10287',
                            route='4452_86269',
                            agency=7778017,
                            service=87,
                            direction=True,
                            shape='4669_658',
                            block='4669_7778018_TxcF5814085-2EF0-4E72-998E-4B282D5CC9AC',
                            headsign='Limerick (Colbert)',
                            name='A481',
                            stops={
                                1: dm.Stop(
                                    id='4669_10287',
                                    seq=1,
                                    stop='8460IR0044',
                                    agency=7778017,
                                    route='4452_86269',
                                    arrival=22500,
                                    departure=22500,
                                    timepoint=True,
                                    headsign='Limerick (Colbert)',
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.NOT_AVAILABLE,
                                ),
                                2: dm.Stop(
                                    id='4669_10287',
                                    seq=2,
                                    stop='8470IR050',
                                    agency=7778017,
                                    route='4452_86269',
                                    arrival=22920,
                                    departure=22920,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                3: dm.Stop(
                                    id='4669_10287',
                                    seq=3,
                                    stop='8470IR0043',
                                    agency=7778017,
                                    route='4452_86269',
                                    arrival=23580,
                                    departure=23820,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                4: dm.Stop(
                                    id='4669_10287',
                                    seq=4,
                                    stop='8470IR0049',
                                    agency=7778017,
                                    route='4452_86269',
                                    arrival=24360,
                                    departure=24420,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                5: dm.Stop(
                                    id='4669_10287',
                                    seq=5,
                                    stop='8470IR0042',
                                    agency=7778017,
                                    route='4452_86269',
                                    arrival=24900,
                                    departure=24960,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                            },
                        ),
                        '4669_10288': dm.Trip(
                            id='4669_10288',
                            route='4452_86269',
                            agency=7778017,
                            service=87,
                            direction=True,
                            shape='4669_657',
                            block='4669_7778018_Txc107C7D84-5B07-4FDE-8875-8E9673265809',
                            headsign='Limerick (Colbert)',
                            name='A471',
                            stops={
                                1: dm.Stop(
                                    id='4669_10288',
                                    seq=1,
                                    stop='8360IR0003',
                                    agency=7778017,
                                    route='4452_86269',
                                    arrival=24600,
                                    departure=24600,
                                    timepoint=True,
                                    headsign='Limerick (Colbert)',
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.NOT_AVAILABLE,
                                ),
                                2: dm.Stop(
                                    id='4669_10288',
                                    seq=2,
                                    stop='8360IR0010',
                                    agency=7778017,
                                    route='4452_86269',
                                    arrival=25560,
                                    departure=25560,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                3: dm.Stop(
                                    id='4669_10288',
                                    seq=3,
                                    stop='8400IR0127',
                                    agency=7778017,
                                    route='4452_86269',
                                    arrival=27000,
                                    departure=27000,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.NOT_AVAILABLE,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                            },
                        ),
                    },
                ),
                '4452_86289': dm.Route(
                    id='4452_86289',
                    agency=7778017,
                    short_name='DART',
                    long_name='Bray - Howth',
                    route_type=dm.RouteType.RAIL,
                    description=None,
                    url=None,
                    color=None,
                    text_color=None,
                    trips={
                        '4452_2655': dm.Trip(
                            id='4452_2655',
                            route='4452_86289',
                            agency=7778017,
                            service=83,
                            direction=False,
                            shape='4452_42',
                            block='4452_7778018_Txc47315F93-ACBE-4CE8-9F30-920A2B0C3C75',
                            headsign='Malahide',
                            name='E818',
                            stops={
                                1: dm.Stop(
                                    id='4452_2655',
                                    seq=1,
                                    stop='8350IR0122',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=69480,
                                    departure=69480,
                                    timepoint=True,
                                    headsign='Malahide',
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.NOT_AVAILABLE,
                                ),
                                2: dm.Stop(
                                    id='4452_2655',
                                    seq=2,
                                    stop='8350IR0123',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=70080,
                                    departure=70260,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                3: dm.Stop(
                                    id='4452_2655',
                                    seq=3,
                                    stop='8250IR0022',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=70500,
                                    departure=70560,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                4: dm.Stop(
                                    id='4452_2655',
                                    seq=4,
                                    stop='8250IR0021',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=70680,
                                    departure=70680,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                5: dm.Stop(
                                    id='4452_2655',
                                    seq=5,
                                    stop='8250IR0014',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=70980,
                                    departure=70980,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                            },
                        ),
                        '4452_2662': dm.Trip(
                            id='4452_2662',
                            route='4452_86289',
                            agency=7778017,
                            service=84,
                            direction=False,
                            shape='4452_42',
                            block='4452_7778018_TxcB8ED8C45-6923-4D5B-8601-5F8CC37418F3',
                            headsign='Malahide',
                            name='E818',
                            stops={
                                1: dm.Stop(
                                    id='4452_2662',
                                    seq=1,
                                    stop='8350IR0122',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=69480,
                                    departure=69480,
                                    timepoint=True,
                                    headsign='Malahide',
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.NOT_AVAILABLE,
                                ),
                                2: dm.Stop(
                                    id='4452_2662',
                                    seq=2,
                                    stop='8350IR0123',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=70080,
                                    departure=70260,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                3: dm.Stop(
                                    id='4452_2662',
                                    seq=3,
                                    stop='8250IR0022',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=70500,
                                    departure=70560,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                                4: dm.Stop(
                                    id='4452_2662',
                                    seq=4,
                                    stop='8250IR0021',
                                    agency=7778017,
                                    route='4452_86289',
                                    arrival=70680,
                                    departure=70680,
                                    timepoint=True,
                                    headsign=None,
                                    pickup=dm.StopPointType.REGULAR,
                                    dropoff=dm.StopPointType.REGULAR,
                                ),
                            },
                        ),
                    },
                ),
            },
        ),
    },
)
