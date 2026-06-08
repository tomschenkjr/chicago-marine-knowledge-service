import pytest

from app.places import get_place, list_places


def test_list_places_includes_monroe_harbor():
    place_ids = {place.id for place in list_places()}
    assert "monroe_harbor" in place_ids


def test_monroe_harbor_relationships():
    place = get_place("monroe_harbor")
    assert place.weather_station_names == ["Oak Street Weather Station"]
    assert place.water_sensor_names == ["Ohio Street Beach"]
    assert place.use_dever_crib is True


def test_unknown_place_raises_clear_error():
    with pytest.raises(ValueError, match="Unknown place_id"):
        get_place("not_a_place")

