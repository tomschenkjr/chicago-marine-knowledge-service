import csv
from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo

import httpx

from app.models import Observation, SourceKind, SourceStatus
from app.settings import settings
from app.sources.quality import parse_float, quality_flags

CHICAGO_TZ = ZoneInfo("America/Chicago")


class DeverCribClient:
    async def status(self) -> SourceStatus:
        try:
            await self.latest_observation()
            return SourceStatus(
                source=SourceKind.DEVER_CRIB,
                name="NOAA GLERL Dever Crib / CHII2",
                endpoint=str(settings.dever_recent_csv_url),
                status="healthy",
            )
        except Exception as exc:  # pragma: no cover - exercised by integration checks
            return SourceStatus(
                source=SourceKind.DEVER_CRIB,
                name="NOAA GLERL Dever Crib / CHII2",
                endpoint=str(settings.dever_recent_csv_url),
                status="unavailable",
                detail=str(exc),
            )

    async def latest_observation(self) -> Observation | None:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(str(settings.dever_recent_csv_url))
            response.raise_for_status()

        reader = csv.DictReader(StringIO(response.text))
        first = next(reader, None)
        if first is None:
            return None

        observed_at = datetime.strptime(first["DateTime"], "%Y-%m-%d %H:%M").replace(tzinfo=CHICAGO_TZ)
        values = {
            "air_temperature_c": parse_float(first.get("Temp")),
            "dew_point_c": parse_float(first.get("DewPt")),
            "wind_speed_mps": parse_float(first.get("Speed")),
            "wind_gust_mps": parse_float(first.get("Gust")),
            "wind_direction_deg": parse_float(first.get("Dir")),
            "relative_humidity_percent": parse_float(first.get("RelHum")),
            "station_pressure": parse_float(first.get("StaPress")),
            "par": parse_float(first.get("PAR")),
        }
        return Observation(
            sensor_id="chii2_dever_crib",
            sensor_name="Dever Crib / CHII2",
            source=SourceKind.DEVER_CRIB,
            observed_at=observed_at,
            observed_at_label=first["DateTime"],
            values=values,
            units={
                "air_temperature_c": "C",
                "dew_point_c": "C",
                "wind_speed_mps": "m/s",
                "wind_gust_mps": "m/s",
                "wind_direction_deg": "degrees",
                "relative_humidity_percent": "%",
            },
            raw=first,
            quality_flags=quality_flags(first),
        )

