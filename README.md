# InstaAutomation — Weather Image Generator

A Python script that fetches detailed weather data from [Open-Meteo](https://open-meteo.com) (free, no API key required), logs it to a file, and optionally generates a weather infographic image using the OpenAI API.

Default location: **Pune, Maharashtra, India**.

## Features

- **Free weather data** — current conditions, 24-hour hourly forecast, and 7-day daily forecast
- **Automatic geocoding** — pass a city name or use latitude/longitude coordinates
- **Persistent logging** — each run appends a human-readable report and full JSON to `logs/weather.log`
- **AI weather infographic** — uses GPT-4o-mini to craft an image prompt, then DALL-E 3 to generate a poster-style dashboard

## How it works

```
Open-Meteo API  →  fetch_weather()  →  save_weather_log()
                                              ↓
                                    generate_weather_image()
                                              ↓
                              GPT-4o-mini (image prompt)
                                              ↓
                              DALL-E 3 (1024×1024 PNG)
                                              ↓
                              output/weather_infographic.png
```

## Requirements

- Python 3.10+
- An [OpenAI API key](https://platform.openai.com/account/api-keys) with billing enabled (only needed for image generation)

## Installation

```powershell
git clone <your-repo-url>
cd InstaAutomation
pip install -r requirements.txt
```

Copy the example environment file and add your OpenAI key:

```powershell
copy .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
```

> **Never commit `.env`** — it is listed in `.gitignore`. Do not share API keys in chat, commits, or screenshots.

## Usage

### Default (Pune, India)

```powershell
python weather_image.py
```

### Another city

```powershell
python weather_image.py Mumbai
python weather_image.py "New Delhi"
```

### Custom location via environment variables

```powershell
$env:WEATHER_CITY = "London"
$env:WEATHER_LAT = "51.5074"
$env:WEATHER_LON = "-0.1278"
python weather_image.py
```

Or set these permanently in `.env`:

```env
WEATHER_CITY=London
WEATHER_LAT=51.5074
WEATHER_LON=-0.1278
```

### Weather only (no OpenAI key)

If `OPENAI_API_KEY` is not set, the script still fetches weather and writes the log. Image generation is skipped.

## Output

| Path | Description |
|------|-------------|
| `logs/weather.log` | Append-only log with current conditions, 7-day forecast, and raw JSON |
| `output/weather_infographic.png` | Generated weather poster (requires valid OpenAI key) |

## Project structure

```
InstaAutomation/
├── weather_image.py      # Main script
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── .env                  # Your secrets (not committed)
├── logs/
│   └── weather.log       # Weather data log
└── output/
    └── weather_infographic.png
```

## Key functions

| Function | Purpose |
|----------|---------|
| `fetch_weather()` | Fetches detailed weather from Open-Meteo |
| `save_weather_log()` | Appends formatted data to `logs/weather.log` |
| `generate_weather_image()` | Builds a prompt via LLM and generates a DALL-E 3 image |
| `print_weather_summary()` | Prints a readable report to the terminal |

## Weather data included

**Current:** temperature, feels-like, humidity, precipitation, cloud cover, pressure, wind speed/direction/gusts, weather conditions

**Hourly (next 24 h):** temperature, humidity, precipitation probability, cloud cover, wind

**Daily (7 days):** min/max temperature, sunrise/sunset, precipitation, UV index, weather conditions

## Troubleshooting

### `401 Unauthorized` / invalid API key

OpenAI rejected the key in your `.env` file. The weather log is still saved; only image generation fails.

1. Create a new key at [platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)
2. Revoke any key that was exposed
3. Update `.env` — one line, no quotes:
   ```
   OPENAI_API_KEY=sk-your-new-key
   ```
4. Run again: `python weather_image.py`

### Image generation requires billing

DALL-E 3 is a paid OpenAI API feature. Ensure your account has billing set up and available credits.

### City not found

If geocoding fails, the script falls back to the default coordinates (Pune). Override with `WEATHER_LAT` and `WEATHER_LON`.

## Dependencies

- [requests](https://pypi.org/project/requests/) — HTTP client for Open-Meteo
- [openai](https://pypi.org/project/openai/) — OpenAI API (GPT-4o-mini + DALL-E 3)
- [python-dotenv](https://pypi.org/project/python-dotenv/) — loads `.env` at startup

## License

Use and modify freely for personal or automation projects.
