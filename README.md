# TFINTA - Transport for Ireland Data

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