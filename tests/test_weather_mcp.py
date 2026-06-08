from app.sources.weather_mcp import _json_text_to_dict


def test_json_text_to_dict_parses_object_text():
    assert _json_text_to_dict('{"alerts": []}') == {"alerts": []}


def test_json_text_to_dict_preserves_non_json_text():
    assert _json_text_to_dict("plain forecast text") == {"text": "plain forecast text"}

