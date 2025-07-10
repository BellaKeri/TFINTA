# TFINTA - Transport for Ireland Data

***"Python library and shell scripts for parsing and displaying*** **Transport for Ireland (TFI/NTA)** ***Rail and DART schedule datasets, both GTFS and realtime"***

Since version 1.2 it is PyPI package:

<https://pypi.org/project/tfinta/>

- [TFINTA - Transport for Ireland Data](#tfinta---transport-for-ireland-data)
  - [License](#license)
  - [Overview](#overview)
  - [Use](#use)
    - [Install](#install)
    - [Quick start](#quick-start)
    - [GTFS tool: `gtfs`](#gtfs-tool-gtfs)
      - [`gtfs read` command](#gtfs-read-command)
      - [`gtfs print` command](#gtfs-print-command)
    - [DART tool: `dart`](#dart-tool-dart)
    - [`dart read` command](#dart-read-command)
    - [`dart print` command](#dart-print-command)
    - [Realtime tool: `realtime`](#realtime-tool-realtime)
    - [`realtime print` command](#realtime-print-command)
  - [Data Sources](#data-sources)
    - [Stations](#stations)
    - [Trains](#trains)
    - [GTFS Schedule Files](#gtfs-schedule-files)
  - [Development Instructions](#development-instructions)
    - [Setup](#setup)
    - [Updating Dependencies](#updating-dependencies)
    - [Creating a New Version](#creating-a-new-version)
    - [TODO](#todo)

## License

Copyright 2025 BellaKeri <BellaKeri@github.com> & Daniel Balparda <balparda@github.com>

Licensed under the ***Apache License, Version 2.0*** (the "License"); you may not use this file except in compliance with the License. You may obtain a [copy of the License here](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

## Overview

TFINTA (Transport for Ireland Data) is a small, batteries-included toolkit for working with publicly-available Irish public-transport datasets—right from your shell or from pure Python.

| What you get | CLI entry-point | What it does |
|:-------------|:---------------:|:-------------|
| Static GTFS schedules for bus, rail, ferry, Luas… | `gtfs` | Download the national GTFS bundle, cache it, and let you inspect any table (agency, stops, routes, shapes, trips, calendars…). |
| Irish Rail / DART schedules (their separate GTFS feed) | `dart` | Same idea, but focused on heavy-rail only—extra helpers for station boards and service calendars. |
| Live train movements via the Irish Rail XML feed | `realtime` | Query the current running trains or a live arrivals/departures board for any station. |
| Python API | `import tfinta` | Load the cached databases as Pandas DataFrames or iterate over strongly-typed dataclasses. |

The authors and the library/tools art ***NOT*** affiliated with TFI or Irish Rail. The project simply republishes data that both agencies already expose for free. Always check the license/terms on the upstream feeds before redistributing.

Why another transport library?

- One-stop shop – static schedules and live positions under a single import.
- Zero boilerplate – no need to remember URLs; the code bundles them.
- Typed, 90%+ test-covered, MIT-compatible – ideal for research, hobby dashboards or production back-ends.
- Friendly CLI – perfect for quick shell exploration or cron-driven exports.

Happy hacking & *fáilte chuig sonraí iompair na hÉireann!*

## Use

The TFINTA CLI (`gtfs`, `dart` and `realtime` commands) lets you download, cache, inspect, and pretty-print the official Transport for Ireland Rail and DART schedule dataset from your shell. It also allows you access to realtime data provided by the rail service.

### Install

To use in your project/terminal just do:

```sh
poetry add tfinta  # (or pip install tfinta)
```

(In code you will use as `from tfinta import dart` for example.)

### Quick start

```shell
poetry add tfinta             # 1: Install the library
poetry run gtfs read          # 2: Download latest GTFS feed (cached for 7 days)
poetry run gtfs print basics  # 3: View some basics (files, agencies, routes)
poetry run dart print stops   # 4: Show all DART stops
poetry run dart print trips -d 20250701  # 5: Show all DART trips for 1st Jul 2025
poetry run realtime print running        # 6: See the trains currently running on the network
```

### GTFS tool: `gtfs`

All commands are executed through Poetry so your project’s virtual-env is used: `poetry run gtfs [-v] <command> [<sub-command>] [options]`

- `-v` / `-vv` / `-vvv` / `-vvvv` Raise log level from `ERROR` → `WARN` → `INFO` → `DEBUG**`
- `<command>` Either read (download/update data) or print (pretty-print parts of the DB)
- `<sub-command>` Only required for `print` (see below)
- options Command-specific flags (see full `-h` output below)

Below is the exact `-h`/`--help` output so you can see every flag at a glance. Each block is produced with the same Poetry invocation you will use (`poetry run gtfs …`).

```text
usage: gtfs [-h] [-v] {read,print} ...

positional arguments:
  {read,print}
    read         Read DB from official sources
    print        Print DB

options:
  -h, --help     show this help message and exit
  -v, --verbose  Increase verbosity (use -v, -vv, -vvv, -vvvv for ERR/WARN/INFO/DEBUG output)
```

#### `gtfs read` command

Downloads / refreshes the GTFS zip, parses it and stores it locally. The data will live, by default, in `src/tfinta/.tfinta-data/transit.db`, the caching will share the `src/tfinta/.tfinta-data` directory.

```text
usage: gtfs read [-h] [-f FRESHNESS] [-u UNKNOWNFILE] [-i UNKNOWNFIELD] [-r REPLACE] [-o OVERRIDE]

options:
  -h, --help            show this help message and exit
  -f FRESHNESS, --freshness FRESHNESS
                        Number of days to cache; 0 == always load (default: 10)
  -u UNKNOWNFILE, --unknownfile UNKNOWNFILE
                        0 == disallows unknown files ; 1 == allows unknown files (default: 1)
  -i UNKNOWNFIELD, --unknownfield UNKNOWNFIELD
                        0 == disallows unknown fields ; 1 == allows unknown fields (default: 0)
  -r REPLACE, --replace REPLACE
                        0 == does not load the same version again ; 1 == forces replace version (default: 0)
  -o OVERRIDE, --override OVERRIDE
                        If given, this ZIP file path will override the download (default: empty)
```

Examples:

```shell
# Force-download the feed even if cached < 7 days
poetry run gtfs read -f 0

# Parse a local experimental feed instead of the official zip
poetry run gtfs read -o /tmp/gtfs-test.zip

# Replace an existing version even if it has the same feed_info.txt version
poetry run gtfs read -s 1
```

#### `gtfs print` command

Pretty-prints pieces of the cached database. Requires one sub-command that selects what to show.

```text
usage: gtfs print [-h] {basics,calendars,stops,shape,trip,all} ...

positional arguments:
  {basics,calendars,stops,shape,trip,all}
    basics              Print Basic Data
    calendars           Print Calendars/Services
    stops               Print Stops
    shape               Print Shape
    trip                Print Trip
    all                 Print All Data

options:
  -h, --help            show this help message and exit
```

Sub-commands & examples:

| Sub-command | What it shows | Options | Example |
|:------------|:--------------|:--------|:--------|
| `basics` | Feed metadata (agency, version, date span, language…) |  | `poetry run gtfs print basics` |
| `calendars` | Service calendars plus any exceptions |  | `poetry run gtfs print calendars` |
| `stops` | Every stop with lat/lon and parent station |  | `poetry run gtfs print stops` |
| `shape` | All points making up one shape trajectory | `-i ID, --id ID` Shape ID | `poetry run gtfs print shape -i 4452_42` |
| `trip` | Stop-times, shape and calendar for one trip | `-i ID, --id ID` Trip ID` | `poetry run gtfs print trip -i 4452_210` |
| `all` | A concatenation of every printable section |  | `poetry run gtfs print all > everything.txt` |

### DART tool: `dart`

All commands are executed through Poetry so your project’s virtual-env is used: `poetry run dart [-v] <command> [<sub-command>] [options]` (same `-v` flag and command/sub-command structure as with `gtfs`).

```text
usage: dart [-h] [-v] {read,print} ...

positional arguments:
  {read,print}
    read         Read DB from official sources
    print        Print DB

options:
  -h, --help     show this help message and exit
  -v, --verbose  Increase verbosity (use -v, -vv, -vvv, -vvvv for ERR/WARN/INFO/DEBUG output)
```

### `dart read` command

Downloads or refreshes the Rail-&-DART GTFS zip, parses it and stores it locally. Basically a wrapper for `gtfs read`.

```text
usage: dart read [-h] [-f FRESHNESS] [-r REPLACE]

options:
  -h, --help            show this help message and exit
  -f FRESHNESS, --freshness FRESHNESS
                        Number of days to cache; 0 == always load (default: 10)
  -r REPLACE, --replace REPLACE
                        0 == does not load the same version again ; 1 == forces replace version (default: 0)
```

### `dart print` command

Pretty-prints slices of the cached DART database. Requires one sub-command selecting what to display.

```text
usage: dart print [-h] {calendars,stops,trips,station,trip,all} ...

positional arguments:
  {calendars,stops,trips,station,trip,all}
    calendars           Print Calendars/Services
    stops               Print Stops
    trips               Print Trips
    station             Print Station Chart
    trip                Print DART Trip
    all                 Print All Data

options:
  -h, --help            show this help message and exit
```

Sub-commands & examples:

| Sub-command | What it shows | Options | Example |
|:------------|:--------------|:--------|:--------|
| `calendars` | Every service calendar plus exceptions |  | `poetry run dart print calendars` |
| `stops` | All DART stops with lat/lon & CRR code |  | `poetry run dart print stops` |
| `trips` | All DART train services on a day | `-d DAY, --day DAY` day to consider in `YYYYMMDD` format (default: today) | `poetry run dart print trips -d 20250815` |
| `station` | Arrivals/departures board for one station on a day | `-s STATION, --station STATION` station to print chart for; finds by ID (stops.txt/stop_id) or by name (stop_name)<br/>`-d DAY, --day DAY` day to consider in `YYYYMMDD` format (default: today) | `poetry run dart print station -s "Tara"` <!-- markdownlint-disable-line MD033 --> |
| `trip` | Detailed stop-times & shape for a single train | -c CODE, --code CODE  DART train code, like "E108" for example | `poetry run dart print trip -c E108` |
| `all` | Concatenation of every printable section |  | `poetry run dart print all > dart.txt` |

### Realtime tool: `realtime`

All commands are executed through Poetry so your project’s virtual-env is used: `poetry run dart [-v] <command> [<sub-command>] [options]` (same `-v` flag and command/sub-command structure as with `gtfs`).

```text
usage: realtime [-h] [-v] {print} ...

positional arguments:
  {print}
    print        Print RPC Call

options:
  -h, --help     show this help message and exit
  -v, --verbose  Increase verbosity (use -v, -vv, -vvv, -vvvv for ERR/WARN/INFO/DEBUG output)
```

### `realtime print` command

Prints realtime data.

```text
usage: realtime print [-h] {stations,running,station,train} ...

positional arguments:
  {stations,running,station,train}
    stations            Print All System Stations
    running             Print Running Trains
    station             Print Station Board
    train               Print Train Movements

options:
  -h, --help            show this help message and exit
```

Sub-commands & examples:

| Sub-command | What it shows | Options | Example |
|:------------|:--------------|:--------|:--------|
| `stations` | Every station with 5-letter code, lat/lon & county |  | `poetry run realtime print stations` |
| `running` | All trains currently reporting movement, inc. origin/destination & delay |  | `poetry run realtime print running` |
| `station` | Live board for one station on the current day (arrivals, departures, platform, delay) | `-c CODE, --code CODE` Either a 5-letter station code (ex: `LURGN`) or a search string that can be identified as a station (ex: `lurgan`) | `poetry run realtime print station -c tara` |
| `train` | Full movement log for a single train: each stop’s schedule/expected/actual times | `-c CODE, --code CODE` Train code (ex: `E108`)<br/>`-d DAY, --day DAY` day to consider in `YYYYMMDD` format (default: today) | `poetry run realtime print train -c E108` <!-- markdownlint-disable-line MD033 --> |

## Data Sources

### Stations

[GPT Search](https://chatgpt.com/share/683abe5a-9e80-800d-b703-f5080a69c970)

[Official dataset Rail&DART](https://api.irishrail.ie/realtime/)

1. [Get All Stations](http://api.irishrail.ie/realtime/realtime.asmx/getAllStationsXML) - usage  returns a list of all stations with `StationDesc`, `StationCode`, `StationId`, `StationAlias`, `StationLatitude` and `StationLongitude` ordered by Latitude, Longitude. Example:

```xml
<objStation>
    <StationDesc>Howth Junction</StationDesc>
    <StationAlias>Donaghmede ( Howth Junction )</StationAlias>
    <StationLatitude>53.3909</StationLatitude>
    <StationLongitude>-6.15672</StationLongitude>
    <StationCode>HWTHJ</StationCode>
    <StationId>105</StationId>
</objStation>
```

### Trains

[Official running Trains](http://api.irishrail.ie/realtime/)

1. [Get All Running Trains](http://api.irishrail.ie/realtime/realtime.asmx/getCurrentTrainsXML) - Usage returns a listing of 'running trains' ie trains that are between origin and destination or are due to start within 10 minutes of the query time. Returns `TrainStatus`, `TrainLatitude`, `TrainLongitude`, `TrainCode`, `TrainDate`, `PublicMessage` and `Direction`.

- a . `TrainStatus` = ***N*** for not yet running or ***R*** for running.

- b . `TrainCode` is Irish Rail's unique code for an individual train service on a date.

- c . `Direction` is either *Northbound* or *Southbound* for trains between Dundalk and Rosslare and between Sligo and Dublin.  for all other trains the direction is to the destination *eg. To Limerick*.

- d . `Public Message` is the latest information on the train uses ***\n*** for a line break *eg AA509\n11:00 - Waterford to Dublin Heuston (0 mins late)\nDeparted Waterford next stop Thomastown*.

```xml
<objTrainPositions>
    <TrainStatus>N</TrainStatus>
    <TrainLatitude>51.9018</TrainLatitude>
    <TrainLongitude>-8.4582</TrainLongitude>
    <TrainCode>D501</TrainCode>
    <TrainDate>01 Jun 2025</TrainDate>
    <PublicMessage>D501\nCork to Cobh\nExpected Departure 08:00</PublicMessage>
    <Direction>To Cobh</Direction>
</objTrainPositions>
```

### GTFS Schedule Files

The [Official GTFS Schedules](https://data.gov.ie/dataset/operator-gtfs-schedule-files) will have a small 19kb CSV, [currently here](https://www.transportforireland.ie/transitData/Data/GTFS%20Operator%20Files.csv), that has the positions of all GTFS files. We will load this CSV to search for the `Iarnród Éireann / Irish Rail` entry.

GTFS is [defined here](https://gtfs.org/documentation/schedule/reference/). It has 6 mandatory tables (files) and a number of optional ones. We will start by making a cached loader for this data into memory dicts that will be pickled to disk.

## Development Instructions

### Setup

If you want to develop for this project, first install [Poetry](https://python-poetry.org/docs/cli/), but make sure it is like this:

```sh
brew uninstall poetry
python3.11 -m pip install --user pipx
python3.11 -m pipx ensurepath
# re-open terminal
poetry self add poetry-plugin-export@^1.8  # allows export to requirements.txt (see below)
poetry config virtualenvs.in-project true  # creates venv inside project directory
poetry config pypi-token.pypi <TOKEN>      # add you personal project token
```

Now install the project:

```sh
brew install python@3.11 python@3.13 git
brew update
brew upgrade
brew cleanup -s
# or on Ubuntu/Debian: sudo apt-get install python3.11 python3.11-venv git

git clone https://github.com/BellaKeri/TFINTA.git TFINTA
cd TFINTA

poetry env use python3.11  # creates the venv: use 3.11, but supports 3.13
poetry install --sync      # HONOR the project's poetry.lock file, uninstalls stray packages
poetry env info            # no-op: just to check

poetry run pytest
# or any command as:
poetry run <any-command>
```

To activate like a regular environment do:

```sh
poetry env activate
# will print activation command which you next execute, or you can do:
source .env/bin/activate                         # if .env is local to the project
source "$(poetry env info --path)/bin/activate"  # for other paths

pytest

deactivate
```

### Updating Dependencies

To update `poetry.lock` file to more current versions:

```sh
poetry update  # ignores current lock, updates, rewrites `poetry.lock` file
poetry run pytest
```

To add a new dependency you should:

```sh
poetry add "pkg>=1.2.3"  # regenerates lock, updates env
# also: "pkg@^1.2.3" = latest 1.* ; "pkg@~1.2.3" = latest 1.2.* ; "pkg@1.2.3" exact
poetry export --format requirements.txt --without-hashes --output requirements.txt
```

If you added a dependency to `pyproject.toml`:

```sh
poetry run pip3 freeze --all  # lists all dependencies pip knows about
poetry lock     # re-lock your dependencies, so `poetry.lock` is regenerated
poetry install  # sync your virtualenv to match the new lock file
poetry export --format requirements.txt --without-hashes --output requirements.txt
```

### Creating a New Version

```sh
# bump the version!
poetry version minor  # updates 1.6 to 1.7, for example
# or:
poetry version patch  # updates 1.6 to 1.6.1
# or:
poetry version <version-number>
# (also updates `pyproject.toml` and `poetry.lock`)

# publish to GIT, including a TAG
git commit -a -m "release version 1.7"
git tag 1.7
git push
git push --tags

# prepare package for PyPI
poetry build
poetry publish
```

### TODO

- Versioning of GTFS data
- Migrate to SQL?
