import json

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import TextContent

from app.models import Coordinates
from app.models import ForecastContext, SourceKind, SourceStatus
from app.settings import settings


class WeatherMcpClient:
    async def status(self) -> SourceStatus:
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.get(str(settings.weather_mcp_health_url))
                response.raise_for_status()
                data = response.json()
            return SourceStatus(
                source=SourceKind.WEATHER_MCP,
                name="NOAA Weather MCP",
                endpoint=str(settings.weather_mcp_sse_url),
                status=data.get("status", "healthy"),
                detail=data.get("service"),
            )
        except Exception as exc:  # pragma: no cover - exercised by integration checks
            return SourceStatus(
                source=SourceKind.WEATHER_MCP,
                name="NOAA Weather MCP",
                endpoint=str(settings.weather_mcp_sse_url),
                status="unavailable",
                detail=str(exc),
            )

    async def forecast_context(self, coordinates: Coordinates | None = None) -> ForecastContext:
        forecast = None
        hourly_forecast = None
        alerts = None
        note = (
            "Forecast and alert data are available through the weather MCP SSE endpoint. "
            "No coordinates were supplied for this context request."
        )
        if coordinates is not None:
            try:
                forecast, hourly_forecast, alerts = await self._call_weather_tools(coordinates)
                note = "Forecast, hourly forecast, and alert context were fetched from the weather MCP."
            except Exception as exc:  # pragma: no cover - exercised by integration checks
                note = f"Weather MCP is configured, but tool calls failed: {exc}"

        return ForecastContext(
            health=await self.status(),
            tools=["get_forecast", "get_hourly_forecast", "get_alerts"],
            note=note,
            forecast=forecast,
            hourly_forecast=hourly_forecast,
            alerts=alerts,
        )

    async def _call_weather_tools(
        self,
        coordinates: Coordinates,
    ) -> tuple[dict | None, dict | None, dict | None]:
        async with sse_client(str(settings.weather_mcp_sse_url)) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                args = {
                    "latitude": coordinates.latitude,
                    "longitude": coordinates.longitude,
                }
                forecast_result = await session.call_tool("get_forecast", args)
                hourly_result = await session.call_tool("get_hourly_forecast", args)
                alerts_result = await session.call_tool("get_alerts", args)
                return (
                    _tool_result_to_dict(forecast_result),
                    _tool_result_to_dict(hourly_result),
                    _tool_result_to_dict(alerts_result),
                )


def _tool_result_to_dict(result) -> dict | None:
    if getattr(result, "structuredContent", None):
        return result.structuredContent
    if getattr(result, "structured_content", None):
        return result.structured_content
    content = getattr(result, "content", None) or []
    if len(content) == 1 and isinstance(content[0], TextContent):
        return _json_text_to_dict(content[0].text)
    if content:
        return {"content": [item.model_dump(mode="json") for item in content]}
    return None


def _json_text_to_dict(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}
    if isinstance(parsed, dict):
        return parsed
    return {"value": parsed}
