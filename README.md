# TFINTA - Transport for Ireland Data

## Data Sources

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
