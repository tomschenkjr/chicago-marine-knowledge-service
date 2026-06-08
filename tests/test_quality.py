from app.sources.quality import parse_float, quality_flags


def test_parse_float_filters_known_bad_sentinels():
    assert parse_float("-100000") is None
    assert parse_float("-99999.992") is None
    assert parse_float("999.9") is None
    assert parse_float("-99") is None


def test_parse_float_accepts_regular_numbers():
    assert parse_float("18.9") == 18.9
    assert parse_float(0) == 0.0


def test_quality_flags_marks_bad_numeric_values():
    flags = quality_flags({"wave_height": "-99999.992", "wind_speed": "1.2"})
    assert flags == ["wave_height:bad_sentinel"]

