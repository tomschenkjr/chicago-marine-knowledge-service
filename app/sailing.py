import re
from typing import Any

from app.lake_locations import buoy_location_context
from app.models import Observation

MPS_TO_KT = 1.94384449
M_TO_FT = 3.280839895


def build_sailing_conditions(
    area_id: str,
    marine_briefing: dict[str, Any],
    city_weather: list[Observation],
    city_water: list[Observation],
    dever: Observation | None,
    buoys: list[dict[str, Any]],
    source_statuses: list,
) -> dict[str, Any]:
    alerts = marine_briefing.get("active_alerts") or {}
    forecast = marine_briefing.get("nearshore_forecast") or {}
    raw_forecast = forecast.get("raw_forecast", "")
    wind_baseline = parse_wind_kt(raw_forecast)
    wave_baseline = parse_wave_ft(raw_forecast)

    wind_observations = collect_winds(city_weather, dever, buoys)
    wave_observations = collect_waves(city_water, buoys)
    wind_assessment = assess_wind(wind_observations, wind_baseline)
    wave_assessment = assess_waves(wave_observations, wave_baseline)
    variations = build_variations(wind_assessment, wave_assessment)
    cautions = build_cautions(alerts, city_water, wind_assessment, wave_assessment)
    risk_level = risk_from(alerts, wind_assessment, wave_assessment)
    headline = headline_from(risk_level, wind_assessment, wave_assessment, alerts)
    location_context = build_location_context(area_id, buoys)

    return {
        "area_id": area_id,
        "headline": headline,
        "risk_level": risk_level,
        "alerts_first": alerts,
        "marine_forecast_baseline": {
            "zone_id": forecast.get("zone_id"),
            "zone_name": forecast.get("zone_name"),
            "source": forecast.get("source"),
            "wind_kt": wind_baseline,
            "waves_ft": wave_baseline,
            "raw_forecast": raw_forecast,
        },
        "observation_summary": {
            "city_weather": [observation.model_dump(mode="json") for observation in city_weather],
            "city_water": [observation.model_dump(mode="json") for observation in city_water],
            "dever_crib": dever.model_dump(mode="json") if dever else None,
            "buoys": buoys,
        },
        "location_context": location_context,
        "wind_assessment": wind_assessment,
        "wave_assessment": wave_assessment,
        "variations": variations,
        "cautions": cautions,
        "source_statuses": source_statuses,
        "llm_briefing_context": build_llm_context(
            headline, alerts, wind_assessment, wave_assessment, variations, cautions, location_context
        ),
    }


def parse_wind_kt(text: str) -> dict[str, Any]:
    match = re.search(r"winds? [^.]*?(?:around )?(\d+)(?: to (\d+))? kt", text, re.IGNORECASE)
    if not match:
        return {"min": None, "max": None, "text": None}
    low = float(match.group(1))
    high = float(match.group(2) or match.group(1))
    return {"min": low, "max": high, "text": match.group(0)}


def parse_wave_ft(text: str) -> dict[str, Any]:
    match = re.search(r"waves? (\d+)(?: to (\d+))? ft", text, re.IGNORECASE)
    if not match:
        return {"min": None, "max": None, "text": None}
    low = float(match.group(1))
    high = float(match.group(2) or match.group(1))
    return {"min": low, "max": high, "text": match.group(0)}


def collect_winds(
    city_weather: list[Observation],
    dever: Observation | None,
    buoys: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    winds: list[dict[str, Any]] = []
    for observation in city_weather:
        speed = observation.values.get("wind_speed_mps")
        if speed is not None:
            winds.append({"name": observation.sensor_name, "wind_kt": speed * MPS_TO_KT, "source": observation.source})
    if dever and dever.values.get("wind_speed_mps") is not None:
        winds.append(
            {
                "name": dever.sensor_name,
                "wind_kt": dever.values["wind_speed_mps"] * MPS_TO_KT,
                "source": dever.source,
                "lake_area": "central offshore",
                "landmark": "Harrison-Dever Crib",
                "proximity": "about 3 miles offshore from downtown Chicago",
            }
        )
    for buoy in buoys:
        speed = buoy.get("values", {}).get("wind_speed_mps")
        if speed is not None:
            winds.append(
                {
                    "name": buoy_label(buoy),
                    "wind_kt": speed * MPS_TO_KT,
                    "source": "marine_mcp",
                    "station_id": buoy.get("station_id"),
                    **buoy_location_fields(buoy),
                }
            )
    return winds


def collect_waves(city_water: list[Observation], buoys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    waves: list[dict[str, Any]] = []
    for observation in city_water:
        height = observation.values.get("wave_height_m")
        if height is not None:
            waves.append({"name": observation.sensor_name, "wave_ft": height * M_TO_FT, "source": observation.source})
    for buoy in buoys:
        height = buoy.get("values", {}).get("wave_height_m")
        if height is not None:
            waves.append(
                {
                    "name": buoy_label(buoy),
                    "wave_ft": height * M_TO_FT,
                    "source": "marine_mcp",
                    "station_id": buoy.get("station_id"),
                    **buoy_location_fields(buoy),
                }
            )
    return waves


def assess_wind(observations: list[dict[str, Any]], baseline: dict[str, Any]) -> dict[str, Any]:
    if not observations:
        return {"category": "unknown", "observations": [], "comparison": "no_observations"}
    max_observed = max(observations, key=lambda item: item["wind_kt"])
    category = wind_category(max_observed["wind_kt"])
    forecast_max = baseline.get("max")
    comparison = "unknown"
    if forecast_max is not None:
        if max_observed["wind_kt"] > forecast_max + 3:
            comparison = "observed_above_forecast"
        elif max_observed["wind_kt"] < max((baseline.get("min") or forecast_max) - 3, 0):
            comparison = "observed_below_forecast"
        else:
            comparison = "observed_matches_forecast"
    return {"category": category, "max_observed": max_observed, "observations": observations, "comparison": comparison}


def assess_waves(observations: list[dict[str, Any]], baseline: dict[str, Any]) -> dict[str, Any]:
    if not observations:
        return {"category": "unknown", "observations": [], "comparison": "no_observations"}
    max_observed = max(observations, key=lambda item: item["wave_ft"])
    category = wave_category(max_observed["wave_ft"])
    forecast_max = baseline.get("max")
    comparison = "unknown"
    if forecast_max is not None:
        if max_observed["wave_ft"] > forecast_max + 1:
            comparison = "observed_above_forecast"
        elif max_observed["wave_ft"] < max((baseline.get("min") or forecast_max) - 1, 0):
            comparison = "observed_below_forecast"
        else:
            comparison = "observed_matches_forecast"
    return {"category": category, "max_observed": max_observed, "observations": observations, "comparison": comparison}


def wind_category(wind_kt: float) -> str:
    if wind_kt < 8:
        return "poor_light"
    if wind_kt < 10:
        return "marginal_light"
    if wind_kt <= 15:
        return "good"
    if wind_kt <= 20:
        return "exciting_fast"
    return "risky"


def wave_category(wave_ft: float) -> str:
    if wave_ft < 2:
        return "smooth"
    if wave_ft <= 5:
        return "rougher"
    return "dangerous"


def build_variations(wind: dict[str, Any], waves: dict[str, Any]) -> list[str]:
    variations: list[str] = []
    if wind.get("comparison") in {"observed_above_forecast", "observed_below_forecast"}:
        item = wind["max_observed"]
        variations.append(
            f"Wind {wind['comparison'].replace('_', ' ')} at {observation_location_label(item)}: "
            f"{item['wind_kt']:.1f} kt."
        )
    if waves.get("comparison") in {"observed_above_forecast", "observed_below_forecast"}:
        item = waves["max_observed"]
        variations.append(
            f"Waves {waves['comparison'].replace('_', ' ')} at {observation_location_label(item)}: "
            f"{item['wave_ft']:.1f} ft."
        )
    return variations


def build_cautions(alerts: dict[str, Any], city_water: list[Observation], wind: dict[str, Any], waves: dict[str, Any]) -> list[str]:
    cautions: list[str] = []
    if alerts.get("alerts"):
        cautions.append("Marine alerts or advisories are active; treat these as the primary planning constraint.")
    if wind.get("category") == "risky":
        cautions.append("Observed wind is over 20 kt at one or more sensors.")
    if waves.get("category") == "dangerous":
        cautions.append("Observed wave height is over 5 ft at one or more sensors.")
    for observation in city_water:
        if observation.quality_flags:
            cautions.append(f"{observation.sensor_name} water data has quality flags: {', '.join(observation.quality_flags)}.")
    return cautions


def risk_from(alerts: dict[str, Any], wind: dict[str, Any], waves: dict[str, Any]) -> str:
    if alerts.get("alerts") or wind.get("category") == "risky" or waves.get("category") == "dangerous":
        return "high"
    if wind.get("category") == "exciting_fast" or waves.get("category") == "rougher":
        return "moderate"
    return "low"


def headline_from(risk: str, wind: dict[str, Any], waves: dict[str, Any], alerts: dict[str, Any]) -> str:
    if alerts.get("alerts"):
        return "Active marine alerts are the primary sailing concern."
    return f"{risk.title()} risk sailing conditions: wind is {wind.get('category')} and waves are {waves.get('category')}."


def build_llm_context(
    headline: str,
    alerts: dict[str, Any],
    wind: dict[str, Any],
    waves: dict[str, Any],
    variations: list[str],
    cautions: list[str],
    location_context: dict[str, Any] | None = None,
) -> str:
    parts = [headline]
    if not alerts.get("alerts"):
        parts.append(alerts.get("message", "No active marine alerts reported."))
    if location_context:
        parts.append("Observation geography: " + location_context.get("summary", "Chicago lakefront observations."))
    parts.append(f"Wind assessment: {wind.get('category')} with comparison {wind.get('comparison')}.")
    parts.append(f"Wave assessment: {waves.get('category')} with comparison {waves.get('comparison')}.")
    if variations:
        parts.append("Callouts: " + " ".join(variations))
    if cautions:
        parts.append("Cautions: " + " ".join(cautions))
    return " ".join(parts)


def buoy_label(buoy: dict[str, Any]) -> str:
    return buoy.get("display_name") or buoy.get("location", {}).get("display_name") or f"Buoy {buoy.get('station_id')}"


def buoy_location_fields(buoy: dict[str, Any]) -> dict[str, Any]:
    location = buoy.get("location") or {}
    return {
        "lake_area": location.get("lake_area"),
        "landmark": location.get("landmark"),
        "proximity": location.get("proximity"),
        "relative_position": location.get("relative_position"),
        "narrative_location": location.get("narrative_location"),
    }


def observation_location_label(item: dict[str, Any]) -> str:
    narrative_location = item.get("narrative_location")
    if narrative_location:
        return f"{item['name']} ({narrative_location})"
    proximity = item.get("proximity")
    if proximity:
        return f"{item['name']} ({proximity})"
    return item["name"]


def build_location_context(area_id: str, buoys: list[dict[str, Any]]) -> dict[str, Any]:
    station_ids = [str(buoy.get("station_id")) for buoy in buoys if buoy.get("station_id")]
    context = buoy_location_context(station_ids or None)
    context["area_id"] = area_id
    context["summary"] = "; ".join(
        f"{buoy['display_name']} is {buoy['narrative_location']}" for buoy in context["buoys"]
    )
    return context
