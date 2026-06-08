from pydantic import BaseModel, HttpUrl


class Settings(BaseModel):
    city_base_url: HttpUrl = "https://data.cityofchicago.org/resource"
    city_locations_dataset: str = "g3ip-u8rb"
    city_weather_dataset: str = "k7hf-8y75"
    city_water_dataset: str = "qmqz-2xku"
    dever_recent_csv_url: HttpUrl = "https://www.glerl.noaa.gov/metdata/chi/tmp2/file3hr_m.csv"
    dever_page_url: HttpUrl = "https://www.glerl.noaa.gov/metdata/chi/"
    weather_mcp_health_url: HttpUrl = "https://weather-mcp.tomschenkjr.net/health"
    weather_mcp_sse_url: HttpUrl = "https://weather-mcp.tomschenkjr.net/sse"
    marine_mcp_sse_url: HttpUrl = "https://marine-mcp.tomschenkjr.net/sse"
    request_timeout_seconds: float = 12.0


settings = Settings()
