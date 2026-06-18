#!/usr/bin/env python3
"""
Fetch detailed weather from Open-Meteo (free), log it, and generate a weather
infographic image using the OpenAI API.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import AuthenticationError, OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_LATITUDE = 18.5204
DEFAULT_LONGITUDE = 73.8567
DEFAULT_CITY = "Pune"

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "weather.log"
IMAGE_OUTPUT = Path(__file__).parent / "output" / "weather_infographic.png"

WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_description(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WMO_WEATHER_CODES.get(int(code), f"Weather code {code}")


def resolve_location(city: str | None, latitude: float, longitude: float) -> dict:
    """Resolve city name to coordinates via Open-Meteo geocoding, or use defaults."""
    if not city:
        return {
            "name": DEFAULT_CITY,
            "latitude": latitude,
            "longitude": longitude,
            "country": "",
            "timezone": "auto",
        }

    response = requests.get(
        OPEN_METEO_GEOCODING_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("results") or []

    if not results:
        print(f"City '{city}' not found. Using default coordinates.")
        return {
            "name": city,
            "latitude": latitude,
            "longitude": longitude,
            "country": "",
            "timezone": "auto",
        }

    place = results[0]
    return {
        "name": place.get("name", city),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "country": place.get("country", ""),
        "timezone": place.get("timezone", "auto"),
        "admin1": place.get("admin1", ""),
    }


def fetch_weather(
    city: str | None = None,
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
) -> dict:
    """
    Fetch detailed weather data from Open-Meteo (free, no API key required).
    Returns a structured dictionary with current, hourly, and daily forecasts.
    """
    location = resolve_location(city, latitude, longitude)

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": location["timezone"],
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "rain",
            "showers",
            "snowfall",
            "weather_code",
            "cloud_cover",
            "pressure_msl",
            "surface_pressure",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "is_day",
        ],
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "weather_code",
            "cloud_cover",
            "wind_speed_10m",
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_max",
            "apparent_temperature_min",
            "sunrise",
            "sunset",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "uv_index_max",
        ],
        "forecast_days": 7,
    }

    response = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    current = data.get("current", {})
    weather_code = current.get("weather_code")

    hourly = data.get("hourly", {})
    hourly_times = hourly.get("time", [])[:24]
    hourly_summary = [
        {
            "time": hourly_times[i],
            "temperature_c": hourly.get("temperature_2m", [None] * 24)[i],
            "humidity_pct": hourly.get("relative_humidity_2m", [None] * 24)[i],
            "precipitation_probability_pct": hourly.get("precipitation_probability", [None] * 24)[i],
            "precipitation_mm": hourly.get("precipitation", [None] * 24)[i],
            "weather": weather_description(hourly.get("weather_code", [None] * 24)[i]),
            "cloud_cover_pct": hourly.get("cloud_cover", [None] * 24)[i],
            "wind_speed_kmh": hourly.get("wind_speed_10m", [None] * 24)[i],
        }
        for i in range(min(24, len(hourly_times)))
    ]

    daily = data.get("daily", {})
    daily_times = daily.get("time", [])
    daily_summary = [
        {
            "date": daily_times[i],
            "weather": weather_description(daily.get("weather_code", [None] * len(daily_times))[i]),
            "temp_max_c": daily.get("temperature_2m_max", [None] * len(daily_times))[i],
            "temp_min_c": daily.get("temperature_2m_min", [None] * len(daily_times))[i],
            "feels_like_max_c": daily.get("apparent_temperature_max", [None] * len(daily_times))[i],
            "feels_like_min_c": daily.get("apparent_temperature_min", [None] * len(daily_times))[i],
            "sunrise": daily.get("sunrise", [None] * len(daily_times))[i],
            "sunset": daily.get("sunset", [None] * len(daily_times))[i],
            "precipitation_mm": daily.get("precipitation_sum", [None] * len(daily_times))[i],
            "precipitation_probability_max_pct": daily.get(
                "precipitation_probability_max", [None] * len(daily_times)
            )[i],
            "max_wind_kmh": daily.get("wind_speed_10m_max", [None] * len(daily_times))[i],
            "uv_index_max": daily.get("uv_index_max", [None] * len(daily_times))[i],
        }
        for i in range(len(daily_times))
    ]

    wind_dir = current.get("wind_direction_10m")
    wind_direction_label = f"{wind_dir}°" if wind_dir is not None else "N/A"

    location_label = location["name"]
    if location.get("admin1"):
        location_label += f", {location['admin1']}"
    if location.get("country"):
        location_label += f", {location['country']}"

    weather_report = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Open-Meteo (https://open-meteo.com)",
        "location": {
            "name": location_label,
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timezone": data.get("timezone", location["timezone"]),
            "elevation_m": data.get("elevation"),
        },
        "current": {
            "time": current.get("time"),
            "conditions": weather_description(weather_code),
            "weather_code": weather_code,
            "is_day": bool(current.get("is_day")),
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "rain_mm": current.get("rain"),
            "showers_mm": current.get("showers"),
            "snowfall_cm": current.get("snowfall"),
            "cloud_cover_pct": current.get("cloud_cover"),
            "pressure_msl_hpa": current.get("pressure_msl"),
            "surface_pressure_hpa": current.get("surface_pressure"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_direction": wind_direction_label,
            "wind_gusts_kmh": current.get("wind_gusts_10m"),
        },
        "hourly_next_24h": hourly_summary,
        "daily_7day_forecast": daily_summary,
    }

    return weather_report


def save_weather_log(weather_data: dict, log_path: Path = LOG_FILE) -> Path:
    """Append formatted weather data to a log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    divider = "=" * 72
    human_lines = [
        divider,
        f"Weather log entry — {weather_data['fetched_at_utc']}",
        divider,
        f"Location: {weather_data['location']['name']}",
        f"Coordinates: {weather_data['location']['latitude']}, {weather_data['location']['longitude']}",
        f"Timezone: {weather_data['location']['timezone']}",
        "",
        "--- CURRENT CONDITIONS ---",
        f"  Time: {weather_data['current']['time']}",
        f"  Conditions: {weather_data['current']['conditions']}",
        f"  Temperature: {weather_data['current']['temperature_c']} °C",
        f"  Feels like: {weather_data['current']['feels_like_c']} °C",
        f"  Humidity: {weather_data['current']['humidity_pct']} %",
        f"  Cloud cover: {weather_data['current']['cloud_cover_pct']} %",
        f"  Precipitation: {weather_data['current']['precipitation_mm']} mm",
        f"  Wind: {weather_data['current']['wind_speed_kmh']} km/h {weather_data['current']['wind_direction']}",
        f"  Wind gusts: {weather_data['current']['wind_gusts_kmh']} km/h",
        f"  Pressure: {weather_data['current']['pressure_msl_hpa']} hPa",
        "",
        "--- 7-DAY FORECAST ---",
    ]

    for day in weather_data["daily_7day_forecast"]:
        human_lines.append(
            f"  {day['date']}: {day['weather']} | "
            f"{day['temp_min_c']}–{day['temp_max_c']} °C | "
            f"Rain {day['precipitation_mm']} mm ({day['precipitation_probability_max_pct']}%) | "
            f"UV {day['uv_index_max']}"
        )

    human_lines.extend(["", "--- RAW JSON ---", json.dumps(weather_data, indent=2), ""])

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write("\n".join(human_lines) + "\n")

    print(f"Weather data logged to: {log_path}")
    return log_path


def get_openai_api_key() -> str | None:
    """Return a trimmed OpenAI API key from the environment, if set."""
    key = os.environ.get("OPENAI_API_KEY")
    return key.strip() if key else None


def _build_image_prompt_locally(weather_data: dict) -> str:
    """Build a DALL-E prompt from weather data without calling the chat API."""
    loc = weather_data["location"]["name"]
    cur = weather_data["current"]
    forecast_lines = ", ".join(
        f"{day['date']}: {day['weather']} {day['temp_min_c']}-{day['temp_max_c']}C"
        for day in weather_data["daily_7day_forecast"][:7]
    )
    return (
        f"A modern weather infographic poster for {loc}. "
        f"Current conditions: {cur['conditions']}, {cur['temperature_c']}C "
        f"(feels like {cur['feels_like_c']}C), humidity {cur['humidity_pct']}%, "
        f"wind {cur['wind_speed_kmh']} km/h, cloud cover {cur['cloud_cover_pct']}%. "
        f"Include a 7-day forecast strip showing: {forecast_lines}. "
        f"Clean dashboard layout, readable typography, weather icons, atmospheric sky "
        f"matching {cur['conditions'].lower()}, professional mobile-app style design."
    )


def _build_image_prompt_with_llm(client: OpenAI, weather_data: dict) -> str:
    """Use an LLM to craft a rich DALL-E prompt from structured weather data."""
    compact = {
        "location": weather_data["location"]["name"],
        "current": weather_data["current"],
        "daily_forecast": weather_data["daily_7day_forecast"],
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write concise, vivid image-generation prompts for weather infographics. "
                    "Output ONLY the prompt text, no quotes or explanation. "
                    "The image should be a beautiful, modern weather dashboard poster with icons, "
                    "temperature readings, 7-day mini forecast strip, location name, and atmospheric "
                    "illustration matching the conditions. Use clean typography and readable layout."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create a DALL-E image prompt for this weather data:\n"
                    f"{json.dumps(compact, indent=2)}"
                ),
            },
        ],
        temperature=0.7,
        max_tokens=400,
    )

    return response.choices[0].message.content.strip()


def generate_weather_image(
    weather_data: dict,
    output_path: Path = IMAGE_OUTPUT,
    api_key: str | None = None,
) -> Path | None:
    """
    Use OpenAI (LLM + image model) to generate a weather infographic from log data.
    Requires OPENAI_API_KEY environment variable or api_key argument.
    """
    key = (api_key or get_openai_api_key() or "").strip()
    if not key:
        print("Skipping image generation — OPENAI_API_KEY is not set in .env")
        return None

    if not key.startswith("sk-"):
        print("Skipping image generation — OPENAI_API_KEY must start with 'sk-'")
        return None

    client = OpenAI(api_key=key)

    try:
        image_prompt = _build_image_prompt_with_llm(client, weather_data)
    except AuthenticationError:
        print("\nOpenAI rejected your API key (401 Unauthorized).")
        print("The weather log was saved, but image generation was skipped.")
        print("\nTo fix this:")
        print("  1. Go to https://platform.openai.com/account/api-keys")
        print("  2. Create a new secret key")
        print("  3. Update OPENAI_API_KEY in your .env file (no quotes, one line)")
        print("  4. Run: python weather_image.py")
        print("\nIf you shared the old key anywhere, revoke it in the OpenAI dashboard.")
        return None
    except Exception as exc:
        print(f"LLM prompt step failed ({exc}). Using local prompt instead.")
        image_prompt = _build_image_prompt_locally(weather_data)

    print("Generating weather image with OpenAI...")
    print(f"Image prompt preview: {image_prompt[:120]}...")

    try:
        image_response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
    except AuthenticationError:
        print("\nOpenAI rejected your API key during image generation (401 Unauthorized).")
        print("Create a new key at https://platform.openai.com/account/api-keys")
        print("and update your .env file.")
        return None

    image_url = image_response.data[0].url
    if not image_url:
        raise RuntimeError("OpenAI did not return an image URL.")

    image_bytes = requests.get(image_url, timeout=60).content
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)

    print(f"Weather image saved to: {output_path}")
    return output_path


def print_weather_summary(weather_data: dict) -> None:
    """Print a readable weather summary to the console."""
    loc = weather_data["location"]["name"]
    cur = weather_data["current"]
    print(f"\n{'=' * 50}")
    print(f"  WEATHER REPORT — {loc}")
    print(f"{'=' * 50}")
    print(f"  {cur['conditions']}")
    print(f"  Temperature:  {cur['temperature_c']} °C  (feels like {cur['feels_like_c']} °C)")
    print(f"  Humidity:     {cur['humidity_pct']} %")
    print(f"  Wind:         {cur['wind_speed_kmh']} km/h {cur['wind_direction']}")
    print(f"  Cloud cover:  {cur['cloud_cover_pct']} %")
    print(f"  Pressure:     {cur['pressure_msl_hpa']} hPa")
    print(f"\n  7-Day Forecast:")
    for day in weather_data["daily_7day_forecast"]:
        print(
            f"    {day['date']}: {day['weather']:20s} "
            f"{day['temp_min_c']:>4}–{day['temp_max_c']:<4} °C"
        )
    print(f"{'=' * 50}\n")


def main() -> None:
    city = os.environ.get("WEATHER_CITY", DEFAULT_CITY)
    if len(sys.argv) > 1:
        city = sys.argv[1]

    lat = float(os.environ.get("WEATHER_LAT", DEFAULT_LATITUDE))
    lon = float(os.environ.get("WEATHER_LON", DEFAULT_LONGITUDE))

    print("Fetching weather from Open-Meteo...")
    weather_data = fetch_weather(city=city, latitude=lat, longitude=lon)

    print_weather_summary(weather_data)
    save_weather_log(weather_data)

    if get_openai_api_key():
        generate_weather_image(weather_data)
    else:
        print(
            "Skipping image generation — set OPENAI_API_KEY in .env to create a weather infographic."
        )


if __name__ == "__main__":
    main()
