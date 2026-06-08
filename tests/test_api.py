from app.main import _build_summary


def test_summary_names_observation_source_counts():
    summary = _build_summary(
        place_name="Monroe Harbor",
        shoreline_weather_count=1,
        shoreline_water_count=1,
        offshore_count=1,
        weather_mcp_status="healthy",
    )

    assert "Monroe Harbor" in summary
    assert "1 shoreline weather" in summary
    assert "1 shoreline water" in summary
    assert "1 offshore Dever Crib" in summary
    assert "'healthy'" in summary

