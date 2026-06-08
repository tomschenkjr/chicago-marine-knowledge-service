from app.sailing import build_sailing_conditions


def test_sailing_variations_use_buoy_landmark_context():
    response = build_sailing_conditions(
        area_id="chicago_lakefront",
        marine_briefing={
            "active_alerts": {"alerts": [], "message": "No active marine alerts reported."},
            "nearshore_forecast": {"raw_forecast": "Southwest winds 10 to 15 kt. Waves 1 to 2 ft."},
        },
        city_weather=[],
        city_water=[],
        dever=None,
        buoys=[
            {
                "station_id": "45198",
                "display_name": "Chicago Buoy",
                "location": {
                    "lake_area": "central lakefront",
                    "proximity": "off downtown Chicago",
                    "landmark": "Navy Pier / Monroe Harbor",
                    "relative_position": "central Chicago lakefront",
                    "narrative_location": "off downtown Chicago near Navy Pier and Monroe Harbor",
                },
                "values": {"wind_speed_mps": 10.5, "wave_height_m": 0.5},
            }
        ],
        source_statuses=[],
    )

    assert "Chicago Buoy (off downtown Chicago near Navy Pier and Monroe Harbor)" in response["variations"][0]
    assert response["location_context"]["buoys"][0]["lake_area"] == "central lakefront"
    assert "Observation geography:" in response["llm_briefing_context"]
