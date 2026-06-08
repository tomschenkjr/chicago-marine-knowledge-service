from app.models import Coordinates, Place


PLACES: dict[str, Place] = {
    "monroe_harbor": Place(
        id="monroe_harbor",
        name="Monroe Harbor",
        coordinates=Coordinates(latitude=41.8809, longitude=-87.6130),
        description="Downtown Chicago harbor with exposure to nearshore and offshore lake conditions.",
        weather_station_names=["Oak Street Weather Station"],
        water_sensor_names=["Ohio Street Beach"],
        use_dever_crib=True,
    ),
    "oak_street_beach": Place(
        id="oak_street_beach",
        name="Oak Street Beach",
        coordinates=Coordinates(latitude=41.9020, longitude=-87.6228),
        description="Nearshore beach location on Chicago's central lakefront.",
        weather_station_names=["Oak Street Weather Station"],
        water_sensor_names=["Ohio Street Beach"],
        use_dever_crib=True,
    ),
    "foster_beach": Place(
        id="foster_beach",
        name="Foster Beach",
        coordinates=Coordinates(latitude=41.9765, longitude=-87.6475),
        description="North lakefront beach location near the Foster Weather Station.",
        weather_station_names=["Foster Weather Station"],
        water_sensor_names=["Osterman Beach"],
        use_dever_crib=True,
    ),
    "63rd_street_beach": Place(
        id="63rd_street_beach",
        name="63rd Street Beach",
        coordinates=Coordinates(latitude=41.7810, longitude=-87.5726),
        description="South lakefront beach location with colocated weather and water sensors.",
        weather_station_names=["63rd Street Weather Station"],
        water_sensor_names=["63rd Street Beach"],
        use_dever_crib=True,
    ),
}


def list_places() -> list[Place]:
    return list(PLACES.values())


def get_place(place_id: str) -> Place:
    try:
        return PLACES[place_id]
    except KeyError as exc:
        valid = ", ".join(sorted(PLACES))
        raise ValueError(f"Unknown place_id '{place_id}'. Valid place ids: {valid}") from exc

