# Data Source Contracts

This service uses Chicago-specific observations as the observation backbone and
uses the NOAA Weather MCP for forecast and alert context.

## City Sensor Locations

- Dataset: `g3ip-u8rb`
- API: `https://data.cityofchicago.org/resource/g3ip-u8rb.json`
- Metadata: `https://data.cityofchicago.org/api/views/g3ip-u8rb.json`
- Owner: Chicago Park District
- Frequency: updated as needed
- Role: sensor metadata and place coordinates

Fields:

| Field | Meaning |
| --- | --- |
| `sensor_name` | Sensor display name |
| `sensor_type` | `Weather` or `Water` |
| `latitude` | Decimal latitude |
| `longitude` | Decimal longitude |
| `location` | Socrata point |

Relationship:

- `sensor_name` maps to `station_name` in `k7hf-8y75` for weather sensors.
- `sensor_name` maps to `beach_name` in `qmqz-2xku` for water sensors.

## City Beach Weather Observations

- Dataset: `k7hf-8y75`
- API: `https://data.cityofchicago.org/resource/k7hf-8y75.json`
- Metadata: `https://data.cityofchicago.org/api/views/k7hf-8y75.json`
- Owner: Chicago Park District
- Frequency: hourly while sensors are operating
- Time period: starts 2015-05-22; current in season
- Role: shoreline and beach weather observations

Fields:

| Field | Unit | Meaning |
| --- | --- | --- |
| `station_name` | text | Weather station name |
| `measurement_timestamp` | local timestamp | Observation time |
| `air_temperature` | C | Air temperature |
| `wet_bulb_temperature` | C | Wet bulb temperature |
| `humidity` | % | Relative humidity |
| `rain_intensity` | mm/hr | Rain intensity |
| `interval_rain` | mm | Rain since last hourly measurement |
| `total_rain` | mm | Rain since midnight |
| `precipitation_type` | code | 0 none, 60 liquid, 70 solid, 40 unspecified |
| `wind_direction` | degrees | Wind direction |
| `wind_speed` | m/s | Wind speed at report time |
| `maximum_wind_speed` | m/s | Max wind in preceding two-minute period |
| `barometric_pressure` | hPa | Barometric pressure |
| `solar_radiation` | W/m2 | Solar radiation |
| `heading` | degrees | Wind unit heading |
| `battery_life` | volts | Battery voltage |

Known behavior:

- Some stations can become stale or seasonal.
- Values such as `999.9` may appear in wind fields and should be treated as
  invalid by quality-control rules.

## City Beach Water Observations

- Dataset: `qmqz-2xku`
- API: `https://data.cityofchicago.org/resource/qmqz-2xku.json`
- Metadata: `https://data.cityofchicago.org/api/views/qmqz-2xku.json`
- Owner: Chicago Park District
- Frequency: hourly while sensors are operating
- Time period: starts 2014-05-28; current in season
- Role: nearshore water observations

Fields:

| Field | Unit | Meaning |
| --- | --- | --- |
| `beach_name` | text | Beach/sensor name |
| `measurement_timestamp` | local timestamp | Observation time |
| `water_temperature` | C | Water temperature |
| `turbidity` | NTU | Water turbidity |
| `transducer_depth` | m | Transducer depth |
| `wave_height` | m | Wave height |
| `wave_period` | seconds | Wave period |
| `battery_life` | volts | Battery voltage |

Known behavior:

- Sensor locations may change with Park District operational needs.
- Sentinel values such as `-100000` and `-99999.992` appear in wave and water
  fields and should be treated as missing/bad data.

## Dever Crib / GLERL CHII2

- Station: `CHII2`
- Site: Harrison-Dever Crib, approximately 2.75 miles offshore
- Page: `https://www.glerl.noaa.gov/metdata/chi/`
- Recent CSV: `https://www.glerl.noaa.gov/metdata/chi/tmp2/file3hr_m.csv`
- Daily raw files: `https://www.glerl.noaa.gov/metdata/chi/{year}/{yyyymmdd}.04t.txt`
- Metadata: `https://www.glerl.noaa.gov/metdata/chi/metadata.html`
- Role: offshore exposure and lake reference observations

Metadata:

| Attribute | Value |
| --- | --- |
| Approximate coordinates | 41.926, -87.572 |
| Site online | 2000-08-03 |
| Site elevation | 176.0 m above mean sea level |
| Anemometer height | 25.9 m above site elevation |
| Air temp height | 22.9 m above site elevation |
| Sampling | every second |
| Averaging interval | 2 minutes |
| Missing sentinel | `-99` |

Daily raw fields:

| Column | Unit | Meaning |
| --- | --- | --- |
| `ID` | code | Chicago is `4` |
| `Year` | year | Year |
| `DOY` | day | Day of year |
| `UTC` | HHMM | UTC time |
| `AirTemp` | C | Average air temperature |
| `WindSpd` | m/s | Scalar average wind speed |
| `WindGst` | m/s | Wind speed maximum |
| `WindDir` | degrees | Unit-vector average wind direction |
| `RelHum` | % | Average relative humidity |

## NOAA Weather MCP

- Health: `https://weather-mcp.tomschenkjr.net/health`
- SSE endpoint: `https://weather-mcp.tomschenkjr.net/sse`
- Role: NOAA point forecast, hourly forecast, and active weather alerts

The knowledge service treats this as forecast and alert context, not as an
observation source.

## NOAA Marine MCP / NDBC Buoy Observations

- SSE endpoint: `https://marine-mcp.tomschenkjr.net/sse`
- Upstream observations: NDBC recent buoy observations
- Role: NOAA marine forecast, active marine alerts, and selected Lake Michigan
  buoy observations

Default buoy station set:

| Station | Display name | Narrative location | Role |
| --- | --- | --- | --- |
| `45174` | Wilmette Buoy | near Wilmette Harbor on the north shore | north shore reference |
| `45198` | Chicago Buoy | off downtown Chicago near Navy Pier and Monroe Harbor | central lakefront reference |

Known behavior:

- Station metadata is attached to buoy observations as `display_name` and
  `location` so clients can use landmarks instead of raw station ids.
- `45013` Atwater Park metadata is retained for optional regional context, but
  it is not in the default Chicago sailing query set because it represents the
  Milwaukee shoreline rather than Chicago lakefront conditions.
- `45007` metadata is retained for open-water context, but it is not in the
  default live query set while its realtime NDBC endpoint returns `404`.
- `45012` is intentionally excluded from the default Chicago sailing summary
  because it is an East Lake Ontario buoy, not a Lake Michigan buoy.
- `45024` is intentionally excluded from the default Chicago sailing summary
  because Ludington is too far north to represent Chicago lakefront conditions.
- Seasonal or recovered buoys may return no recent reports; those records are
  retained with quality flags but ignored in wind and wave comparisons when
  numeric observations are absent.
