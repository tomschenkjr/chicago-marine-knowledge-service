from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SourceKind(StrEnum):
    CITY_SENSOR_LOCATIONS = "city_sensor_locations"
    CITY_BEACH_WEATHER = "city_beach_weather"
    CITY_BEACH_WATER = "city_beach_water"
    DEVER_CRIB = "dever_crib"
    WEATHER_MCP = "weather_mcp"
    MARINE_MCP = "marine_mcp"


class SourceStatus(BaseModel):
    source: SourceKind
    name: str
    endpoint: str
    status: str
    detail: str | None = None


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class Sensor(BaseModel):
    id: str
    name: str
    source: SourceKind
    sensor_type: str
    coordinates: Coordinates | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    sensor_id: str
    sensor_name: str
    source: SourceKind
    observed_at: datetime | None = None
    observed_at_label: str | None = None
    values: dict[str, Any] = Field(default_factory=dict)
    units: dict[str, str] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)
    quality_flags: list[str] = Field(default_factory=list)


class ForecastContext(BaseModel):
    source: SourceKind = SourceKind.WEATHER_MCP
    health: SourceStatus | None = None
    tools: list[str] = Field(default_factory=list)
    note: str
    forecast: dict[str, Any] | None = None
    hourly_forecast: dict[str, Any] | None = None
    alerts: dict[str, Any] | None = None


class Place(BaseModel):
    id: str
    name: str
    coordinates: Coordinates
    description: str
    weather_station_names: list[str] = Field(default_factory=list)
    water_sensor_names: list[str] = Field(default_factory=list)
    use_dever_crib: bool = True


class MarineContextRequest(BaseModel):
    place_id: str = "monroe_harbor"
    response_profile: str = "compact_llm"


class MarineContextResponse(BaseModel):
    place: Place
    shoreline_weather: list[Observation] = Field(default_factory=list)
    shoreline_water: list[Observation] = Field(default_factory=list)
    offshore_observations: list[Observation] = Field(default_factory=list)
    forecast_context: ForecastContext
    source_statuses: list[SourceStatus] = Field(default_factory=list)
    summary: str


class SailingConditionsRequest(BaseModel):
    area_id: str = "chicago_lakefront"
    response_profile: str = "compact_llm"


class SailingConditionsResponse(BaseModel):
    area_id: str
    headline: str
    risk_level: str
    alerts_first: dict[str, Any] = Field(default_factory=dict)
    marine_forecast_baseline: dict[str, Any] = Field(default_factory=dict)
    observation_summary: dict[str, Any] = Field(default_factory=dict)
    location_context: dict[str, Any] = Field(default_factory=dict)
    wind_assessment: dict[str, Any] = Field(default_factory=dict)
    wave_assessment: dict[str, Any] = Field(default_factory=dict)
    variations: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)
    source_statuses: list[SourceStatus] = Field(default_factory=list)
    llm_briefing_context: str
