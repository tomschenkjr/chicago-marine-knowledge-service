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


def _conditions_with_briefing(marine_briefing):
    return build_sailing_conditions(
        area_id="chicago_lakefront",
        marine_briefing=marine_briefing,
        city_weather=[],
        city_water=[],
        dever=None,
        buoys=[{"station_id": "45198", "values": {"wind_speed_mps": 2.0, "wave_height_m": 0.2}}],
        source_statuses=[],
    )


def test_unavailable_marine_source_is_not_reported_as_no_alerts():
    # _safe_dict returns {} when the NOAA Marine MCP forecast/alerts call fails.
    for briefing in ({}, {"active_alerts": {"error": "Could not fetch alerts"}, "nearshore_forecast": {}}):
        response = _conditions_with_briefing(briefing)

        assert "No active marine alerts" not in response["llm_briefing_context"]
        assert "alert status is unknown" in response["llm_briefing_context"]
        assert response["headline"].startswith("Marine alert status unknown.")
        assert response["risk_level"] != "low"
        assert "UNKNOWN" in response["cautions"][0]


def test_known_empty_alerts_still_report_no_alerts():
    response = _conditions_with_briefing(
        {"active_alerts": {"zone_id": "LMZ741", "alerts": [], "message": "No active marine alerts."}}
    )

    assert "No active marine alerts." in response["llm_briefing_context"]
    assert response["risk_level"] == "low"
    assert not any("UNKNOWN" in caution for caution in response["cautions"])
