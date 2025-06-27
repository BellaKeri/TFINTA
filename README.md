# TFINTA - Transport for Ireland Data

This is a set of libraries for loading, parsing, etc on Irish public transit data.

Since version 1.2 it is PyPI package:

<https://pypi.org/project/tfinta/>

## License

Copyright 2025 BellaKeri <BellaKeri@github.com> & Daniel Balparda <balparda@github.com>

Licensed under the ***Apache License, Version 2.0*** (the "License"); you may not use this file except in compliance with the License. You may obtain a [copy of the License here](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

## Overview

TODO

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

* a . `TrainStatus` = ***N*** for not yet running or ***R*** for running.

* b . `TrainCode` is Irish Rail's unique code for an individual train service on a date.

* c . `Direction` is either *Northbound* or *Southbound* for trains between Dundalk and Rosslare and between Sligo and Dublin.  for all other trains the direction is to the destination *eg. To Limerick*.

* d . `Public Message` is the latest information on the train uses ***\n*** for a line break *eg AA509\n11:00 - Waterford to Dublin Heuston (0 mins late)\nDeparted Waterford next stop Thomastown*.

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

## Use

### Install

To use in your project just do:

```sh
pip3 install tfinta
```

and then `from tfinta import base` for using it.

### GTFS

TODO: this needs quite some work.

```sh
poetry run gtfs read
```

### DART

TODO: this needs quite some work.

```sh
poetry run dart print trip -i [id]
```

## Appendix: Development Instructions

### Setup

If you want to develop for this project, first install [Poetry](https://python-poetry.org/docs/cli/), but make sure it is like this:

```sh
brew uninstall poetry
python3.12 -m pip install --user pipx
python3.12 -m pipx ensurepath
# re-open terminal
poetry self add poetry-plugin-export@^1.8  # allows export to requirements.txt (see below)
poetry config virtualenvs.in-project true  # creates venv inside project directory
poetry config pypi-token.pypi <TOKEN>      # add you personal project token
```

Now install the project:

```sh
brew install python@3.12 python@3.13 git
brew update
brew upgrade
brew cleanup -s
# or on Ubuntu/Debian: sudo apt-get install python3.12 python3.12-venv git

git clone https://github.com/BellaKeri/TFINTA.git TFINTA
cd TFINTA

poetry env use python3.12  # creates the venv: use 3.12, but supports 3.13
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

* Versioning of GTFS data
* Migrate to SQL?
