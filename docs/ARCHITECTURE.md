# Architecture

The Chicago Marine Knowledge Service is the **domain layer** for Chicago
lakefront marine conditions. It owns all source collection, normalization,
quality control, and condition interpretation. Clients (notably the
`chicago-marine-knowledge-mcp` wrapper) consume its REST API and never talk to
the underlying sources directly.

```
            ┌─────────────────────────────────────────────┐
 clients ──▶│      Chicago Marine Knowledge Service        │
 (MCP       │                FastAPI app                   │
  wrapper)  │                                              │
            │  places.py   sources/      sailing.py        │
            │  (static)    (connectors)  (interpretation)  │
            └───────┬───────────┬──────────────┬───────────┘
                    │           │              │
        City of Chicago   NOAA GLERL     NOAA Weather MCP
        Socrata (beach    Dever Crib     NOAA Marine MCP
        weather/water)    (CHII2)        (forecast/alerts/buoys)
```

See [DATA_SOURCES.md](DATA_SOURCES.md) for the upstream source contracts and
[API.md](API.md) for the endpoint and response schemas.

---

## Layering principle

The service draws a deliberate line between **observations** and **forecast
context**:

- **Observations** (City beach sensors, Dever Crib) are the measurement
  backbone. They answer "what is actually happening right now."
- **Forecast context** (NOAA Weather MCP, NOAA Marine MCP) is treated as
  context and baseline, not as ground truth.

This separation is why the sailing endpoint compares live observations *against*
the NOAA forecast baseline rather than blending them.

---

## Modules

| Module | Responsibility |
| --- | --- |
| [`app/main.py`](../app/main.py) | FastAPI app, endpoint routing, fan-out, and per-source failure isolation |
| [`app/models.py`](../app/models.py) | Pydantic request/response models and the `SourceKind` enum |
| [`app/places.py`](../app/places.py) | Static catalog of supported places and their City sensor mappings |
| [`app/settings.py`](../app/settings.py) | Source URLs, dataset ids, and request timeout |
| [`app/sources/city.py`](../app/sources/city.py) | City of Chicago Socrata connector (beach weather/water) |
| [`app/sources/dever.py`](../app/sources/dever.py) | NOAA GLERL Dever Crib / CHII2 connector |
| [`app/sources/weather_mcp.py`](../app/sources/weather_mcp.py) | NOAA Weather MCP forecast/alert client |
| [`app/sources/marine_mcp.py`](../app/sources/marine_mcp.py) | NOAA Marine MCP forecast/alert/buoy/briefing client |
| [`app/sources/quality.py`](../app/sources/quality.py) | Sentinel detection and quality flagging |
| [`app/lake_locations.py`](../app/lake_locations.py) | Buoy → lake-area/landmark labeling |
| [`app/sailing.py`](../app/sailing.py) | Sailing-condition interpretation (baseline vs. observation) |

---

## Request fan-out and failure isolation

Endpoints fan out to multiple sources concurrently with `asyncio.gather`. Every
upstream call is wrapped by a `_safe_*` helper in [`app/main.py`](../app/main.py)
that:

1. Applies a timeout (`settings.request_timeout_seconds`, default 12s).
2. On success, records a `SourceStatus` of `healthy` (or `no_data` when the
   source returned nothing).
3. On failure, swallows the exception, records a `SourceStatus` of
   `unavailable` with the error detail, and returns an empty result.

The consequence: a single failing source degrades the response (fewer
observations, a flagged source status) but never fails the whole request. Source
health always travels with the data in `source_statuses`.

---

## Quality control

[`app/sources/quality.py`](../app/sources/quality.py) centralizes bad-data
handling. Known sentinel values from the City and GLERL feeds
(`-100000`, `-99999.992`, `999.9`, `-99`) are treated as missing:

- `parse_float` returns `None` for sentinels so they never enter `values`.
- `quality_flags` records a `<field>:bad_sentinel` flag on the observation so
  clients can see *why* a value is absent.

Quality flags propagate into the sailing endpoint's `cautions` so downstream
LLM briefings can warn about degraded sensors.

---

## Sailing-conditions interpretation

[`app/sailing.py`](../app/sailing.py) turns raw inputs into a sailing
assessment. The design intent is **baseline-first, observation-as-callout**:

1. **Baseline** — Parse wind (kt) and wave (ft) ranges out of the NOAA Marine
   MCP nearshore forecast text (`parse_wind_kt`, `parse_wave_ft`).
2. **Collect observations** — Gather wind from City weather stations, Dever
   Crib, and NDBC buoys; gather waves from City water sensors and buoys.
   Units are normalized to knots and feet (`MPS_TO_KT`, `M_TO_FT`).
3. **Assess** — Take the maximum observed wind/wave, classify it into a
   category, and compare it to the forecast baseline:
   - Wind is `observed_above_forecast` when it exceeds the forecast max by
     more than 3 kt, `observed_below_forecast` when it is more than 3 kt under
     the forecast min, otherwise `observed_matches_forecast`.
   - Waves use the same logic with a 1 ft threshold.
4. **Surface differences** — Only material deviations become `variations`; the
   forecast carries the rest.
5. **Risk, cautions, headline** — Active alerts always dominate. Otherwise risk
   is derived from wind/wave categories, and cautions are added for risky
   conditions and flagged sensor data.
6. **LLM context** — `build_llm_context` assembles a single briefing string
   that leads with alerts and geography, then conditions and callouts.

Category thresholds:

| Wind (kt) | Category | Wave (ft) | Category |
| --- | --- | --- | --- |
| `< 8` | `poor_light` | `< 2` | `smooth` |
| `8–10` | `marginal_light` | `2–5` | `rougher` |
| `10–15` | `good` | `> 5` | `dangerous` |
| `15–20` | `exciting_fast` | | |
| `> 20` | `risky` | | |

Risk level: `high` if any alert is active, wind is `risky`, or waves are
`dangerous`; `moderate` for `exciting_fast` wind or `rougher` waves; otherwise
`low`.

---

## Location labeling

[`app/lake_locations.py`](../app/lake_locations.py) maps NDBC buoy station ids to
human geography (`display_name`, `lake_area`, `landmark`, `narrative_location`),
and `active_for_sailing_summary` controls which buoys appear in the default
Chicago summary. This lets the sailing endpoint describe observations by
landmark ("off downtown Chicago near Navy Pier") instead of raw station ids.
See [DATA_SOURCES.md](DATA_SOURCES.md) for which stations are included and why
others are excluded.

---

## Deployment topology

The service runs as a **private** ECS/Fargate service inside the shared
`mcp-cluster` VPC and is reached only through ECS Service Connect at
`http://cmk-service:8000` (namespace `mcp`) — it has no load balancer and no
public `tomschenkjr.net` hostname. Its security group only admits traffic on
port 8000 from the MCP tasks' security group (`mcp-ecs-tasks-sg`), and it runs
on Fargate Spot. Its own Terraform lives in `terraform/prod`
and is applied independently of `mcp-aws-infra`:

```
chicago-marine-knowledge-service/terraform/prod  ──▶ private REST service (this repo)
mcp-aws-infra/terraform/prod                     ──▶ public MCP wrapper + shared VPC/ALB/ECR + `mcp` namespace
```

The `service_internal_url` output of this repo's Terraform is wired into
`mcp-aws-infra` as the `chicago_marine_knowledge_service_url` variable, which
becomes the MCP wrapper's `MARINE_KNOWLEDGE_SERVICE_URL`. CI/CD
([`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)) builds the
image, pushes to ECR, and rolls the ECS service on every push to `main`.
