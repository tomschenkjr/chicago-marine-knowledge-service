from app.lake_locations import DEFAULT_BUOY_STATIONS, buoy_location
from app.sources.marine_mcp import _parse_buoy_text


def test_default_buoy_stations_are_chicago_relevant():
    assert "45198" in DEFAULT_BUOY_STATIONS
    assert "45174" in DEFAULT_BUOY_STATIONS
    assert "45013" not in DEFAULT_BUOY_STATIONS
    assert "45012" not in DEFAULT_BUOY_STATIONS
    assert "45024" not in DEFAULT_BUOY_STATIONS


def test_buoy_location_uses_landmark_context():
    location = buoy_location("45198")

    assert location["display_name"] == "Chicago Buoy"
    assert location["lake_area"] == "central lakefront"
    assert "Navy Pier" in location["landmark"]
    assert "downtown Chicago" in location["narrative_location"]


def test_parse_buoy_text_enriches_station_location():
    text = "#YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS\n"
    text += "2026 06 07 18 00 250 6.0 7.0 0.5 3.0 2.7 250 1012.0 18.0 12.0 10.0 MM\n"

    parsed = _parse_buoy_text("45198", text)

    assert parsed["display_name"] == "Chicago Buoy"
    assert parsed["location"]["proximity"] == "off downtown Chicago"
    assert parsed["values"]["wind_speed_mps"] == 6.0
