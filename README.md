# Chicago Marine Knowledge Service

Domain API for Chicago lakefront marine conditions.

This service combines shoreline observations, offshore Dever Crib observations,
and NOAA forecast/alert context into source-grounded marine context for
downstream clients.

## Sources

- City of Chicago sensor locations: `g3ip-u8rb`
- City of Chicago beach weather observations: `k7hf-8y75`
- City of Chicago beach water observations: `qmqz-2xku`
- NOAA GLERL Dever Crib / CHII2 observations
- NOAA Weather MCP forecast and alert context
- NOAA Marine MCP forecast, alert, buoy, and sailing briefing context, enriched
  with lake-area and landmark labels for selected Lake Michigan buoys

See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

## Run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoints

```text
GET  /health
GET  /v1/marine/sources
GET  /v1/marine/places
POST /v1/marine/context
POST /v1/marine/sailing-conditions
```

See [docs/API.md](docs/API.md) for full request/response schemas.

## Documentation

- [docs/API.md](docs/API.md) — endpoint and response reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how sources combine and how
  sailing conditions are assessed
- [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) — upstream source contracts and
  quality-control rules

## AWS Deployment

The service is deployed from this repo with Terraform in `terraform/prod`.
It runs as a private ECS/Fargate service in the existing `mcp-cluster` VPC and
is reached by the MCP wrapper through an internal ALB URL.

```bash
cd terraform/prod
AWS_PROFILE=mcp-prod-admin terraform init
AWS_PROFILE=mcp-prod-admin terraform apply
AWS_PROFILE=mcp-prod-admin terraform output service_internal_url
```

Use the `service_internal_url` output as the
`chicago_marine_knowledge_service_url` value in `~/git/mcp-aws-infra`.

The public MCP URL is handled separately by `mcp-aws-infra`; this REST service
does not need a public `tomschenkjr.net` hostname.
