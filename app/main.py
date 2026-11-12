import asyncio

from fastapi import FastAPI, HTTPException

from app.models import (
    MarineContextRequest,
    MarineContextResponse,
    Observation,
    SailingConditionsRequest,
    SailingConditionsResponse,
    SourceKind,
    SourceStatus,
)
from app.places import get_place, list_places
from app.sailing import build_sailing_conditions
from app.sources.city import CitySocrataClient
from app.sources.dever import DeverCribClient
from app.sources.marine_mcp import MarineMcpClient
from app.sources.weather_mcp import WeatherMcpClient
from app.settings import settings

app = FastAPI(
    title="Chicago Marine Knowledge Service",
    description="Source-grounded marine context for Chicago lakefront conditions.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "chicago-marine-knowledge-service"}


@app.get("/v1/marine/places")
async def places():
    return {"places": list_places()}


@app.get("/v1/marine/sources")
async def sources() -> dict[str, list[SourceStatus]]:
    city = CitySocrataClient()
    dever = DeverCribClient()
    marine = MarineMcpClient()
    weather = WeatherMcpClient()
    statuses = await asyncio.gather(
        _safe_status(
            source=SourceKind.CITY_BEACH_WEATHER,
            name="City of Chicago beach sensors",
            endpoint="https://data.cityofchicago.org/resource",
            fetch=city.status,
        ),
        _safe_status(
            source=SourceKind.DEVER_CRIB,
            name="NOAA GLERL Dever Crib / CHII2",
            endpoint="https://www.glerl.noaa.gov/metdata/chi/",
            fetch=dever.status,
        ),
        _safe_status(
            source=SourceKind.MARINE_MCP,
            name="NOAA Marine MCP",
            endpoint="https://marine-mcp.tomschenkjr.net/sse",
            fetch=marine.status,
        ),
        _safe_status(
            source=SourceKind.WEATHER_MCP,
            name="NOAA Weather MCP",
            endpoint="https://weather-mcp.tomschenkjr.net/sse",
            fetch=weather.status,
        ),
    )
    return {"sources": statuses}


@app.post("/v1/marine/context", response_model=MarineContextResponse)
async def marine_context(request: MarineContextRequest) -> MarineContextResponse:
    try:
        place = get_place(request.place_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=_error_detail(exc)) from exc

    city = CitySocrataClient()
    dever = DeverCribClient()
    weather = WeatherMcpClient()

    source_statuses: list[SourceStatus] = []
    shoreline_weather: list[Observation] = []
    for station_name in place.weather_station_names:
        observation = await _safe_observation(
            source=SourceKind.CITY_BEACH_WEATHER,
            name=f"City beach weather: {station_name}",
            endpoint="https://data.cityofchicago.org/resource/k7hf-8y75.json",
            fetch=lambda station_name=station_name: city.latest_weather_observation(station_name),
            source_statuses=source_statuses,
        )
        if observation is not None:
            shoreline_weather.append(observation)

    shoreline_water: list[Observation] = []
    for beach_name in place.water_sensor_names:
        observation = await _safe_observation(
            source=SourceKind.CITY_BEACH_WATER,
            name=f"City beach water: {beach_name}",
            endpoint="https://data.cityofchicago.org/resource/qmqz-2xku.json",
            fetch=lambda beach_name=beach_name: city.latest_water_observation(beach_name),
            source_statuses=source_statuses,
        )
        if observation is not None:
            shoreline_water.append(observation)

    offshore_observations: list[Observation] = []
    if place.use_dever_crib:
        observation = await _safe_observation(
            source=SourceKind.DEVER_CRIB,
            name="NOAA GLERL Dever Crib / CHII2",
            endpoint="https://www.glerl.noaa.gov/metdata/chi/tmp2/file3hr_m.csv",
            fetch=dever.latest_observation,
            source_statuses=source_statuses,
        )
        if observation is not None:
            offshore_observations.append(observation)

    forecast_context = await weather.forecast_context(place.coordinates)
    source_statuses.append(
        await _safe_status(
            source=SourceKind.CITY_BEACH_WEATHER,
            name="City of Chicago beach sensors",
            endpoint="https://data.cityofchicago.org/resource",
            fetch=city.status,
        )
    )
    if forecast_context.health is not None:
        source_statuses.append(forecast_context.health)

    return MarineContextResponse(
        place=place,
        shoreline_weather=shoreline_weather,
        shoreline_water=shoreline_water,
        offshore_observations=offshore_observations,
        forecast_context=forecast_context,
        source_statuses=[status for status in source_statuses if status is not None],
        summary=_build_summary(
            place_name=place.name,
            shoreline_weather_count=len(shoreline_weather),
            shoreline_water_count=len(shoreline_water),
            offshore_count=len(offshore_observations),
            weather_mcp_status=forecast_context.health.status if forecast_context.health else "unknown",
        ),
    )


@app.post("/v1/marine/sailing-conditions", response_model=SailingConditionsResponse)
async def sailing_conditions(request: SailingConditionsRequest) -> SailingConditionsResponse:
    city = CitySocrataClient()
    dever = DeverCribClient()
    marine = MarineMcpClient()
    source_statuses: list[SourceStatus] = []

    (
        city_weather,
        city_water,
        dever_observation,
        city_status,
        marine_results,
    ) = await asyncio.gather(
        _safe_list(
            source=SourceKind.CITY_BEACH_WEATHER,
            name="City beach weather observations",
            endpoint="https://data.cityofchicago.org/resource/k7hf-8y75.json",
            fetch=city.latest_weather_observations,
            source_statuses=source_statuses,
        ),
        _safe_list(
            source=SourceKind.CITY_BEACH_WATER,
            name="City beach water observations",
            endpoint="https://data.cityofchicago.org/resource/qmqz-2xku.json",
            fetch=city.latest_water_observations,
            source_statuses=source_statuses,
        ),
        _safe_observation(
            source=SourceKind.DEVER_CRIB,
            name="NOAA GLERL Dever Crib / CHII2",
            endpoint="https://www.glerl.noaa.gov/metdata/chi/tmp2/file3hr_m.csv",
            fetch=dever.latest_observation,
            source_statuses=source_statuses,
        ),
        _safe_status(
            source=SourceKind.CITY_BEACH_WEATHER,
            name="City of Chicago beach sensors",
            endpoint="https://data.cityofchicago.org/resource",
            fetch=city.status,
        ),
        _safe_marine_sailing_inputs(marine, source_statuses),
    )
    marine_briefing, buoys = marine_results
    source_statuses.append(city_status)

    data = build_sailing_conditions(
        area_id=request.area_id,
        marine_briefing=marine_briefing,
        city_weather=city_weather,
        city_water=city_water,
        dever=dever_observation,
        buoys=buoys,
        source_statuses=source_statuses,
    )
    return SailingConditionsResponse(**data)


async def _safe_marine_sailing_inputs(
    marine: MarineMcpClient,
    source_statuses: list[SourceStatus],
) -> tuple[dict, list]:
    forecast, alerts, buoys = await asyncio.gather(
        _safe_dict(
            source=SourceKind.MARINE_MCP,
            name="NOAA Marine MCP nearshore forecast",
            endpoint="https://marine-mcp.tomschenkjr.net/sse",
            fetch=marine.nearshore_forecast,
            source_statuses=source_statuses,
        ),
        _safe_dict(
            source=SourceKind.MARINE_MCP,
            name="NOAA Marine MCP alerts",
            endpoint="https://marine-mcp.tomschenkjr.net/sse",
            fetch=marine.marine_alerts,
            source_statuses=source_statuses,
        ),
        _safe_list(
            source=SourceKind.MARINE_MCP,
            name="NOAA Marine MCP buoy observations",
            endpoint="https://marine-mcp.tomschenkjr.net/sse",
            fetch=marine.buoy_observations,
            source_statuses=source_statuses,
        ),
    )
    marine_briefing = {
        "location": "Chicago / Lake Michigan",
        "nearshore_forecast": forecast,
        "active_alerts": alerts,
    }
    return marine_briefing, buoys


def _build_summary(
    place_name: str,
    shoreline_weather_count: int,
    shoreline_water_count: int,
    offshore_count: int,
    weather_mcp_status: str,
) -> str:
    return (
        f"{place_name} context includes {shoreline_weather_count} shoreline weather observation(s), "
        f"{shoreline_water_count} shoreline water observation(s), {offshore_count} offshore Dever Crib "
        f"observation(s), and weather MCP forecast/alert source status '{weather_mcp_status}'."
    )


async def _safe_observation(
    source: SourceKind,
    name: str,
    endpoint: str,
    fetch,
    source_statuses: list[SourceStatus],
) -> Observation | None:
    try:
        observation = await asyncio.wait_for(fetch(), timeout=settings.request_timeout_seconds)
    except Exception as exc:  # pragma: no cover - exercised by integration checks
        source_statuses.append(
            SourceStatus(
                source=source,
                name=name,
                endpoint=endpoint,
                status="unavailable",
                detail=_error_detail(exc),
            )
        )
        return None

    source_statuses.append(
        SourceStatus(
            source=source,
            name=name,
            endpoint=endpoint,
            status="healthy" if observation is not None else "no_data",
        )
    )
    return observation


async def _safe_list(
    source: SourceKind,
    name: str,
    endpoint: str,
    fetch,
    source_statuses: list[SourceStatus],
) -> list:
    try:
        items = await asyncio.wait_for(fetch(), timeout=settings.request_timeout_seconds)
    except Exception as exc:  # pragma: no cover - exercised by integration checks
        source_statuses.append(
            SourceStatus(source=source, name=name, endpoint=endpoint, status="unavailable", detail=_error_detail(exc))
        )
        return []
    source_statuses.append(
        SourceStatus(source=source, name=name, endpoint=endpoint, status="healthy" if items else "no_data")
    )
    return items


async def _safe_dict(
    source: SourceKind,
    name: str,
    endpoint: str,
    fetch,
    source_statuses: list[SourceStatus],
) -> dict:
    try:
        item = await asyncio.wait_for(fetch(), timeout=settings.request_timeout_seconds)
    except Exception as exc:  # pragma: no cover - exercised by integration checks
        source_statuses.append(
            SourceStatus(source=source, name=name, endpoint=endpoint, status="unavailable", detail=_error_detail(exc))
        )
        return {}
    source_statuses.append(
        SourceStatus(source=source, name=name, endpoint=endpoint, status="healthy" if item else "no_data")
    )
    return item


async def _safe_status(source: SourceKind, name: str, endpoint: str, fetch) -> SourceStatus:
    try:
        return await asyncio.wait_for(fetch(), timeout=settings.request_timeout_seconds)
    except Exception as exc:  # pragma: no cover - exercised by integration checks
        return SourceStatus(source=source, name=name, endpoint=endpoint, status="unavailable", detail=_error_detail(exc))


def _error_detail(exc: Exception) -> str:
    """Readable error text; some exceptions (e.g. TimeoutError) have an empty str()."""
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__
