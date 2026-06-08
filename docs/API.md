# API Reference

The Chicago Marine Knowledge Service is a FastAPI application that returns
source-grounded marine context for the Chicago lakefront. All responses are
JSON. There is no authentication; the service is intended to run privately and
be reached only by the MCP wrapper over an internal network.

Interactive schema docs are available when the service is running:

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

Base path conventions:

- `/health` — unversioned liveness probe
- `/v1/marine/*` — versioned marine endpoints

---

## `GET /health`

Liveness probe. Always returns `200` when the process is up; it does not check
upstream sources.

Response:

```json
{
  "status": "healthy",
  "service": "chicago-marine-knowledge-service"
}
```

---

## `GET /v1/marine/places`

List the supported lakefront places and the City sensors each one is mapped to.
Place definitions are static (see [`app/places.py`](../app/places.py)).

Response:

```json
{
  "places": [
    {
      "id": "monroe_harbor",
      "name": "Monroe Harbor",
      "coordinates": { "latitude": 41.8809, "longitude": -87.613 },
      "description": "Downtown Chicago harbor with exposure to nearshore and offshore lake conditions.",
      "weather_station_names": ["Oak Street Weather Station"],
      "water_sensor_names": ["Ohio Street Beach"],
      "use_dever_crib": true
    }
  ]
}
```

Supported `id` values: `monroe_harbor`, `oak_street_beach`, `foster_beach`,
`63rd_street_beach`.

---

## `GET /v1/marine/sources`

Probe every upstream source and report health. Each source is queried with a
timeout (`request_timeout_seconds`, default 12s) and failures are reported
rather than raised, so this endpoint returns `200` even when a source is down.

Response:

```json
{
  "sources": [
    {
      "source": "city_beach_weather",
      "name": "City of Chicago beach sensors",
      "endpoint": "https://data.cityofchicago.org/resource",
      "status": "healthy",
      "detail": null
    }
  ]
}
```

`SourceStatus` fields:

| Field | Meaning |
| --- | --- |
| `source` | One of the `SourceKind` values (see below) |
| `name` | Human-readable source label |
| `endpoint` | Upstream endpoint probed |
| `status` | `healthy`, `no_data`, `unavailable`, or `unknown` |
| `detail` | Error text when `status` is `unavailable`, otherwise `null` |

`SourceKind` values: `city_sensor_locations`, `city_beach_weather`,
`city_beach_water`, `dever_crib`, `weather_mcp`, `marine_mcp`.

---

## `POST /v1/marine/context`

Collect source-grounded context for a single place: shoreline weather, shoreline
water, offshore Dever Crib observations, and NOAA Weather MCP forecast/alert
context.

Request:

```json
{
  "place_id": "monroe_harbor",
  "response_profile": "compact_llm"
}
```

| Field | Default | Meaning |
| --- | --- | --- |
| `place_id` | `monroe_harbor` | A supported place id |
| `response_profile` | `compact_llm` | Hint for downstream formatting; currently informational |

Returns `404` if `place_id` is unknown (the error detail lists valid ids).

Response (`MarineContextResponse`):

| Field | Type | Meaning |
| --- | --- | --- |
| `place` | `Place` | The resolved place definition |
| `shoreline_weather` | `Observation[]` | Latest City beach weather observations for the place's stations |
| `shoreline_water` | `Observation[]` | Latest City beach water observations for the place's sensors |
| `offshore_observations` | `Observation[]` | Latest Dever Crib observation when `use_dever_crib` is true |
| `forecast_context` | `ForecastContext` | NOAA Weather MCP forecast, hourly forecast, and alerts |
| `source_statuses` | `SourceStatus[]` | Per-source health for this request |
| `summary` | `string` | One-line plain-text summary of what was collected |

`Observation` fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `sensor_id` | `string` | Stable sensor identifier |
| `sensor_name` | `string` | Display name |
| `source` | `SourceKind` | Originating source |
| `observed_at` | `datetime?` | Parsed observation time, if available |
| `observed_at_label` | `string?` | Original timestamp label from the source |
| `values` | `object` | Normalized numeric/text values |
| `units` | `object` | Unit per value key |
| `raw` | `object` | Raw upstream record |
| `quality_flags` | `string[]` | Quality-control flags (e.g. sentinel/stale markers) |

`ForecastContext` fields: `source`, `health` (`SourceStatus?`), `tools`
(string list), `note`, `forecast`, `hourly_forecast`, `alerts`.

---

## `POST /v1/marine/sailing-conditions`

Produce a lakewide sailing assessment. The NOAA Marine MCP forecast and alerts
are used as the baseline, and current observations (City shoreline, Dever Crib,
NDBC buoys) are compared against that baseline so only material differences are
surfaced.

Request:

```json
{
  "area_id": "chicago_lakefront",
  "response_profile": "compact_llm"
}
```

| Field | Default | Meaning |
| --- | --- | --- |
| `area_id` | `chicago_lakefront` | Currently the only supported area |
| `response_profile` | `compact_llm` | Hint for downstream formatting; currently informational |

Response (`SailingConditionsResponse`):

| Field | Type | Meaning |
| --- | --- | --- |
| `area_id` | `string` | Echoed area id |
| `headline` | `string` | One-line summary of conditions |
| `risk_level` | `string` | Overall risk derived from alerts, wind, and waves |
| `alerts_first` | `object` | Active marine alerts/advisories, surfaced first |
| `marine_forecast_baseline` | `object` | NOAA forecast zone, source, baseline wind (kt) and waves (ft), raw text |
| `observation_summary` | `object` | City weather/water, Dever Crib, and buoy observations used |
| `location_context` | `object` | Lake-area and landmark labeling for the area and buoys |
| `wind_assessment` | `object` | Observed-vs-baseline wind comparison |
| `wave_assessment` | `object` | Observed-vs-baseline wave comparison |
| `variations` | `string[]` | Notable deviations from the forecast baseline |
| `cautions` | `string[]` | Sailing cautions derived from alerts and observations |
| `source_statuses` | `SourceStatus[]` | Per-source health for this request |
| `llm_briefing_context` | `string` | Pre-assembled context block for an LLM briefing |

See [ARCHITECTURE.md](ARCHITECTURE.md) for how the baseline-versus-observation
assessment is computed, and [DATA_SOURCES.md](DATA_SOURCES.md) for the upstream
source contracts and quality-control rules.
