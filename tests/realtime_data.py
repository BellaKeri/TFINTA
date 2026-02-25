# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
"""Realtime unittest data."""

from __future__ import annotations

import datetime

from tfinta import realtime_data_model as dm
from tfinta import tfinta_base as base

from . import util

RT_TIME = 1751184867.863  # datetime.datetime(2025, 6, 29, 9, 14, 27, 863000)

STATIONS_OBJ = dm.LatestData(
  stations={
    'MHIDE': dm.Station(
      id=228,
      code='MHIDE',
      description='Malahide with extra looooooooooooooooooong name',
      location=base.Point(
        latitude=54.6123,
        longitude=-5.91744,
      ),
      alias=None,
    ),
    'CENTJ': dm.Station(
      id=1517,
      code='CENTJ',
      description='CENTRAL JUNCTION',
      location=None,
      alias='Dublin Connolly',
    ),
    'BRAY': dm.Station(
      id=64,
      code='BRAY',
      description='Bray',
      location=base.Point(
        latitude=51.8688,
        longitude=-8.32417,
      ),
      alias=None,
    ),
    'CITYJ': dm.Station(
      id=1516,
      code='CITYJ',
      description='CITY JUNCTION',
      location=None,
      alias='Dublin Belfast',
    ),
    'COBH': dm.Station(
      id=66,
      code='COBH',
      description='Cobh',
      location=base.Point(
        latitude=51.8491,
        longitude=-8.29956,
      ),
      alias=None,
    ),
    'MOIRA': dm.Station(
      id=1519,
      code='MOIRA',
      description='MOIRA',
      location=None,
      alias='Dublin Belfast',
    ),
  },
  running_trains={},
  station_boards={},
  trains={},
  stations_tm=RT_TIME,
  running_tm=None,
)

RUNNING_OBJ = dm.LatestData(
  stations={},
  running_trains={
    'A152': dm.RunningTrain(
      code='A152',
      status=dm.TrainStatus.RUNNING,
      day=datetime.date(2025, 6, 29),
      direction='Northbound',
      message='A152\n'
      '13:50 - Dublin Connolly to Belfast (5 mins late)\n'
      'Arrived Dundalk next stop Newry',
      position=base.Point(
        latitude=54.0007,
        longitude=-6.41291,
      ),
    ),
    'A218': dm.RunningTrain(
      code='A218',
      status=dm.TrainStatus.NOT_YET_RUNNING,
      day=datetime.date(2025, 6, 29),
      direction='To Cork',
      message='A218\nDublin Heuston to Cork\nExpected Departure 15:00',
      position=base.Point(
        latitude=53.3464,
        longitude=-6.29461,
      ),
    ),
    'A407': dm.RunningTrain(
      code='A407',
      status=dm.TrainStatus.RUNNING,
      day=datetime.date(2025, 6, 29),
      direction='To Dublin Heuston',
      message='A407\n'
      '14:20 - Limerick to Dublin Heuston (-1 mins late)\n'
      'Departed LJ461 next stop Thurles',
      position=None,
    ),
    'A908': dm.RunningTrain(
      code='A908',
      status=dm.TrainStatus.NOT_YET_RUNNING,
      day=datetime.date(2025, 6, 29),
      direction='Northbound',
      message='A908\nDublin Connolly to Sligo\nExpected Departure 15:05',
      position=base.Point(
        latitude=53.3531,
        longitude=-6.24591,
      ),
    ),
    'B957': dm.RunningTrain(
      code='B957',
      status=dm.TrainStatus.TERMINATED,
      day=datetime.date(2025, 6, 29),
      direction='Southbound',
      message='B957\n'
      '13:55 - Maynooth to Dublin Connolly(13 mins late)\n'
      'TERMINATED Dublin Connolly at 14:51',
      position=base.Point(
        latitude=53.3531,
        longitude=-6.24591,
      ),
    ),
    'E218': dm.RunningTrain(
      code='E218',
      status=dm.TrainStatus.NOT_YET_RUNNING,
      day=datetime.date(2025, 6, 29),
      direction='Southbound',
      message='E218\nMalahide to Bray\nExpected Departure 15:04',
      position=base.Point(
        latitude=53.4509,
        longitude=-6.15649,
      ),
    ),
    'P375': dm.RunningTrain(
      code='P375',
      status=dm.TrainStatus.TERMINATED,
      day=datetime.date(2025, 6, 29),
      direction='Southbound',
      message='P375\n14:40 - M3 Parkway to Clonsilla(0 mins late)\nTERMINATED Clonsilla at 14:49',
      position=base.Point(
        latitude=53.3831,
        longitude=-6.4242,
      ),
    ),
  },
  station_boards={},
  trains={},
  stations_tm=None,
  running_tm=RT_TIME,
)

_STATION_OBJ_QUERY = dm.StationLineQueryData(
  tm_server=datetime.datetime(2025, 6, 29, 9, 14, 27, 863000, tzinfo=datetime.UTC),
  tm_query=base.DayTime(time=33267),
  station_name='Malahide with extra looooooooooooooooooong name',
  station_code='MHIDE',
  day=datetime.date(2025, 6, 29),
)
STATION_OBJ = dm.LatestData(
  stations=STATIONS_OBJ.stations,
  running_trains={},
  station_boards={
    'MHIDE': (
      1751184867.863,
      _STATION_OBJ_QUERY,
      [
        dm.StationLine(
          query=_STATION_OBJ_QUERY,
          train_code='P702',
          origin_code='BRAY',
          origin_name='Bray',
          destination_code='CENTJ',
          destination_name='Dublin Connolly',
          trip=base.DayRange(
            arrival=base.DayTime(time=31500),
            departure=base.DayTime(time=35100),
          ),
          direction='Southbound',
          due_in=base.DayTime(time=540),
          late=5,
          location_type=dm.LocationType.STOP,
          status='En Route',
          scheduled=base.DayRange(
            arrival=base.DayTime(time=33720),
            departure=base.DayTime(time=33780),
            nullable=True,
          ),
          expected=base.DayRange(
            arrival=base.DayTime(time=33720),
            departure=base.DayTime(time=34020),
            nullable=True,
            strict=False,
          ),
          train_type=dm.TrainType.DMU,
          last_location='Arrived Rush and Lusk',
        ),
        dm.StationLine(
          query=_STATION_OBJ_QUERY,
          train_code='E802',
          origin_code='BRAY',
          origin_name='Bray',
          destination_code='MHIDE',
          destination_name='Malahide',
          trip=base.DayRange(
            arrival=base.DayTime(time=31860),
            departure=base.DayTime(time=36360),
          ),
          direction='Northbound',
          due_in=base.DayTime(time=3120),
          late=1,
          location_type=dm.LocationType.DESTINATION,
          status='En Route',
          scheduled=base.DayRange(
            arrival=base.DayTime(time=36360),
            departure=None,
            nullable=True,
          ),
          expected=base.DayRange(
            arrival=base.DayTime(time=36420),
            departure=None,
            nullable=True,
            strict=False,
          ),
          train_type=dm.TrainType.DART,
          last_location='Arrived Salthill and Monkstown',
        ),
        dm.StationLine(
          query=_STATION_OBJ_QUERY,
          train_code='E205',
          origin_code='MHIDE',
          origin_name='Malahide',
          destination_code='BRAY',
          destination_name='Bray',
          trip=base.DayRange(
            arrival=base.DayTime(time=37440),
            departure=base.DayTime(time=41940),
          ),
          direction='Southbound',
          due_in=base.DayTime(time=4200),
          late=0,
          location_type=dm.LocationType.ORIGIN,
          status='No Information',
          scheduled=base.DayRange(
            arrival=None,
            departure=base.DayTime(time=37440),
            nullable=True,
          ),
          expected=base.DayRange(
            arrival=None,
            departure=base.DayTime(time=37440),
            nullable=True,
            strict=False,
          ),
          train_type=dm.TrainType.DART,
          last_location=None,
        ),
        dm.StationLine(
          query=_STATION_OBJ_QUERY,
          train_code='D802',
          origin_code='CENTJ',
          origin_name='Dublin Connolly',
          trip=base.DayRange(
            arrival=base.DayTime(time=36600),
            departure=base.DayTime(time=40500),
          ),
          destination_code='BRAY',
          destination_name='Bray',
          direction='Northbound',
          due_in=base.DayTime(time=4860),
          late=-1,
          location_type=dm.LocationType.STOP,
          status='No Information',
          scheduled=base.DayRange(
            arrival=base.DayTime(time=38100),
            departure=base.DayTime(time=38280),
            nullable=True,
          ),
          expected=base.DayRange(
            arrival=base.DayTime(time=38100),
            departure=base.DayTime(time=38340),
            nullable=True,
            strict=False,
          ),
          train_type=dm.TrainType.DMU,
          last_location=None,
        ),
      ],
    ),
  },
  trains={},
  stations_tm=RT_TIME,
  running_tm=None,
)

_TRAIN_OBJ_QUERY = dm.TrainStopQueryData(
  train_code='E108',
  day=datetime.date(2025, 6, 29),
  origin_code='MHIDE',
  origin_name='Malahide',
  destination_code='BRAY',
  destination_name='Bray',
)
TRAIN_OBJ = dm.LatestData(
  stations=STATIONS_OBJ.stations,
  running_trains={},
  station_boards={},
  trains={
    'E108': {
      datetime.date(2025, 6, 29): (
        1751184867.863,
        _TRAIN_OBJ_QUERY,
        {
          1: dm.TrainStop(
            query=_TRAIN_OBJ_QUERY,
            auto_arrival=True,
            auto_depart=True,
            location_type=dm.LocationType.ORIGIN,
            stop_type=dm.StopType.UNKNOWN,
            station_order=1,
            station_code='MHIDE',
            station_name='Malahide',
            scheduled=base.DayRange(
              arrival=None,
              departure=base.DayTime(time=34200),
              nullable=True,
            ),
            expected=base.DayRange(
              arrival=None,
              departure=base.DayTime(time=34200),
              nullable=True,
              strict=False,
            ),
            actual=base.DayRange(
              arrival=base.DayTime(time=33564),
              departure=base.DayTime(time=34224),
              nullable=True,
            ),
          ),
          2: dm.TrainStop(
            query=_TRAIN_OBJ_QUERY,
            auto_arrival=True,
            auto_depart=True,
            location_type=dm.LocationType.STOP,
            stop_type=dm.StopType.UNKNOWN,
            station_order=2,
            station_code='COBH',
            station_name='Cobh',
            scheduled=base.DayRange(
              arrival=base.DayTime(time=34410),
              departure=base.DayTime(time=34440),
              nullable=True,
            ),
            expected=base.DayRange(
              arrival=base.DayTime(time=34434),
              departure=base.DayTime(time=34422),
              nullable=True,
              strict=False,
            ),
            actual=base.DayRange(
              arrival=base.DayTime(time=34392),
              departure=base.DayTime(time=34470),
              nullable=True,
            ),
          ),
          3: dm.TrainStop(
            query=_TRAIN_OBJ_QUERY,
            auto_arrival=True,
            auto_depart=True,
            location_type=dm.LocationType.CREW_RELIEF_OR_CURRENT,
            stop_type=dm.StopType.UNKNOWN,
            station_order=3,
            station_code='GRGRD',
            station_name='Clongriffin',
            scheduled=base.DayRange(
              arrival=base.DayTime(time=34560),
              departure=base.DayTime(time=34590),
              nullable=True,
            ),
            expected=base.DayRange(
              arrival=base.DayTime(time=34590),
              departure=base.DayTime(time=34566),
              nullable=True,
              strict=False,
            ),
            actual=base.DayRange(
              arrival=base.DayTime(time=34536),
              departure=base.DayTime(time=34614),
              nullable=True,
            ),
          ),
          4: dm.TrainStop(
            query=_TRAIN_OBJ_QUERY,
            auto_arrival=True,
            auto_depart=True,
            location_type=dm.LocationType.STOP,
            stop_type=dm.StopType.UNKNOWN,
            station_order=4,
            station_code='BRAY',
            station_name='Bray',
            scheduled=base.DayRange(
              arrival=base.DayTime(time=38670),
              departure=base.DayTime(time=38730),
              nullable=True,
            ),
            expected=base.DayRange(
              arrival=base.DayTime(time=38694),
              departure=base.DayTime(time=38646),
              nullable=True,
              strict=False,
            ),
            actual=base.DayRange(
              arrival=base.DayTime(time=38586),
              departure=base.DayTime(time=38706),
              nullable=True,
            ),
          ),
          5: dm.TrainStop(
            query=_TRAIN_OBJ_QUERY,
            auto_arrival=False,
            auto_depart=False,
            location_type=dm.LocationType.TIMING_POINT,
            stop_type=dm.StopType.UNKNOWN,
            station_order=5,
            station_code='CITYJ',
            station_name='CITY JUNCTION',
            scheduled=base.DayRange(
              arrival=base.DayTime(time=38790),
              departure=base.DayTime(time=38790),
              nullable=True,
            ),
            expected=base.DayRange(
              arrival=base.DayTime(time=38766),
              departure=base.DayTime(time=38766),
              nullable=True,
              strict=False,
            ),
            actual=base.DayRange(
              arrival=None,
              departure=None,
              nullable=True,
            ),
          ),
          6: dm.TrainStop(
            query=_TRAIN_OBJ_QUERY,
            auto_arrival=True,
            auto_depart=True,
            location_type=dm.LocationType.TIMING_POINT,
            stop_type=dm.StopType.UNKNOWN,
            station_order=6,
            station_code='MOIRA',
            station_name=None,
            scheduled=base.DayRange(
              arrival=base.DayTime(time=39060),
              departure=base.DayTime(time=39060),
              nullable=True,
            ),
            expected=base.DayRange(
              arrival=base.DayTime(time=39036),
              departure=base.DayTime(time=38994),
              nullable=True,
              strict=False,
            ),
            actual=base.DayRange(
              arrival=base.DayTime(time=38994),
              departure=base.DayTime(time=39018),
              nullable=True,
            ),
          ),
          7: dm.TrainStop(
            query=_TRAIN_OBJ_QUERY,
            auto_arrival=True,
            auto_depart=False,
            location_type=dm.LocationType.DESTINATION,
            stop_type=dm.StopType.CURRENT,
            station_order=7,
            station_code='BRAY',
            station_name='Bray',
            scheduled=base.DayRange(
              arrival=base.DayTime(time=39300),
              departure=None,
              nullable=True,
            ),
            expected=base.DayRange(
              arrival=base.DayTime(time=39258),
              departure=None,
              nullable=True,
              strict=False,
            ),
            actual=base.DayRange(
              arrival=base.DayTime(time=39306),
              departure=None,
              nullable=True,
            ),
          ),
        },
      ),
    },
  },
  stations_tm=RT_TIME,
  running_tm=None,
)

STATIONS_TABLE: util.ExpectedPrettyPrint = [
  '[magenta]Irish Rail Stations @ [bold]2025/Jun/29-08:14:27-UTC[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]ID[/]',
      '[bold cyan]Code[/]',
      '[bold cyan]Name[/]',
      '[bold cyan]Alias[/]',
      '[bold cyan]Location °[/]',
      '[bold cyan]Location[/]',
    ],
    rows=[
      [
        '[bold cyan]64[/]',
        '[bold]BRAY[/]',
        '[bold yellow]Bray[/]',
        '[bold]∅[/]',
        '[bold yellow]51°52′7.68″N[/]\n[bold yellow]8°19′27.01″W[/]',  # noqa: RUF001
        '[bold]51.8688000[/]\n[bold]-8.3241700[/]',
      ],
      [
        '[bold cyan]1517[/]',
        '[bold]CENTJ[/]',
        '[bold yellow]CENTRAL JUNCTION[/]',
        '[bold]Dublin Connolly[/]',
        '[bold yellow]∅[/]\n[bold yellow]∅[/]',
        '[bold]∅[/]\n[bold]∅[/]',
      ],
      [
        '[bold cyan]1516[/]',
        '[bold]CITYJ[/]',
        '[bold yellow]CITY JUNCTION[/]',
        '[bold]Dublin Belfast[/]',
        '[bold yellow]∅[/]\n[bold yellow]∅[/]',
        '[bold]∅[/]\n[bold]∅[/]',
      ],
      [
        '[bold cyan]66[/]',
        '[bold]COBH[/]',
        '[bold yellow]Cobh[/]',
        '[bold]∅[/]',
        '[bold yellow]51°50′56.76″N[/]\n[bold yellow]8°17′58.42″W[/]',  # noqa: RUF001
        '[bold]51.8491000[/]\n[bold]-8.2995600[/]',
      ],
      [
        '[bold cyan]1519[/]',
        '[bold]MOIRA[/]',
        '[bold yellow]MOIRA[/]',
        '[bold]Dublin Belfast[/]',
        '[bold yellow]∅[/]\n[bold yellow]∅[/]',
        '[bold]∅[/]\n[bold]∅[/]',
      ],
      [
        '[bold cyan]228[/]',
        '[bold]MHIDE[/]',
        '[bold yellow]Malahide with extra looooooooooooooooooong name[/]',
        '[bold]∅[/]',
        '[bold yellow]54°36′44.28″N[/]\n[bold yellow]5°55′2.78″W[/]',  # noqa: RUF001
        '[bold]54.6123000[/]\n[bold]-5.9174400[/]',
      ],
    ],
  ),
]

RUNNING_TABLE: util.ExpectedPrettyPrint = [
  '[magenta]Irish Rail Running Trains @ [bold]2025/Jun/29-08:14:27-UTC[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]Train[/]',
      '[bold cyan]Direction[/]',
      '[bold cyan]Location °[/]',
      '[bold cyan]Location[/]',
      '[bold cyan]Message[/]',
    ],
    rows=[
      [
        '[bold cyan]A152[/]\n[bold][green]►[/][/]',
        '[bold]Northbound[/]',
        '[bold yellow]54°0′2.52″N[/]\n[bold yellow]6°24′46.48″W[/]',  # noqa: RUF001
        '[bold]54.0007000[/]\n[bold]-6.4129100[/]',
        (
          '[bold]13:50 - Dublin Connolly to Belfast (5 mins late)[/]\n'
          '[bold]Arrived Dundalk next stop Newry[/]'
        ),
      ],
      [
        '[bold cyan]A407[/]\n[bold][green]►[/][/]',
        '[bold]To Dublin Heus…[/]',
        '[bold]∅[/]\n[bold]∅[/]',
        '[bold]∅[/]\n[bold]∅[/]',
        (
          '[bold]14:20 - Limerick to Dublin Heuston (-1 mins late)[/]\n'
          '[bold]Departed LJ461 next stop Thurles[/]'
        ),
      ],
      [
        '[bold cyan]A218[/]\n[bold][red]■[/][/]',
        '[bold]To Cork[/]',
        '[bold yellow]53°20′47.04″N[/]\n[bold yellow]6°17′40.60″W[/]',  # noqa: RUF001
        '[bold]53.3464000[/]\n[bold]-6.2946100[/]',
        '[bold]Dublin Heuston to Cork[/]\n[bold]Expected Departure 15:00[/]',
      ],
      [
        '[bold cyan]A908[/]\n[bold][red]■[/][/]',
        '[bold]Northbound[/]',
        '[bold yellow]53°21′11.16″N[/]\n[bold yellow]6°14′45.28″W[/]',  # noqa: RUF001
        '[bold]53.3531000[/]\n[bold]-6.2459100[/]',
        '[bold]Dublin Connolly to Sligo[/]\n[bold]Expected Departure 15:05[/]',
      ],
      [
        '[bold cyan]E218[/]\n[bold][red]■[/][/]',
        '[bold]Southbound[/]',
        '[bold yellow]53°27′3.24″N[/]\n[bold yellow]6°9′23.36″W[/]',  # noqa: RUF001
        '[bold]53.4509000[/]\n[bold]-6.1564900[/]',
        '[bold]Malahide to Bray[/]\n[bold]Expected Departure 15:04[/]',
      ],
      [
        '[bold cyan]B957[/]\n[bold][yellow]✗[/][/]',
        '[bold]Southbound[/]',
        '[bold yellow]53°21′11.16″N[/]\n[bold yellow]6°14′45.28″W[/]',  # noqa: RUF001
        '[bold]53.3531000[/]\n[bold]-6.2459100[/]',
        (
          '[bold]13:55 - Maynooth to Dublin Connolly(13 mins late)[/]\n'
          '[bold]TERMINATED Dublin Connolly at 14:51[/]'
        ),
      ],
      [
        '[bold cyan]P375[/]\n[bold][yellow]✗[/][/]',
        '[bold]Southbound[/]',
        '[bold yellow]53°22′59.16″N[/]\n[bold yellow]6°25′27.12″W[/]',  # noqa: RUF001
        '[bold]53.3831000[/]\n[bold]-6.4242000[/]',
        (
          '[bold]14:40 - M3 Parkway to Clonsilla(0 mins late)[/]\n'
          '[bold]TERMINATED Clonsilla at 14:49[/]'
        ),
      ],
    ],
  ),
]

STATION_TABLE: util.ExpectedPrettyPrint = [
  (
    '[magenta]Irish Rail Station '
    '[bold]Malahide with extra looooooooooooooooooong name (MHIDE)[/][magenta] '
    'Board @ [bold]2025/Jun/29-08:14:27-UTC[/]'
  ),
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]Train[/]',
      '[bold cyan]Origin[/]',
      '[bold cyan]Dest.[/]',
      '[bold cyan]Due[/]',
      '[bold cyan]Arrival[/]',
      '[bold cyan]Depart.[/]',
      '[bold cyan]Late[/]',
      '[bold cyan]Status[/]',
      '[bold cyan]Location[/]',
    ],
    rows=[
      [
        '[bold cyan]P702[/]\n[bold](S)[/]\n[bold]DMU[/]',
        '[bold]BRAY[/]\n[bold]Bray[/]\n[bold]08:45:00[/]',
        '[bold yellow]CENTJ[/]\n[bold yellow]Dublin Connolly[/]\n[bold]09:45:00[/]',
        '[bold]+9[/]',
        '[bold green]09:22:00[/]',
        '[bold green]09:23:00[/]\n[bold red]09:27:00[/]',
        '\n[bold red]+5[/]',
        '\n[bold]En Route[/]',
        '\n[bold]Arrived Rush a…[/]',
      ],
      [
        '[bold cyan]E802[/]\n[bold](N)[/]\n[bold]DART[/]',
        '[bold]BRAY[/]\n[bold]Bray[/]\n[bold]08:51:00[/]',
        '[bold yellow]MHIDE[/]\n[bold yellow]Malahide[/]\n[bold]10:06:00[/]',
        '[bold]+52[/]',
        '[bold green]10:06:00[/]\n[bold red]10:07:00[/]',
        '[bold green]∅[/]',
        '\n[bold red]+1[/]',
        '\n[bold]En Route[/]',
        '\n[bold]Arrived Salthi…[/]',
      ],
      [
        '[bold cyan]E205[/]\n[bold](S)[/]\n[bold]DART[/]',
        '[bold]MHIDE[/]\n[bold]Malahide[/]\n[bold]10:24:00[/]',
        '[bold yellow]BRAY[/]\n[bold yellow]Bray[/]\n[bold]11:39:00[/]',
        '[bold]+70[/]',
        '[bold green]∅[/]',
        '[bold green]10:24:00[/]',
        '\n',
        '\n[bold]No Information[/]',
        '\n[bold]∅[/]',
      ],
      [
        '[bold cyan]D802[/]\n[bold](N)[/]\n[bold]DMU[/]',
        '[bold]CENTJ[/]\n[bold]Dublin Connolly[/]\n[bold]10:10:00[/]',
        '[bold yellow]BRAY[/]\n[bold yellow]Bray[/]\n[bold]11:15:00[/]',
        '[bold]+81[/]',
        '[bold green]10:35:00[/]',
        '[bold green]10:38:00[/]\n[bold red]10:39:00[/]',
        '\n[bold yellow]-1[/]',
        '\n[bold]No Information[/]',
        '\n[bold]∅[/]',
      ],
    ],
  ),
]

TRAIN_TABLE: util.ExpectedPrettyPrint = [
  '[magenta]Irish Rail Train [bold]E108[/][magenta] @ [bold]2025/Jun/29-08:14:27-UTC[/]',
  '',
  'Day:         [bold yellow]2025-06-29·Sun[/]',
  'Origin:      [bold yellow]Malahide (MHIDE)[/]',
  'Destination: [bold yellow]Bray (BRAY)[/]',
  '',
  util.ExpectedTable(
    columns=[
      '[bold cyan]#[/]',
      '[bold cyan]Stop[/]',
      '[bold cyan]Arr.(Expect)[/]',
      '[bold cyan]A.(Actual)[/]',
      '[bold cyan]Depart.(Expect)[/]',
      '[bold cyan]D.(Actual)[/]',
      '[bold cyan]Late(Min)[/]',
    ],
    rows=[
      [
        '[bold cyan]1[/]',
        '[bold yellow]MHIDE[/]\n[bold yellow]Malahide[/]\n[bold][green]ORIGIN[/][/]',
        '[bold green]∅[/]\n[bold][green]⚙[/]',
        '[bold yellow]09:19:24[/]',
        '[bold green]09:30:00[/]\n[bold][green]⚙[/]',
        '[bold yellow]09:30:24[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]2[/]',
        '[bold yellow]COBH[/]\n[bold yellow]Cobh[/]\n[bold][green]■[/][/]',
        '[bold green]09:33:30[/]\n[bold red]09:33:54[/]\n[bold][green]⚙[/]',
        '[bold yellow]09:33:12[/]',
        '[bold green]09:34:00[/]\n[bold red]09:33:42[/]\n[bold][green]⚙[/]',
        '[bold yellow]09:34:30[/]',
        '[bold][green]-0.30[/]',
      ],
      [
        '[bold cyan]3[/]',
        '[bold yellow]GRGRD[/]\n[bold yellow]Clongriffin[/]\n[bold][green]■■[/][/]',
        '[bold green]09:36:00[/]\n[bold red]09:36:30[/]\n[bold][green]⚙[/]',
        '[bold yellow]09:35:36[/]',
        '[bold green]09:36:30[/]\n[bold red]09:36:06[/]\n[bold][green]⚙[/]',
        '[bold yellow]09:36:54[/]',
        '[bold][green]-0.40[/]',
      ],
      [
        '[bold cyan]4[/]',
        '[bold yellow]BRAY[/]\n[bold yellow]Bray[/]\n[bold][green]■[/][/]',
        '[bold green]10:44:30[/]\n[bold red]10:44:54[/]\n[bold][green]⚙[/]',
        '[bold yellow]10:43:06[/]',
        '[bold green]10:45:30[/]\n[bold red]10:44:06[/]\n[bold][green]⚙[/]',
        '[bold yellow]10:45:06[/]',
        '[bold][green]-1.40[/]',
      ],
      [
        '[bold cyan]5[/]',
        '[bold yellow]CITYJ[/]\n[bold yellow]CITY JUNCTION[/]\n[bold][red]⏱[/][/]',
        '[bold green]10:46:30[/]\n[bold red]10:46:06[/]',
        '[bold yellow]∅[/]',
        '[bold green]10:46:30[/]\n[bold red]10:46:06[/]',
        '[bold yellow]∅[/]',
        '[bold]∅[/]',
      ],
      [
        '[bold cyan]6[/]',
        '[bold yellow]MOIRA[/]\n[bold yellow]????[/]\n[bold][red]⏱[/][/]',
        '[bold green]10:51:00[/]\n[bold red]10:50:36[/]\n[bold][green]⚙[/]',
        '[bold yellow]10:49:54[/]',
        '[bold green]10:51:00[/]\n[bold red]10:49:54[/]\n[bold][green]⚙[/]',
        '[bold yellow]10:50:18[/]',
        '[bold][green]-1.10[/]',
      ],
      [
        '[bold cyan]7[/]\n[bold yellow]CURRENT[/]',
        '[bold yellow]BRAY[/]\n[bold yellow]Bray[/]\n[bold][green]DESTINATION[/][/]',
        '[bold green]10:55:00[/]\n[bold red]10:54:18[/]\n[bold][green]⚙[/]',
        '[bold yellow]10:55:06[/]',
        '[bold green]∅[/]',
        '[bold yellow]∅[/]',
        '[bold][red]+0.10[/]',
      ],
    ],
  ),
]
