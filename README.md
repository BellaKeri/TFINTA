# TFINTA - Transport for Ireland Data

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

The [Official GTFS Schedules](https://data.gov.ie/dataset/operator-gtfs-schedule-files)
will have a small 19kb CSV,
[currently here](https://www.transportforireland.ie/transitData/Data/GTFS%20Operator%20Files.csv),
that has the positions of all GTFS files.
We will load this CSV to search for the `Iarnród Éireann / Irish Rail` entry.

GTFS is [defined here](https://gtfs.org/documentation/schedule/reference/).
It has 6 mandatory tables (files) and a number of optional ones.
We will start by making a cached loader for this data into memory dicts
that will be pickled to disk.

## Installation & Usage

### Dependencies

```sh
brew install git uv python@3.13

git clone https://github.com/BellaKeri/TFINTA.git TFINTA
cd TFINTA

uv venv --python 3.13
source .venv/bin/activate
uv pip install --upgrade pip
uv pip install -r requirements.txt

pytest

deactivate
```

### Running GTFS to load the database

```sh
./gtfs.py read
```
