from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class BuoyLocation:
    station_id: str
    display_name: str
    lake_area: str
    proximity: str
    landmark: str
    relative_position: str
    narrative_location: str
    active_for_sailing_summary: bool = True


BUOY_LOCATIONS: dict[str, BuoyLocation] = {
    "45174": BuoyLocation(
        station_id="45174",
        display_name="Wilmette Buoy",
        lake_area="north shore",
        proximity="near Wilmette",
        landmark="Wilmette Harbor",
        relative_position="north of the Chicago lakefront",
        narrative_location="near Wilmette Harbor on the north shore",
    ),
    "45198": BuoyLocation(
        station_id="45198",
        display_name="Chicago Buoy",
        lake_area="central lakefront",
        proximity="off downtown Chicago",
        landmark="Navy Pier / Monroe Harbor",
        relative_position="central Chicago lakefront",
        narrative_location="off downtown Chicago near Navy Pier and Monroe Harbor",
    ),
    "45013": BuoyLocation(
        station_id="45013",
        display_name="Atwater Park Buoy",
        lake_area="Milwaukee nearshore",
        proximity="near Atwater Park",
        landmark="Milwaukee shoreline",
        relative_position="well north of Chicago",
        narrative_location="near Atwater Park along the Milwaukee shoreline",
    ),
    "45007": BuoyLocation(
        station_id="45007",
        display_name="South Lake Michigan Buoy",
        lake_area="south Lake Michigan open water",
        proximity="open water east-southeast of Milwaukee",
        landmark="open south Lake Michigan",
        relative_position="north and offshore from Chicago",
        narrative_location="in open south Lake Michigan north and offshore from Chicago",
    ),
    "45015": BuoyLocation(
        station_id="45015",
        display_name="Calumet Beach Buoy",
        lake_area="south lakefront",
        proximity="near Calumet Beach",
        landmark="Calumet Harbor",
        relative_position="south Chicago lakefront",
        narrative_location="near Calumet Beach and Calumet Harbor on the south lakefront",
        active_for_sailing_summary=False,
    ),
}


DEFAULT_BUOY_STATIONS = ["45174", "45198"]


def buoy_location(station_id: str) -> dict[str, Any]:
    location = BUOY_LOCATIONS.get(station_id)
    if location is None:
        return {
            "station_id": station_id,
            "display_name": f"Buoy {station_id}",
            "lake_area": "unknown",
            "proximity": "unknown lake location",
            "landmark": "unknown",
            "relative_position": "unknown",
            "narrative_location": "unknown lake location",
            "active_for_sailing_summary": True,
        }
    return asdict(location)


def enrich_buoy_observation(observation: dict[str, Any]) -> dict[str, Any]:
    station_id = str(observation.get("station_id", ""))
    location = buoy_location(station_id)
    return {
        **observation,
        "display_name": location["display_name"],
        "location": location,
    }


def buoy_location_context(station_ids: Iterable[str] | None = None) -> dict[str, Any]:
    stations = list(station_ids or DEFAULT_BUOY_STATIONS)
    return {
        "scale": "Chicago lakefront and south Lake Michigan",
        "usage_note": (
            "Use lake_area, proximity, and landmark for narrative location; keep station_id "
            "for source provenance."
        ),
        "buoys": [buoy_location(station_id) for station_id in stations],
    }
