from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client

from app.models import SourceKind, SourceStatus
from app.settings import settings
from app.lake_locations import DEFAULT_BUOY_STATIONS, enrich_buoy_observation
from app.sources.weather_mcp import _tool_result_to_dict


BUOY_STATIONS = DEFAULT_BUOY_STATIONS


class MarineMcpClient:
    async def status(self) -> SourceStatus:
        try:
            async with sse_client(str(settings.marine_mcp_sse_url)) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    await session.list_tools()
            return SourceStatus(
                source=SourceKind.MARINE_MCP,
                name="NOAA Marine MCP",
                endpoint=str(settings.marine_mcp_sse_url),
                status="healthy",
            )
        except Exception as exc:  # pragma: no cover - exercised by integration checks
            return SourceStatus(
                source=SourceKind.MARINE_MCP,
                name="NOAA Marine MCP",
                endpoint=str(settings.marine_mcp_sse_url),
                status="unavailable",
                detail=str(exc),
            )

    async def sailing_briefing(self) -> dict[str, Any]:
        async with sse_client(str(settings.marine_mcp_sse_url)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                forecast_result = await session.call_tool("get_nearshore_forecast", {"zone_id": "LMZ741"})
                alerts_result = await session.call_tool("get_marine_alerts", {"zone_id": "LMZ741"})
                return {
                    "location": "Chicago / Lake Michigan",
                    "nearshore_forecast": _tool_result_to_dict(forecast_result) or {},
                    "active_alerts": _tool_result_to_dict(alerts_result) or {},
                }

    async def buoy_observations(self, station_ids: list[str] | None = None) -> list[dict[str, Any]]:
        station_ids = station_ids or BUOY_STATIONS
        observations: list[dict[str, Any]] = []
        async with sse_client(str(settings.marine_mcp_sse_url)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                for station_id in station_ids:
                    result = await session.call_tool("get_buoy_observations", {"station_id": station_id})
                    parsed = _tool_result_to_dict(result) or {}
                    text = parsed.get("text") or parsed.get("result") or "" if isinstance(parsed, dict) else ""
                    observations.append(_parse_buoy_text(station_id, text))
        return observations


def _parse_buoy_text(station_id: str, text: str) -> dict[str, Any]:
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    if not lines:
        return enrich_buoy_observation(
            {"station_id": station_id, "raw": text, "values": {}, "quality_flags": ["no_data"]}
        )

    parts = lines[0].split()
    values: dict[str, Any] = {}
    try:
        values = {
            "wind_direction_deg": _float_or_none(parts[5]),
            "wind_speed_mps": _float_or_none(parts[6]),
            "wind_gust_mps": _float_or_none(parts[7]),
            "wave_height_m": _float_or_none(parts[8]),
            "dominant_wave_period_s": _float_or_none(parts[9]),
            "air_temperature_c": _float_or_none(parts[13]),
            "water_temperature_c": _float_or_none(parts[14]),
        }
    except IndexError:
        return enrich_buoy_observation(
            {"station_id": station_id, "raw": text, "values": {}, "quality_flags": ["parse_error"]}
        )

    return enrich_buoy_observation(
        {
            "station_id": station_id,
            "observed_at": " ".join(parts[:5]),
            "values": values,
            "raw_latest_line": lines[0],
            "quality_flags": [key for key, value in values.items() if value is None],
        }
    )


def _float_or_none(value: str) -> float | None:
    if value in {"MM", "", "NA"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None
