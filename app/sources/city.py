from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.models import Coordinates, Observation, Sensor, SourceKind, SourceStatus
from app.settings import settings
from app.sources.quality import parse_float, quality_flags


class CitySocrataClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def _get_json(self, dataset: str, query: str = "") -> list[dict[str, Any]]:
        url = f"{settings.city_base_url}/{dataset}.json{query}"
        if self._client is not None:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.json()

        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def status(self) -> SourceStatus:
        try:
            await self._get_json(settings.city_locations_dataset, "?$limit=1")
            return SourceStatus(
                source=SourceKind.CITY_SENSOR_LOCATIONS,
                name="City of Chicago sensor locations",
                endpoint=str(settings.city_base_url),
                status="healthy",
            )
        except Exception as exc:  # pragma: no cover - exercised by integration checks
            return SourceStatus(
                source=SourceKind.CITY_SENSOR_LOCATIONS,
                name="City of Chicago sensor locations",
                endpoint=str(settings.city_base_url),
                status="unavailable",
                detail=str(exc),
            )

    async def sensors(self) -> list[Sensor]:
        records = await self._get_json(settings.city_locations_dataset, "?$limit=5000")
        sensors: list[Sensor] = []
        for record in records:
            name = record["sensor_name"]
            sensor_type = record["sensor_type"]
            sensors.append(
                Sensor(
                    id=_slug(name),
                    name=name,
                    source=SourceKind.CITY_SENSOR_LOCATIONS,
                    sensor_type=sensor_type,
                    coordinates=Coordinates(
                        latitude=float(record["latitude"]),
                        longitude=float(record["longitude"]),
                    ),
                    metadata={"raw": record},
                )
            )
        return sensors

    async def latest_weather_observation(self, station_name: str) -> Observation | None:
        query = (
            f"?station_name={quote(station_name)}"
            "&$order=measurement_timestamp%20DESC"
            "&$limit=1"
        )
        records = await self._get_json(settings.city_weather_dataset, query)
        if not records:
            return None
        record = records[0]
        values = {
            "air_temperature_c": parse_float(record.get("air_temperature")),
            "wet_bulb_temperature_c": parse_float(record.get("wet_bulb_temperature")),
            "relative_humidity_percent": parse_float(record.get("humidity")),
            "rain_intensity_mm_per_hr": parse_float(record.get("rain_intensity")),
            "interval_rain_mm": parse_float(record.get("interval_rain")),
            "total_rain_mm": parse_float(record.get("total_rain")),
            "precipitation_type_code": parse_float(record.get("precipitation_type")),
            "wind_direction_deg": parse_float(record.get("wind_direction")),
            "wind_speed_mps": parse_float(record.get("wind_speed")),
            "maximum_wind_speed_mps": parse_float(record.get("maximum_wind_speed")),
            "barometric_pressure_hpa": parse_float(record.get("barometric_pressure")),
            "solar_radiation_w_m2": parse_float(record.get("solar_radiation")),
            "heading_deg": parse_float(record.get("heading")),
            "battery_life_v": parse_float(record.get("battery_life")),
        }
        return Observation(
            sensor_id=_slug(station_name),
            sensor_name=station_name,
            source=SourceKind.CITY_BEACH_WEATHER,
            observed_at=_parse_socrata_datetime(record.get("measurement_timestamp")),
            observed_at_label=record.get("measurement_timestamp_label"),
            values=values,
            units={
                "air_temperature_c": "C",
                "wind_speed_mps": "m/s",
                "maximum_wind_speed_mps": "m/s",
                "barometric_pressure_hpa": "hPa",
            },
            raw=record,
            quality_flags=quality_flags(record),
        )

    async def latest_weather_observations(self) -> list[Observation]:
        sensors = await self.sensors()
        observations: list[Observation] = []
        for sensor in sensors:
            if sensor.sensor_type != "Weather":
                continue
            observation = await self.latest_weather_observation(sensor.name)
            if observation is not None:
                observations.append(observation)
        return observations

    async def latest_water_observation(self, beach_name: str) -> Observation | None:
        where = quote(
            (
                f"beach_name = '{_escape_soql(beach_name)}' AND "
                "("
                "water_temperature IS NOT NULL OR "
                "turbidity IS NOT NULL OR "
                "transducer_depth IS NOT NULL OR "
                "wave_height IS NOT NULL OR "
                "wave_period IS NOT NULL OR "
                "battery_life IS NOT NULL"
                ")"
            ),
            safe="",
        )
        query = (
            f"?$where={where}"
            "&$order=measurement_timestamp%20DESC"
            "&$limit=1"
        )
        records = await self._get_json(settings.city_water_dataset, query)
        if not records:
            return None
        record = records[0]
        values = {
            "water_temperature_c": parse_float(record.get("water_temperature")),
            "turbidity_ntu": parse_float(record.get("turbidity")),
            "transducer_depth_m": parse_float(record.get("transducer_depth")),
            "wave_height_m": parse_float(record.get("wave_height")),
            "wave_period_s": parse_float(record.get("wave_period")),
            "battery_life_v": parse_float(record.get("battery_life")),
        }
        return Observation(
            sensor_id=_slug(beach_name),
            sensor_name=beach_name,
            source=SourceKind.CITY_BEACH_WATER,
            observed_at=_parse_socrata_datetime(record.get("measurement_timestamp")),
            observed_at_label=record.get("measurement_timestamp_label"),
            values=values,
            units={
                "water_temperature_c": "C",
                "turbidity_ntu": "NTU",
                "wave_height_m": "m",
                "wave_period_s": "s",
            },
            raw=record,
            quality_flags=quality_flags(record),
        )

    async def latest_water_observations(self) -> list[Observation]:
        sensors = await self.sensors()
        observations: list[Observation] = []
        for sensor in sensors:
            if sensor.sensor_type != "Water":
                continue
            observation = await self.latest_water_observation(sensor.name)
            if observation is not None:
                observations.append(observation)
        return observations


def _parse_socrata_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _slug(value: str) -> str:
    return (
        value.lower()
        .replace(" - ", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("__", "_")
    )


def _escape_soql(value: str) -> str:
    return value.replace("'", "''")
