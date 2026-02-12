# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""GTFS unittest data."""

from __future__ import annotations

import collections
import datetime
import io
import pathlib
import zipfile
import zoneinfo

from tfinta import gtfs_data_model as dm
from tfinta import tfinta_base as base

from . import util


def ZipDirBytes(src_dir: pathlib.Path, /) -> bytes:
  """Create an in-memory ZIP from every *.txt file under `src_dir` (non-recursive).

  Args:
    src_dir: directory containing .txt files to be zipped.

  Returns:
    bytes of the created ZIP file.

  """
  buf = io.BytesIO()
  with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for txt in src_dir.glob('*.txt'):
      zf.writestr(txt.name, txt.read_text(encoding='utf-8'))
  return buf.getvalue()


####################################################################################################
# PURE GTFS
####################################################################################################


# this is the data in OPERATOR_CSV_PATH and in ZIP_DIR_1
ZIP_DB_1_TM = 1750446841.939905
ZIP_DB_1 = dm.GTFSData(
  tm=ZIP_DB_1_TM,
  files=dm.OfficialFiles(
    tm=ZIP_DB_1_TM,
    files={
      "Allen's Bus Hire": {
        'https://www.transportforireland.ie/transitData/Data/GTFS_All.zip': None,
        'https://www.transportforireland.ie/transitData/Data/GTFS_Small_Operators.zip': None,
      },
      'Iarnród Éireann / Irish Rail': {
        'https://www.transportforireland.ie/transitData/Data/GTFS_All.zip': None,
        'https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip': dm.FileMetadata(
          tm=ZIP_DB_1_TM,
          publisher='National Transport Authority',
          url='https://www.nationaltransport.ie/',
          language='en',
          days=base.DaysRange(
            start=datetime.date(2025, 5, 30),
            end=datetime.date(2026, 5, 30),
          ),
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
      point=base.Point(
        latitude=53.275854,
        longitude=-6.103358,
      ),
    ),
    '8250IR0021': dm.BaseStop(
      id='8250IR0021',
      parent=None,
      code='0',
      name='Killiney',
      point=base.Point(
        latitude=53.25571,
        longitude=-6.113167,
      ),
    ),
    '8250IR0022': dm.BaseStop(
      id='8250IR0022',
      parent=None,
      code='0',
      name='Shankill',
      point=base.Point(
        latitude=53.236522,
        longitude=-6.117228,
      ),
    ),
    '8350IR0122': dm.BaseStop(
      id='8350IR0122',
      parent=None,
      code='0',
      name='Greystones',
      point=base.Point(
        latitude=53.144026,
        longitude=-6.061128,
      ),
    ),
    '8350IR0123': dm.BaseStop(
      id='8350IR0123',
      parent='8350IR0122',
      code='0',
      name='Bray (Daly)',
      point=base.Point(
        latitude=53.203712,
        longitude=-6.100194,
      ),
    ),
    '8360IR0003': dm.BaseStop(
      id='8360IR0003',
      parent=None,
      code='0',
      name='Ennis',
      point=base.Point(
        latitude=52.839215,
        longitude=-8.97545,
      ),
    ),
    '8360IR0010': dm.BaseStop(
      id='8360IR0010',
      parent=None,
      code='0',
      name='Sixmilebridge',
      point=base.Point(
        latitude=52.738061,
        longitude=-8.785265,
      ),
    ),
    '8400IR0127': dm.BaseStop(
      id='8400IR0127',
      parent=None,
      code='0',
      name='Limerick (Colbert)',
      point=base.Point(
        latitude=52.658909,
        longitude=-8.624813,
      ),
    ),
    '8460IR0044': dm.BaseStop(
      id='8460IR0044',
      parent=None,
      code='0',
      name='Galway (Ceannt)',
      point=base.Point(
        latitude=53.273766,
        longitude=-9.047075,
      ),
    ),
    '8470IR0042': dm.BaseStop(
      id='8470IR0042',
      parent=None,
      code='0',
      name='Ardrahan',
      point=base.Point(
        latitude=53.157044,
        longitude=-8.814752,
      ),
    ),
    '8470IR0043': dm.BaseStop(
      id='8470IR0043',
      parent=None,
      code='0',
      name='Athenry',
      point=base.Point(
        latitude=53.30153,
        longitude=-8.748547,
      ),
    ),
    '8470IR0049': dm.BaseStop(
      id='8470IR0049',
      parent=None,
      code='0',
      name='Craughwell',
      point=base.Point(
        latitude=53.225817,
        longitude=-8.73576,
      ),
    ),
    '8470IR050': dm.BaseStop(
      id='8470IR050',
      parent=None,
      code='0',
      name='Oranmore',
      point=base.Point(
        latitude=53.27558,
        longitude=-8.946804,
      ),
    ),
  },
  calendar={
    83: dm.CalendarService(
      id=83,
      week=(False, False, False, False, False, False, True),
      days=base.DaysRange(
        start=datetime.date(2025, 6, 1),
        end=datetime.date(2025, 12, 7),
      ),
      exceptions={},
    ),
    84: dm.CalendarService(
      id=84,
      week=(False, False, False, False, False, False, False),
      days=base.DaysRange(
        start=datetime.date(2025, 8, 4),
        end=datetime.date(2025, 8, 4),
      ),
      exceptions={
        datetime.date(2025, 8, 4): True,
      },
    ),
    87: dm.CalendarService(
      id=87,
      week=(True, True, True, True, True, True, False),
      days=base.DaysRange(
        start=datetime.date(2025, 5, 29),
        end=datetime.date(2025, 12, 13),
      ),
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
          point=base.Point(
            latitude=53.1441008463399,
            longitude=-6.06088487517706,
          ),
          distance=0.0,
        ),
        2: dm.ShapePoint(
          id='4452_42',
          seq=2,
          point=base.Point(
            latitude=53.1441497,
            longitude=-6.0608973,
          ),
          distance=5.5,
        ),
        3: dm.ShapePoint(
          id='4452_42',
          seq=3,
          point=base.Point(
            latitude=53.1443514,
            longitude=-6.0610831,
          ),
          distance=31.16,
        ),
        4: dm.ShapePoint(
          id='4452_42',
          seq=4,
          point=base.Point(
            latitude=53.1446195,
            longitude=-6.0613355,
          ),
          distance=65.446,
        ),
        5: dm.ShapePoint(
          id='4452_42',
          seq=5,
          point=base.Point(
            latitude=53.1448083,
            longitude=-6.0615225,
          ),
          distance=89.901,
        ),
        6: dm.ShapePoint(
          id='4452_42',
          seq=6,
          point=base.Point(
            latitude=53.1450306,
            longitude=-6.061775,
          ),
          distance=119.86,
        ),
        7: dm.ShapePoint(
          id='4452_42',
          seq=7,
          point=base.Point(
            latitude=53.1451908304815,
            longitude=-6.06195374788812,
          ),
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
          point=base.Point(
            latitude=52.8392692317831,
            longitude=-8.97518166525509,
          ),
          distance=0.0,
        ),
        2: dm.ShapePoint(
          id='4669_657',
          seq=2,
          point=base.Point(
            latitude=52.8392347714337,
            longitude=-8.97516263086331,
          ),
          distance=4.044,
        ),
        3: dm.ShapePoint(
          id='4669_657',
          seq=3,
          point=base.Point(
            latitude=52.8379474,
            longitude=-8.9744517,
          ),
          distance=155.106,
        ),
        4: dm.ShapePoint(
          id='4669_657',
          seq=4,
          point=base.Point(
            latitude=52.8375,
            longitude=-8.9742651,
          ),
          distance=206.458,
        ),
        5: dm.ShapePoint(
          id='4669_657',
          seq=5,
          point=base.Point(
            latitude=52.8371903,
            longitude=-8.9740986,
          ),
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
          point=base.Point(
            latitude=53.273610484269,
            longitude=-9.04721964060696,
          ),
          distance=0.0,
        ),
        2: dm.ShapePoint(
          id='4669_658',
          seq=2,
          point=base.Point(
            latitude=53.2735839,
            longitude=-9.0471444,
          ),
          distance=5.827,
        ),
        3: dm.ShapePoint(
          id='4669_658',
          seq=3,
          point=base.Point(
            latitude=53.2732581,
            longitude=-9.0461686,
          ),
          distance=80.343,
        ),
        4: dm.ShapePoint(
          id='4669_658',
          seq=4,
          point=base.Point(
            latitude=53.2730648,
            longitude=-9.0456231,
          ),
          distance=122.619,
        ),
        5: dm.ShapePoint(
          id='4669_658',
          seq=5,
          point=base.Point(
            latitude=53.2727663,
            longitude=-9.0447944,
          ),
          distance=187.119,
        ),
      },
    ),
    '4669_68': dm.Shape(
      id='4669_68',
      points={
        1: dm.ShapePoint(
          id='4669_68',
          seq=1,
          point=base.Point(
            latitude=53.1441008463398,
            longitude=-6.06088487517706,
          ),
          distance=0.0,
        ),
        2: dm.ShapePoint(
          id='4669_68',
          seq=2,
          point=base.Point(
            latitude=53.1441497,
            longitude=-6.0608973,
          ),
          distance=5.5,
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
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=22500),
                      departure=base.DayTime(time=22500),
                    ),
                  ),
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
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=22920),
                      departure=base.DayTime(time=22920),
                    ),
                  ),
                ),
                3: dm.Stop(
                  id='4669_10287',
                  seq=3,
                  stop='8470IR0043',
                  agency=7778017,
                  route='4452_86269',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=23580),
                      departure=base.DayTime(time=23820),
                    ),
                  ),
                ),
                4: dm.Stop(
                  id='4669_10287',
                  seq=4,
                  stop='8470IR0049',
                  agency=7778017,
                  route='4452_86269',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=24360),
                      departure=base.DayTime(time=24420),
                    ),
                  ),
                ),
                5: dm.Stop(
                  id='4669_10287',
                  seq=5,
                  stop='8470IR0042',
                  agency=7778017,
                  route='4452_86269',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=24900),
                      departure=base.DayTime(time=24960),
                    ),
                  ),
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
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=24600),
                      departure=base.DayTime(time=24600),
                    ),
                  ),
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
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=25560),
                      departure=base.DayTime(time=25560),
                    ),
                  ),
                ),
                3: dm.Stop(
                  id='4669_10288',
                  seq=3,
                  stop='8400IR0127',
                  agency=7778017,
                  route='4452_86269',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=27000),
                      departure=base.DayTime(time=27000),
                    ),
                  ),
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
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=69480),
                      departure=base.DayTime(time=69480),
                    ),
                  ),
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
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70080),
                      departure=base.DayTime(time=70260),
                    ),
                  ),
                ),
                3: dm.Stop(
                  id='4452_2655',
                  seq=3,
                  stop='8250IR0022',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70500),
                      departure=base.DayTime(time=70560),
                    ),
                  ),
                ),
                4: dm.Stop(
                  id='4452_2655',
                  seq=4,
                  stop='8250IR0021',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70680),
                      departure=base.DayTime(time=70680),
                    ),
                  ),
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
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=69480),
                      departure=base.DayTime(time=69480),
                    ),
                  ),
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
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70080),
                      departure=base.DayTime(time=70260),
                    ),
                  ),
                ),
                3: dm.Stop(
                  id='4452_2662',
                  seq=3,
                  stop='8250IR0022',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70500),
                      departure=base.DayTime(time=70560),
                    ),
                  ),
                ),
                4: dm.Stop(
                  id='4452_2662',
                  seq=4,
                  stop='8250IR0021',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70680),
                      departure=base.DayTime(time=70680),
                    ),
                  ),
                ),
              },
            ),
            '4669_4802': dm.Trip(
              id='4669_4802',
              route='4452_86289',
              agency=7778017,
              service=84,
              direction=False,
              shape='4669_68',
              block='4669_7778018_Txc8293CD9E-01F8-40DB-BD1B-EBC38AE79EB1',
              headsign='Malahide',
              name='E818',
              stops={
                1: dm.Stop(
                  id='4669_4802',
                  seq=1,
                  stop='8350IR0122',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=69480),
                      departure=base.DayTime(time=69480),
                    ),
                  ),
                  headsign='Malahide',
                  pickup=dm.StopPointType.REGULAR,
                  dropoff=dm.StopPointType.NOT_AVAILABLE,
                ),
                2: dm.Stop(
                  id='4669_4802',
                  seq=2,
                  stop='8350IR0123',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70080),
                      departure=base.DayTime(time=70260),
                    ),
                  ),
                ),
                3: dm.Stop(
                  id='4669_4802',
                  seq=3,
                  stop='8250IR0022',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70500),
                      departure=base.DayTime(time=70560),
                    ),
                  ),
                ),
                4: dm.Stop(
                  id='4669_4802',
                  seq=4,
                  stop='8250IR0021',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=70800),
                      departure=base.DayTime(time=70800),
                    ),
                  ),
                ),
              },
            ),
            '4452_2666': dm.Trip(
              id='4452_2666',
              route='4452_86289',
              agency=7778017,
              service=83,
              direction=False,
              shape='4452_42',
              block='4452_776668_TxcB8ED8C45-6923-4D5B-8601-5F8CC37418F3',
              headsign='Malahide',
              name='E666',
              stops={
                1: dm.Stop(
                  id='4452_2666',
                  seq=1,
                  stop='8350IR0122',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=76680),
                      departure=base.DayTime(time=76680),
                    ),
                  ),
                  headsign='Malahide',
                  pickup=dm.StopPointType.REGULAR,
                  dropoff=dm.StopPointType.NOT_AVAILABLE,
                ),
                2: dm.Stop(
                  id='4452_2666',
                  seq=2,
                  stop='8350IR0123',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=77280),
                      departure=base.DayTime(time=77460),
                    ),
                  ),
                ),
                3: dm.Stop(
                  id='4452_2666',
                  seq=3,
                  stop='8250IR0022',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=77700),
                      departure=base.DayTime(time=77760),
                    ),
                  ),
                ),
                4: dm.Stop(
                  id='4452_2666',
                  seq=4,
                  stop='8250IR0021',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=77880),
                      departure=base.DayTime(time=77880),
                    ),
                  ),
                ),
              },
            ),
            '4669_4666': dm.Trip(
              id='4669_4666',
              route='4452_86289',
              agency=7778017,
              service=84,
              direction=True,
              shape='4669_68',
              block='4669_7778018_Txc829999E-01F8-40DB-BD1B-EBC38AE79EB1',
              headsign='Malahide',
              name='E666',
              stops={
                1: dm.Stop(
                  id='4669_4666',
                  seq=1,
                  stop='8250IR0022',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=77700),
                      departure=base.DayTime(time=77760),
                    ),
                  ),
                ),
                2: dm.Stop(
                  id='4669_4666',
                  seq=2,
                  stop='8250IR0021',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=77880),
                      departure=base.DayTime(time=77880),
                    ),
                  ),
                ),
              },
            ),
            '4669_4999': dm.Trip(
              id='4669_4999',
              route='4452_86289',
              agency=7778017,
              service=83,
              direction=False,
              shape='4669_657',
              block='4669_7778018_Txc829999E-01F8-6666-BD1B-EBC38AE79EB1',
              headsign='Malahide',
              name='E666',
              stops={
                1: dm.Stop(
                  id='4669_4999',
                  seq=1,
                  stop='8350IR0122',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=76680),
                      departure=base.DayTime(time=76680),
                    ),
                  ),
                  headsign='Malahide',
                  pickup=dm.StopPointType.REGULAR,
                  dropoff=dm.StopPointType.NOT_AVAILABLE,
                ),
                2: dm.Stop(
                  id='4669_4999',
                  seq=2,
                  stop='8350IR0123',
                  agency=7778017,
                  route='4452_86289',
                  scheduled=dm.ScheduleStop(
                    times=base.DayRange(
                      arrival=base.DayTime(time=77280),
                      departure=base.DayTime(time=77460),
                    ),
                  ),
                ),
              },
            ),
          },
        ),
      },
    ),
  },
)

CALENDARS_TABLE: util.ExpectedPrettyPrint = [
  util.ExpectedTable(
    columns=[
      '[bold cyan]Service[/]',
      '[bold cyan]Start[/]',
      '[bold cyan]End[/]',
      '[bold cyan]Mon[/]',
      '[bold cyan]Tue[/]',
      '[bold cyan]Wed[/]',
      '[bold cyan]Thu[/]',
      '[bold cyan]Fri[/]',
      '[bold cyan]Sat[/]',
      '[bold cyan]Sun[/]',
      '[bold cyan]Exceptions[/]',
    ],
    rows=[
      [
        '[bold cyan]83[/]',
        '[bold yellow]2025-06-01·Sun[/]',
        '[bold]2025-12-07·Sun[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✓[/]',
        '∅',
      ],
      [
        '[bold cyan]84[/]',
        '[bold yellow]2025-08-04·Mon[/]',
        '[bold]∅[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]2025-08-04·Mon ✓[/]',
      ],
      [
        '[bold cyan]87[/]',
        '[bold yellow]2025-05-29·Thu[/]',
        '[bold]2025-12-13·Sat[/]',
        '[bold]✓[/]',
        '[bold]✓[/]',
        '[bold]✓[/]',
        '[bold]✓[/]',
        '[bold]✓[/]',
        '[bold]✓[/]',
        '[bold]✗[/]',
        '[bold]2025-06-02·Mon ✗[/]\n[bold]2025-08-04·Mon ✗[/]\n[bold]2025-10-27·Mon ✗[/]',
      ],
    ],
  ),
]

# DART-specific calendar (services 83 and 84 only)
DART_CALENDARS_TABLE: util.ExpectedPrettyPrint = [
  util.ExpectedTable(
    columns=[
      '[bold cyan]Service[/]',
      '[bold cyan]Start[/]',
      '[bold cyan]End[/]',
      '[bold cyan]Mon[/]',
      '[bold cyan]Tue[/]',
      '[bold cyan]Wed[/]',
      '[bold cyan]Thu[/]',
      '[bold cyan]Fri[/]',
      '[bold cyan]Sat[/]',
      '[bold cyan]Sun[/]',
      '[bold cyan]Exceptions[/]',
    ],
    rows=[
      [
        '[bold cyan]83[/]',
        '[bold yellow]2025-06-01·Sun[/]',
        '[bold]2025-12-07·Sun[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✓[/]',
        '∅',
      ],
      [
        '[bold cyan]84[/]',
        '[bold yellow]2025-08-04·Mon[/]',
        '[bold]∅[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]✗[/]',
        '[bold]2025-08-04·Mon ✓[/]',
      ],
    ],
  ),
]

# DART-specific stops (4 stations only)
DART_STOPS_TABLE: util.ExpectedPrettyPrint = [
  util.ExpectedTable(
    columns=[
      '[bold cyan]Stop[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Type[/]',
      '[bold cyan]Location °[/]',
      '[bold cyan]Location[/]',
      '[bold cyan]Zone[/]',
      '[bold cyan]Desc.[/]',
      '[bold cyan]URL[/]',
    ],
    rows=[
      [
        '[bold cyan]8350IR0123[/]\n[bold red]  └─ 8350IR0122[/]',
        '[bold]∅[/]',
        '[bold yellow]Bray (Daly)[/]\n[bold red]  └─ Greystones[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°12′13.36″N[/]\n[bold yellow]6°6′0.70″W[/]',  # noqa: RUF001
        '[bold]53.2037120[/]\n[bold]-6.1001940[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8350IR0122[/]',
        '[bold]∅[/]',
        '[bold yellow]Greystones[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°8′38.49″N[/]\n[bold yellow]6°3′40.06″W[/]',  # noqa: RUF001
        '[bold]53.1440260[/]\n[bold]-6.0611280[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8250IR0021[/]',
        '[bold]∅[/]',
        '[bold yellow]Killiney[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°15′20.56″N[/]\n[bold yellow]6°6′47.40″W[/]',  # noqa: RUF001
        '[bold]53.2557100[/]\n[bold]-6.1131670[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8250IR0022[/]',
        '[bold]∅[/]',
        '[bold yellow]Shankill[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°14′11.48″N[/]\n[bold yellow]6°7′2.02″W[/]',  # noqa: RUF001
        '[bold]53.2365220[/]\n[bold]-6.1172280[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
]

BASICS_TABLE: util.ExpectedPrettyPrint = [
  '[magenta]Agency [bold]Iarnród Éireann / Irish Rail (7778017)[/]',
  '  https://www.irishrail.ie/en-ie/ (Europe/London)',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]Route[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Long Name[/]',
      '[bold cyan]Type[/]',
      '[bold cyan]Desc.[/]',
      '[bold cyan]URL[/]',
      '[bold cyan]Color[/]',
      '[bold cyan]Text[/]',
      '[bold cyan]# Trips[/]',
    ],
    rows=[
      [
        '[bold cyan]4452_86269[/]',
        '[bold yellow]rail[/]',
        '[bold yellow]Limerick - Galway[/]',
        '[bold]RAIL[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]2[/]',
      ],
      [
        '[bold cyan]4452_86289[/]',
        '[bold yellow]DART[/]',
        '[bold yellow]Bray - Howth[/]',
        '[bold]RAIL[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]6[/]',
      ],
    ],
  ),
  '',
  '[bold magenta]Files @ 2025/Jun/20-19:14:01-UTC[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]Agency[/]',
      '[bold cyan]URLs / Data[/]',
    ],
    rows=[
      [
        "[bold cyan]Allen's Bus Hire[/]",
        '[bold]https://www.transportforireland.ie/transitData/Data/GTFS_All.zip[/]',
      ],
      [
        "[bold cyan]Allen's Bus Hire[/]",
        '[bold]https://www.transportforireland.ie/transitData/Data/GTFS_Small_Operators.zip[/]',
      ],
      [
        '[bold cyan]Iarnród Éireann / Irish Rail[/]',
        '[bold]https://www.transportforireland.ie/transitData/Data/GTFS_All.zip[/]',
      ],
      [
        '[bold cyan]Iarnród Éireann / Irish Rail[/]',
        '[bold]https://www.transportforireland.ie/transitData/Data/GTFS_Irish_Rail.zip[/]',
      ],
      [
        '',
        (
          'Version: [bold yellow]826FB35E-D58B-4FAB-92EC-C5D5CB697E68[/]\n'
          'Last load: [bold yellow]2025/Jun/20-19:14:01-UTC[/]\n'
          'Publisher: [bold]National Transport Authority[/]\n'
          'URL: [bold]https://www.nationaltransport.ie/[/]\n'
          'Language: [bold]en[/]\n'
          'Days range: [bold yellow]2025-05-30·Fri - 2026-05-30·Sat[/]\n'
          'Mail: [bold]∅[/]'
        ),
      ],
      [
        '[bold cyan]Iarnród Éireann / Irish Rail[/]',
        '[bold]https://www.transportforireland.ie/transitData/Data/GTFS_Realtime.zip[/]',
      ],
      [
        '[bold cyan]Wexford Bus[/]',
        '[bold]https://www.transportforireland.ie/transitData/Data/GTFS_All.zip[/]',
      ],
      [
        '[bold cyan]Wexford Bus[/]',
        '[bold]https://www.transportforireland.ie/transitData/Data/GTFS_Wexford_Bus.zip[/]',
      ],
    ],
  ),
]

STOPS_TABLE: util.ExpectedPrettyPrint = [
  util.ExpectedTable(
    columns=[
      '[bold cyan]Stop[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Type[/]',
      '[bold cyan]Location °[/]',
      '[bold cyan]Location[/]',
      '[bold cyan]Zone[/]',
      '[bold cyan]Desc.[/]',
      '[bold cyan]URL[/]',
    ],
    rows=[
      [
        '[bold cyan]8470IR0042[/]',
        '[bold]∅[/]',
        '[bold yellow]Ardrahan[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°9′25.36″N[/]\n[bold yellow]8°48′53.11″W[/]',  # noqa: RUF001
        '[bold]53.1570440[/]\n[bold]-8.8147520[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8470IR0043[/]',
        '[bold]∅[/]',
        '[bold yellow]Athenry[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°18′5.51″N[/]\n[bold yellow]8°44′54.77″W[/]',  # noqa: RUF001
        '[bold]53.3015300[/]\n[bold]-8.7485470[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8350IR0123[/]\n[bold red]  └─ 8350IR0122[/]',
        '[bold]∅[/]',
        '[bold yellow]Bray (Daly)[/]\n[bold red]  └─ Greystones[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°12′13.36″N[/]\n[bold yellow]6°6′0.70″W[/]',  # noqa: RUF001
        '[bold]53.2037120[/]\n[bold]-6.1001940[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8470IR0049[/]',
        '[bold]∅[/]',
        '[bold yellow]Craughwell[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°13′32.94″N[/]\n[bold yellow]8°44′8.74″W[/]',  # noqa: RUF001
        '[bold]53.2258170[/]\n[bold]-8.7357600[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8250IR0014[/]',
        '[bold]∅[/]',
        '[bold yellow]Dalkey[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°16′33.07″N[/]\n[bold yellow]6°6′12.09″W[/]',  # noqa: RUF001
        '[bold]53.2758540[/]\n[bold]-6.1033580[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8360IR0003[/]',
        '[bold]∅[/]',
        '[bold yellow]Ennis[/]',
        '[bold]STOP[/]',
        '[bold yellow]52°50′21.17″N[/]\n[bold yellow]8°58′31.62″W[/]',  # noqa: RUF001
        '[bold]52.8392150[/]\n[bold]-8.9754500[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8460IR0044[/]',
        '[bold]∅[/]',
        '[bold yellow]Galway (Ceannt)[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°16′25.56″N[/]\n[bold yellow]9°2′49.47″W[/]',  # noqa: RUF001
        '[bold]53.2737660[/]\n[bold]-9.0470750[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8350IR0122[/]',
        '[bold]∅[/]',
        '[bold yellow]Greystones[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°8′38.49″N[/]\n[bold yellow]6°3′40.06″W[/]',  # noqa: RUF001
        '[bold]53.1440260[/]\n[bold]-6.0611280[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8250IR0021[/]',
        '[bold]∅[/]',
        '[bold yellow]Killiney[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°15′20.56″N[/]\n[bold yellow]6°6′47.40″W[/]',  # noqa: RUF001
        '[bold]53.2557100[/]\n[bold]-6.1131670[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8400IR0127[/]',
        '[bold]∅[/]',
        '[bold yellow]Limerick (Colbert)[/]',
        '[bold]STOP[/]',
        '[bold yellow]52°39′32.07″N[/]\n[bold yellow]8°37′29.33″W[/]',  # noqa: RUF001
        '[bold]52.6589090[/]\n[bold]-8.6248130[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8470IR050[/]',
        '[bold]∅[/]',
        '[bold yellow]Oranmore[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°16′32.09″N[/]\n[bold yellow]8°56′48.49″W[/]',  # noqa: RUF001
        '[bold]53.2755800[/]\n[bold]-8.9468040[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8250IR0022[/]',
        '[bold]∅[/]',
        '[bold yellow]Shankill[/]',
        '[bold]STOP[/]',
        '[bold yellow]53°14′11.48″N[/]\n[bold yellow]6°7′2.02″W[/]',  # noqa: RUF001
        '[bold]53.2365220[/]\n[bold]-6.1172280[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]8360IR0010[/]',
        '[bold]∅[/]',
        '[bold yellow]Sixmilebridge[/]',
        '[bold]STOP[/]',
        '[bold yellow]52°44′17.02″N[/]\n[bold yellow]8°47′6.95″W[/]',  # noqa: RUF001
        '[bold]52.7380610[/]\n[bold]-8.7852650[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
]

SHAPE_4669_658_TABLE: util.ExpectedPrettyPrint = [
  '[magenta]GTFS Shape ID [bold]4669_658[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Distance[/]',
      '[bold cyan]Latitude °[/]',
      '[bold cyan]Longitude °[/]',
      '[bold cyan]Latitude[/]',
      '[bold cyan]Longitude[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]0.00[/]',
        '[bold yellow]53°16′25.00″N[/]',  # noqa: RUF001
        '[bold yellow]9°2′49.99″W[/]',  # noqa: RUF001
        '[bold]53.2736105[/]',
        '[bold]-9.0472196[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]5.83[/]',
        '[bold yellow]53°16′24.90″N[/]',  # noqa: RUF001
        '[bold yellow]9°2′49.72″W[/]',  # noqa: RUF001
        '[bold]53.2735839[/]',
        '[bold]-9.0471444[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]80.34[/]',
        '[bold yellow]53°16′23.73″N[/]',  # noqa: RUF001
        '[bold yellow]9°2′46.21″W[/]',  # noqa: RUF001
        '[bold]53.2732581[/]',
        '[bold]-9.0461686[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold]122.62[/]',
        '[bold yellow]53°16′23.03″N[/]',  # noqa: RUF001
        '[bold yellow]9°2′44.24″W[/]',  # noqa: RUF001
        '[bold]53.2730648[/]',
        '[bold]-9.0456231[/]',
      ],
      [
        '[bold cyan]5[/]',
        '[bold]187.12[/]',
        '[bold yellow]53°16′21.96″N[/]',  # noqa: RUF001
        '[bold yellow]9°2′41.26″W[/]',  # noqa: RUF001
        '[bold]53.2727663[/]',
        '[bold]-9.0447944[/]',
      ],
    ],
  ),
]

TRIP_4452_2655_TABLE: util.ExpectedPrettyPrint = [
  '[magenta]GTFS Trip ID [bold]4452_2655[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86289[/]',
  '  Short name:  [bold yellow]DART[/]',
  '  Long name:   [bold yellow]Bray - Howth[/]',
  '  Description: [bold]∅[/]',
  'Direction:     [bold yellow]outbound[/]',
  'Service:       [bold yellow]83[/]',
  'Shape:         [bold]4452_42[/]',
  'Headsign:      [bold]Malahide[/]',
  'Name:          [bold]E818[/]',
  'Block:         [bold]4452_7778018_Txc47315F93-ACBE-4CE8-9F30-920A2B0C3C75[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop ID[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Description[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]8350IR0122[/]',
        '[bold yellow]Greystones[/]',
        '[bold]19:18:00[/]',
        '[bold]19:18:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]8350IR0123[/]',
        '[bold yellow]Bray (Daly)[/]',
        '[bold]19:28:00[/]',
        '[bold]19:31:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]8250IR0022[/]',
        '[bold yellow]Shankill[/]',
        '[bold]19:35:00[/]',
        '[bold]19:36:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold]8250IR0021[/]',
        '[bold yellow]Killiney[/]',
        '[bold]19:38:00[/]',
        '[bold]19:38:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
]

ALL_TRIPS_TABLE: util.ExpectedPrettyPrint = [
  '██ ✿ BASIC DATA ✿ █████████████████████████████████████████████████████████████████',
  '',
  *BASICS_TABLE,
  '',
  '██ ✿ CALENDAR ✿ ███████████████████████████████████████████████████████████████████',
  '',
  *CALENDARS_TABLE,
  '',
  '██ ✿ STOPS ✿ ██████████████████████████████████████████████████████████████████████',
  '',
  *STOPS_TABLE,
  '',
  '██ ✿ SHAPES ✿ █████████████████████████████████████████████████████████████████████',
  '',
  '[magenta]GTFS Shape ID [bold]4452_42[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Distance[/]',
      '[bold cyan]Latitude °[/]',
      '[bold cyan]Longitude °[/]',
      '[bold cyan]Latitude[/]',
      '[bold cyan]Longitude[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]0.00[/]',
        '[bold yellow]53°8′38.76″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′39.19″W[/]',  # noqa: RUF001
        '[bold]53.1441008[/]',
        '[bold]-6.0608849[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]5.50[/]',
        '[bold yellow]53°8′38.94″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′39.23″W[/]',  # noqa: RUF001
        '[bold]53.1441497[/]',
        '[bold]-6.0608973[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]31.16[/]',
        '[bold yellow]53°8′39.67″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′39.90″W[/]',  # noqa: RUF001
        '[bold]53.1443514[/]',
        '[bold]-6.0610831[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold]65.45[/]',
        '[bold yellow]53°8′40.63″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′40.81″W[/]',  # noqa: RUF001
        '[bold]53.1446195[/]',
        '[bold]-6.0613355[/]',
      ],
      [
        '[bold cyan]5[/]',
        '[bold]89.90[/]',
        '[bold yellow]53°8′41.31″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′41.48″W[/]',  # noqa: RUF001
        '[bold]53.1448083[/]',
        '[bold]-6.0615225[/]',
      ],
      [
        '[bold cyan]6[/]',
        '[bold]119.86[/]',
        '[bold yellow]53°8′42.11″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′42.39″W[/]',  # noqa: RUF001
        '[bold]53.1450306[/]',
        '[bold]-6.0617750[/]',
      ],
      [
        '[bold cyan]7[/]',
        '[bold]141.33[/]',
        '[bold yellow]53°8′42.69″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′43.03″W[/]',  # noqa: RUF001
        '[bold]53.1451908[/]',
        '[bold]-6.0619537[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  '[magenta]GTFS Shape ID [bold]4669_657[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Distance[/]',
      '[bold cyan]Latitude °[/]',
      '[bold cyan]Longitude °[/]',
      '[bold cyan]Latitude[/]',
      '[bold cyan]Longitude[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]0.00[/]',
        '[bold yellow]52°50′21.37″N[/]',  # noqa: RUF001
        '[bold yellow]8°58′30.65″W[/]',  # noqa: RUF001
        '[bold]52.8392692[/]',
        '[bold]-8.9751817[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]4.04[/]',
        '[bold yellow]52°50′21.25″N[/]',  # noqa: RUF001
        '[bold yellow]8°58′30.59″W[/]',  # noqa: RUF001
        '[bold]52.8392348[/]',
        '[bold]-8.9751626[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]155.11[/]',
        '[bold yellow]52°50′16.61″N[/]',  # noqa: RUF001
        '[bold yellow]8°58′28.03″W[/]',  # noqa: RUF001
        '[bold]52.8379474[/]',
        '[bold]-8.9744517[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold]206.46[/]',
        '[bold yellow]52°50′15.00″N[/]',  # noqa: RUF001
        '[bold yellow]8°58′27.35″W[/]',  # noqa: RUF001
        '[bold]52.8375000[/]',
        '[bold]-8.9742651[/]',
      ],
      [
        '[bold cyan]5[/]',
        '[bold]242.70[/]',
        '[bold yellow]52°50′13.89″N[/]',  # noqa: RUF001
        '[bold yellow]8°58′26.75″W[/]',  # noqa: RUF001
        '[bold]52.8371903[/]',
        '[bold]-8.9740986[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  *SHAPE_4669_658_TABLE,
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  '[magenta]GTFS Shape ID [bold]4669_68[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Distance[/]',
      '[bold cyan]Latitude °[/]',
      '[bold cyan]Longitude °[/]',
      '[bold cyan]Latitude[/]',
      '[bold cyan]Longitude[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]0.00[/]',
        '[bold yellow]53°8′38.76″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′39.19″W[/]',  # noqa: RUF001
        '[bold]53.1441008[/]',
        '[bold]-6.0608849[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]5.50[/]',
        '[bold yellow]53°8′38.94″N[/]',  # noqa: RUF001
        '[bold yellow]6°3′39.23″W[/]',  # noqa: RUF001
        '[bold]53.1441497[/]',
        '[bold]-6.0608973[/]',
      ],
    ],
  ),
  '',
  '██ ✿ TRIPS ✿ ██████████████████████████████████████████████████████████████████████',
  '',
  '[magenta]GTFS Trip ID [bold]4669_10287[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86269[/]',
  '  Short name:  [bold yellow]rail[/]',
  '  Long name:   [bold yellow]Limerick - Galway[/]',
  '  Description: [bold]∅[/]',
  'Direction:     [bold yellow]inbound[/]',
  'Service:       [bold yellow]87[/]',
  'Shape:         [bold]4669_658[/]',
  'Headsign:      [bold]Limerick (Colbert)[/]',
  'Name:          [bold]A481[/]',
  'Block:         [bold]4669_7778018_TxcF5814085-2EF0-4E72-998E-4B282D5CC9AC[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop ID[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Description[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]8460IR0044[/]',
        '[bold yellow]Galway (Ceannt)[/]',
        '[bold]06:15:00[/]',
        '[bold]06:15:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]8470IR050[/]',
        '[bold yellow]Oranmore[/]',
        '[bold]06:22:00[/]',
        '[bold]06:22:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]8470IR0043[/]',
        '[bold yellow]Athenry[/]',
        '[bold]06:33:00[/]',
        '[bold]06:37:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold]8470IR0049[/]',
        '[bold yellow]Craughwell[/]',
        '[bold]06:46:00[/]',
        '[bold]06:47:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]5[/]',
        '[bold]8470IR0042[/]',
        '[bold yellow]Ardrahan[/]',
        '[bold]06:55:00[/]',
        '[bold]06:56:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  '[magenta]GTFS Trip ID [bold]4669_10288[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86269[/]',
  '  Short name:  [bold yellow]rail[/]',
  '  Long name:   [bold yellow]Limerick - Galway[/]',
  '  Description: [bold]∅[/]',
  'Direction:     [bold yellow]inbound[/]',
  'Service:       [bold yellow]87[/]',
  'Shape:         [bold]4669_657[/]',
  'Headsign:      [bold]Limerick (Colbert)[/]',
  'Name:          [bold]A471[/]',
  'Block:         [bold]4669_7778018_Txc107C7D84-5B07-4FDE-8875-8E9673265809[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop ID[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Description[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]8360IR0003[/]',
        '[bold yellow]Ennis[/]',
        '[bold]06:50:00[/]',
        '[bold]06:50:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]8360IR0010[/]',
        '[bold yellow]Sixmilebridge[/]',
        '[bold]07:06:00[/]',
        '[bold]07:06:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]8400IR0127[/]',
        '[bold yellow]Limerick (Colbert)[/]',
        '[bold]07:30:00[/]',
        '[bold]07:30:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  *TRIP_4452_2655_TABLE,
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  '[magenta]GTFS Trip ID [bold]4452_2662[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86289[/]',
  '  Short name:  [bold yellow]DART[/]',
  '  Long name:   [bold yellow]Bray - Howth[/]',
  '  Description: [bold]∅[/]',
  'Direction:     [bold yellow]outbound[/]',
  'Service:       [bold yellow]84[/]',
  'Shape:         [bold]4452_42[/]',
  'Headsign:      [bold]Malahide[/]',
  'Name:          [bold]E818[/]',
  'Block:         [bold]4452_7778018_TxcB8ED8C45-6923-4D5B-8601-5F8CC37418F3[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop ID[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Description[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]8350IR0122[/]',
        '[bold yellow]Greystones[/]',
        '[bold]19:18:00[/]',
        '[bold]19:18:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]8350IR0123[/]',
        '[bold yellow]Bray (Daly)[/]',
        '[bold]19:28:00[/]',
        '[bold]19:31:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]8250IR0022[/]',
        '[bold yellow]Shankill[/]',
        '[bold]19:35:00[/]',
        '[bold]19:36:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold]8250IR0021[/]',
        '[bold yellow]Killiney[/]',
        '[bold]19:38:00[/]',
        '[bold]19:38:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  '[magenta]GTFS Trip ID [bold]4452_2666[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86289[/]',
  '  Short name:  [bold yellow]DART[/]',
  '  Long name:   [bold yellow]Bray - Howth[/]',
  '  Description: [bold]∅[/]',
  'Direction:     [bold yellow]outbound[/]',
  'Service:       [bold yellow]83[/]',
  'Shape:         [bold]4452_42[/]',
  'Headsign:      [bold]Malahide[/]',
  'Name:          [bold]E666[/]',
  'Block:         [bold]4452_776668_TxcB8ED8C45-6923-4D5B-8601-5F8CC37418F3[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop ID[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Description[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]8350IR0122[/]',
        '[bold yellow]Greystones[/]',
        '[bold]21:18:00[/]',
        '[bold]21:18:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]8350IR0123[/]',
        '[bold yellow]Bray (Daly)[/]',
        '[bold]21:28:00[/]',
        '[bold]21:31:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]8250IR0022[/]',
        '[bold yellow]Shankill[/]',
        '[bold]21:35:00[/]',
        '[bold]21:36:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold]8250IR0021[/]',
        '[bold yellow]Killiney[/]',
        '[bold]21:38:00[/]',
        '[bold]21:38:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  '[magenta]GTFS Trip ID [bold]4669_4666[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86289[/]',
  '  Short name:  [bold yellow]DART[/]',
  '  Long name:   [bold yellow]Bray - Howth[/]',
  '  Description: [bold]∅[/]',
  'Direction:     [bold yellow]inbound[/]',
  'Service:       [bold yellow]84[/]',
  'Shape:         [bold]4669_68[/]',
  'Headsign:      [bold]Malahide[/]',
  'Name:          [bold]E666[/]',
  'Block:         [bold]4669_7778018_Txc829999E-01F8-40DB-BD1B-EBC38AE79EB1[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop ID[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Description[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]8250IR0022[/]',
        '[bold yellow]Shankill[/]',
        '[bold]21:35:00[/]',
        '[bold]21:36:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]8250IR0021[/]',
        '[bold yellow]Killiney[/]',
        '[bold]21:38:00[/]',
        '[bold]21:38:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  '[magenta]GTFS Trip ID [bold]4669_4802[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86289[/]',
  '  Short name:  [bold yellow]DART[/]',
  '  Long name:   [bold yellow]Bray - Howth[/]',
  '  Description: [bold]∅[/]',
  'Direction:     [bold yellow]outbound[/]',
  'Service:       [bold yellow]84[/]',
  'Shape:         [bold]4669_68[/]',
  'Headsign:      [bold]Malahide[/]',
  'Name:          [bold]E818[/]',
  'Block:         [bold]4669_7778018_Txc8293CD9E-01F8-40DB-BD1B-EBC38AE79EB1[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop ID[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Description[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]8350IR0122[/]',
        '[bold yellow]Greystones[/]',
        '[bold]19:18:00[/]',
        '[bold]19:18:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]8350IR0123[/]',
        '[bold yellow]Bray (Daly)[/]',
        '[bold]19:28:00[/]',
        '[bold]19:31:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold]8250IR0022[/]',
        '[bold yellow]Shankill[/]',
        '[bold]19:35:00[/]',
        '[bold]19:36:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold]8250IR0021[/]',
        '[bold yellow]Killiney[/]',
        '[bold]19:40:00[/]',
        '[bold]19:40:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  '[magenta]GTFS Trip ID [bold]4669_4999[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86289[/]',
  '  Short name:  [bold yellow]DART[/]',
  '  Long name:   [bold yellow]Bray - Howth[/]',
  '  Description: [bold]∅[/]',
  'Direction:     [bold yellow]outbound[/]',
  'Service:       [bold yellow]83[/]',
  'Shape:         [bold]4669_657[/]',
  'Headsign:      [bold]Malahide[/]',
  'Name:          [bold]E666[/]',
  'Block:         [bold]4669_7778018_Txc829999E-01F8-6666-BD1B-EBC38AE79EB1[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop ID[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Description[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold]8350IR0122[/]',
        '[bold yellow]Greystones[/]',
        '[bold]21:18:00[/]',
        '[bold]21:18:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold]8350IR0123[/]',
        '[bold yellow]Bray (Daly)[/]',
        '[bold]21:28:00[/]',
        '[bold]21:31:00[/]',
        '[bold]0[/]',
        '[bold]∅[/]',
      ],
    ],
  ),
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
]


####################################################################################################
# DART
####################################################################################################


STOPS_1: tuple[dm.TrackStop, ...] = (
  dm.TrackStop(
    stop='8350IR0122',
    name='Greystones',
    headsign='Malahide',
    dropoff=dm.StopPointType.NOT_AVAILABLE,
  ),
  dm.TrackStop(stop='8350IR0123', name='Bray (Daly)'),
  dm.TrackStop(stop='8250IR0022', name='Shankill'),
  dm.TrackStop(stop='8250IR0021', name='Killiney'),
)
TIMES_1: tuple[dm.ScheduleStop, ...] = (
  dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=69480), departure=base.DayTime(time=69480))
  ),
  dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=70080), departure=base.DayTime(time=70260))
  ),
  dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=70500), departure=base.DayTime(time=70560))
  ),
  dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=70680), departure=base.DayTime(time=70680))
  ),
)
TIMES_2: tuple[dm.ScheduleStop, ...] = (
  TIMES_1[0],
  TIMES_1[1],
  TIMES_1[2],
  dm.ScheduleStop(
    times=base.DayRange(arrival=base.DayTime(time=70800), departure=base.DayTime(time=70800))
  ),
)

DART_TRIPS_ZIP_1: collections.OrderedDict[str, list[tuple[int, dm.Schedule, dm.Trip]]] = (
  collections.OrderedDict(
    {
      'E666': [
        (
          83,
          dm.Schedule(
            direction=False,
            stops=(
              dm.TrackStop(
                stop='8350IR0122',
                name='Greystones',
                headsign='Malahide',
                pickup=dm.StopPointType.REGULAR,
                dropoff=dm.StopPointType.NOT_AVAILABLE,
              ),
              dm.TrackStop(
                stop='8350IR0123',
                name='Bray (Daly)',
              ),
            ),
            times=(
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=76680),
                  departure=base.DayTime(time=76680),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=77280),
                  departure=base.DayTime(time=77460),
                ),
              ),
            ),
          ),
          ZIP_DB_1.agencies[7778017].routes['4452_86289'].trips['4669_4999'],
        ),
        (
          83,
          dm.Schedule(
            direction=False,
            stops=(
              dm.TrackStop(
                stop='8350IR0122',
                name='Greystones',
                headsign='Malahide',
                pickup=dm.StopPointType.REGULAR,
                dropoff=dm.StopPointType.NOT_AVAILABLE,
              ),
              dm.TrackStop(
                stop='8350IR0123',
                name='Bray (Daly)',
              ),
              dm.TrackStop(
                stop='8250IR0022',
                name='Shankill',
              ),
              dm.TrackStop(
                stop='8250IR0021',
                name='Killiney',
              ),
            ),
            times=(
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=76680),
                  departure=base.DayTime(time=76680),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=77280),
                  departure=base.DayTime(time=77460),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=77700),
                  departure=base.DayTime(time=77760),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=77880),
                  departure=base.DayTime(time=77880),
                ),
              ),
            ),
          ),
          ZIP_DB_1.agencies[7778017].routes['4452_86289'].trips['4452_2666'],
        ),
        (
          84,
          dm.Schedule(
            direction=True,
            stops=(
              dm.TrackStop(
                stop='8250IR0022',
                name='Shankill',
              ),
              dm.TrackStop(
                stop='8250IR0021',
                name='Killiney',
              ),
            ),
            times=(
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=77700),
                  departure=base.DayTime(time=77760),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=77880),
                  departure=base.DayTime(time=77880),
                ),
              ),
            ),
          ),
          ZIP_DB_1.agencies[7778017].routes['4452_86289'].trips['4669_4666'],
        ),
      ],
      'E818': [
        (
          83,
          dm.Schedule(
            direction=False,
            stops=(
              dm.TrackStop(
                stop='8350IR0122',
                name='Greystones',
                headsign='Malahide',
                pickup=dm.StopPointType.REGULAR,
                dropoff=dm.StopPointType.NOT_AVAILABLE,
              ),
              dm.TrackStop(
                stop='8350IR0123',
                name='Bray (Daly)',
              ),
              dm.TrackStop(
                stop='8250IR0022',
                name='Shankill',
              ),
              dm.TrackStop(
                stop='8250IR0021',
                name='Killiney',
              ),
            ),
            times=(
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=69480),
                  departure=base.DayTime(time=69480),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70080),
                  departure=base.DayTime(time=70260),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70500),
                  departure=base.DayTime(time=70560),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70680),
                  departure=base.DayTime(time=70680),
                ),
              ),
            ),
          ),
          ZIP_DB_1.agencies[7778017].routes['4452_86289'].trips['4452_2655'],
        ),
        (
          84,
          dm.Schedule(
            direction=False,
            stops=(
              dm.TrackStop(
                stop='8350IR0122',
                name='Greystones',
                headsign='Malahide',
                pickup=dm.StopPointType.REGULAR,
                dropoff=dm.StopPointType.NOT_AVAILABLE,
              ),
              dm.TrackStop(
                stop='8350IR0123',
                name='Bray (Daly)',
              ),
              dm.TrackStop(
                stop='8250IR0022',
                name='Shankill',
              ),
              dm.TrackStop(
                stop='8250IR0021',
                name='Killiney',
              ),
            ),
            times=(
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=69480),
                  departure=base.DayTime(time=69480),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70080),
                  departure=base.DayTime(time=70260),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70500),
                  departure=base.DayTime(time=70560),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70680),
                  departure=base.DayTime(time=70680),
                ),
              ),
            ),
          ),
          ZIP_DB_1.agencies[7778017].routes['4452_86289'].trips['4452_2662'],
        ),
        (
          84,
          dm.Schedule(
            direction=False,
            stops=(
              dm.TrackStop(
                stop='8350IR0122',
                name='Greystones',
                headsign='Malahide',
                pickup=dm.StopPointType.REGULAR,
                dropoff=dm.StopPointType.NOT_AVAILABLE,
              ),
              dm.TrackStop(
                stop='8350IR0123',
                name='Bray (Daly)',
              ),
              dm.TrackStop(
                stop='8250IR0022',
                name='Shankill',
              ),
              dm.TrackStop(
                stop='8250IR0021',
                name='Killiney',
              ),
            ),
            times=(
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=69480),
                  departure=base.DayTime(time=69480),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70080),
                  departure=base.DayTime(time=70260),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70500),
                  departure=base.DayTime(time=70560),
                ),
              ),
              dm.ScheduleStop(
                times=base.DayRange(
                  arrival=base.DayTime(time=70800),
                  departure=base.DayTime(time=70800),
                ),
              ),
            ),
          ),
          ZIP_DB_1.agencies[7778017].routes['4452_86289'].trips['4669_4802'],
        ),
      ],
    }
  )
)

TRIPS_SCHEDULE_2025_08_04: util.ExpectedPrettyPrint = [
  '[bold magenta]DART Schedule[/]',
  '',
  'Day:      [bold yellow]2025-08-04[/] [bold](Monday)[/]',
  'Services: [bold yellow]84[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]N/S[/]',
      '[bold cyan]Train[/]',
      '[bold cyan]Start[/]',
      '[bold cyan]End[/]',
      '[bold cyan]Depart Time[/]',
      '[bold cyan]Service/Trip Codes/[/][red][★Alt.Times][/]',
    ],
    rows=[
      [
        '[bold][bright_red]N[/][/]',
        '[bold yellow]E818[/]',
        '[bold]Greystones[/]',
        '[bold]Killiney[/]',
        '[bold yellow]19:18:00[/]',
        '[bold]84/4452_2662, 84/4669_4802/[red]★[/][/]',
      ],
      [
        '[bold][bright_blue]S[/][/]',
        '[bold yellow]E666[/]',
        '[bold]Shankill[/]',
        '[bold]Killiney[/]',
        '[bold yellow]21:36:00[/]',
        '[bold]84/4669_4666[/]',
      ],
    ],
  ),
]

STATION_SCHEDULE_2025_08_04: util.ExpectedPrettyPrint = [
  '[magenta]DART Schedule for Station [bold]Bray (Daly) - 8350IR0123[/]',
  '',
  'Day:          [bold yellow]2025-08-04[/] [bold](Monday)[/]',
  'Services:     [bold yellow]84[/]',
  'Destinations: [bold yellow]Killiney[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]N/S[/]',
      '[bold cyan]Train[/]',
      '[bold cyan]Destination[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Departure[/]',
      '[bold cyan]Service/Trip Codes/[/][red][★Alt.Times][/]',
    ],
    rows=[
      [
        '[bold][bright_red]N[/][/]',
        '[bold yellow]E818[/]',
        '[bold yellow]Killiney[/]',
        '[bold]19:28:00[/]',
        '[bold yellow]19:31:00[/]',
        '[bold]84/4452_2662, 84/4669_4802/[red][★][/][bold][/]',
      ],
    ],
  ),
]

TRIP_E666: util.ExpectedPrettyPrint = [
  '[magenta]DART Trip [bold]E666[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86289[/]',
  '  Short name:  [bold yellow]DART[/]',
  '  Long name:   [bold yellow]Bray - Howth[/]',
  '  Description: [bold]∅[/]',
  'Headsign:      [bold]Malahide[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]Trip ID[/]',
      '[bold magenta]4669_4999[/]',
      '[bold magenta]4452_2666[/]',
      '[bold magenta]4669_4666[/]',
    ],
    rows=[
      ['Service', '[bold yellow]83[/]', '[bold yellow]83[/]', '[bold yellow]84[/]'],
      [
        'N/S',
        '[bold][bright_red]N[/][/]',
        '[bold][bright_red]N[/][/]',
        '[bold][bright_blue]S[/][/]',
      ],
      ['Shape', '[bold]4669_657[/]', '[bold]4452_42[/]', '[bold]4669_68[/]'],
      ['Block', '[bold]4669_7778…[/]', '[bold]4452_7766…[/]', '[bold]4669_7778…[/]'],
      [
        '#',
        '[bold cyan]Stop[/]\n[bold cyan]Dropoff[/]\n[bold cyan]Pickup[/]',
        '[bold cyan]Stop[/]\n[bold cyan]Dropoff[/]\n[bold cyan]Pickup[/]',
        '[bold cyan]Stop[/]\n[bold cyan]Dropoff[/]\n[bold cyan]Pickup[/]',
      ],
      [
        '[bold cyan]1[/]',
        '[bold yellow]Greystones[/]\n[bold]21:18:00[red]✗[/][/]\n[bold]21:18:00[green]✓[/][/]',
        '[bold yellow]Greystones[/]\n[bold]21:18:00[red]✗[/][/]\n[bold]21:18:00[green]✓[/][/]',
        '\n[bold red]✗[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold yellow]Bray (Dal…[/]\n[bold]21:28:00[green]✓[/][/]\n[bold]21:31:00[green]✓[/][/]',
        '[bold yellow]Bray (Dal…[/]\n[bold]21:28:00[green]✓[/][/]\n[bold]21:31:00[green]✓[/][/]',
        '\n[bold red]✗[/]',
      ],
      [
        '[bold cyan]3[/]',
        '\n[bold red]✗[/]',
        '[bold yellow]Shankill[/]\n[bold]21:35:00[green]✓[/][/]\n[bold]21:36:00[green]✓[/][/]',
        '[bold yellow]Shankill[/]\n[bold]21:35:00[green]✓[/][/]\n[bold]21:36:00[green]✓[/][/]',
      ],
      [
        '[bold cyan]4[/]',
        '\n[bold red]✗[/]',
        '[bold yellow]Killiney[/]\n[bold]21:38:00[green]✓[/][/]\n[bold]21:38:00[green]✓[/][/]',
        '[bold yellow]Killiney[/]\n[bold]21:38:00[green]✓[/][/]\n[bold]21:38:00[green]✓[/][/]',
      ],
    ],
  ),
]

TRIP_E818: util.ExpectedPrettyPrint = [
  '[magenta]DART Trip [bold]E818[/]',
  '',
  'Agency:        [bold yellow]Iarnród Éireann / Irish Rail[/]',
  'Route:         [bold yellow]4452_86289[/]',
  '  Short name:  [bold yellow]DART[/]',
  '  Long name:   [bold yellow]Bray - Howth[/]',
  '  Description: [bold]∅[/]',
  'Headsign:      [bold]Malahide[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]Trip ID[/]',
      '[bold magenta]4452_2655[/]',
      '[bold magenta]4452_2662[/]',
      '[bold magenta]4669_4802[/]',
    ],
    rows=[
      ['Service', '[bold yellow]83[/]', '[bold yellow]84[/]', '[bold yellow]84[/]'],
      [
        'N/S',
        '[bold][bright_red]N[/][/]',
        '[bold][bright_red]N[/][/]',
        '[bold][bright_red]N[/][/]',
      ],
      ['Shape', '[bold]4452_42[/]', '[bold]4452_42[/]', '[bold]4669_68[/]'],
      ['Block', '[bold]4452_7778…[/]', '[bold]4452_7778…[/]', '[bold]4669_7778…[/]'],
      [
        '#',
        '[bold cyan]Stop[/]\n[bold cyan]Dropoff[/]\n[bold cyan]Pickup[/]',
        '[bold cyan]Stop[/]\n[bold cyan]Dropoff[/]\n[bold cyan]Pickup[/]',
        '[bold cyan]Stop[/]\n[bold cyan]Dropoff[/]\n[bold cyan]Pickup[/]',
      ],
      [
        '[bold cyan]1[/]',
        '[bold yellow]Greystones[/]\n[bold]19:18:00[red]✗[/][/]\n[bold]19:18:00[green]✓[/][/]',
        '[bold yellow]Greystones[/]\n[bold]19:18:00[red]✗[/][/]\n[bold]19:18:00[green]✓[/][/]',
        '[bold yellow]Greystones[/]\n[bold]19:18:00[red]✗[/][/]\n[bold]19:18:00[green]✓[/][/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold yellow]Bray (Dal…[/]\n[bold]19:28:00[green]✓[/][/]\n[bold]19:31:00[green]✓[/][/]',
        '[bold yellow]Bray (Dal…[/]\n[bold]19:28:00[green]✓[/][/]\n[bold]19:31:00[green]✓[/][/]',
        '[bold yellow]Bray (Dal…[/]\n[bold]19:28:00[green]✓[/][/]\n[bold]19:31:00[green]✓[/][/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold yellow]Shankill[/]\n[bold]19:35:00[green]✓[/][/]\n[bold]19:36:00[green]✓[/][/]',
        '[bold yellow]Shankill[/]\n[bold]19:35:00[green]✓[/][/]\n[bold]19:36:00[green]✓[/][/]',
        '[bold yellow]Shankill[/]\n[bold]19:35:00[green]✓[/][/]\n[bold]19:36:00[green]✓[/][/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold yellow]Killiney[/]\n[bold]19:38:00[green]✓[/][/]\n[bold]19:38:00[green]✓[/][/]',
        '[bold yellow]Killiney[/]\n[bold]19:38:00[green]✓[/][/]\n[bold]19:38:00[green]✓[/][/]',
        '[bold yellow]Killiney[/]\n[bold]19:40:00[green]✓[/][/]\n[bold]19:40:00[green]✓[/][/]',
      ],
    ],
  ),
]

ALL_DATA: util.ExpectedPrettyPrint = [
  '██ ✿ CALENDAR ✿ ███████████████████████████████████████████████████████████████████',
  '',
  *DART_CALENDARS_TABLE,
  '',
  '██ ✿ STOPS ✿ ██████████████████████████████████████████████████████████████████████',
  '',
  *DART_STOPS_TABLE,
  '',
  '██ ✿ TRIPS ✿ ██████████████████████████████████████████████████████████████████████',
  '',
  *TRIP_E666,
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
  *TRIP_E818,
  '',
  '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
  '',
]
