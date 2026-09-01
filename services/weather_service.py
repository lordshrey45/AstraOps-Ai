"""
Weather Service — Open-Meteo API integration for Wari Mitra.

Fetches current weather and 7-day forecast from the free
Open-Meteo API using latitude/longitude coordinates.

API: https://api.open-meteo.com/v1/forecast
No API key required.

IMPORTANT: Weather data attribution — "Weather data by Open-Meteo"
"""

import requests


# Open-Meteo API base URL
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather Code descriptions
WMO_CODES = {
    0: ("Clear sky", "bi-sun-fill", "clear"),
    1: ("Mainly clear", "bi-sun-fill", "clear"),
    2: ("Partly cloudy", "bi-cloud-sun-fill", "cloudy"),
    3: ("Overcast", "bi-clouds-fill", "cloudy"),
    45: ("Fog", "bi-cloud-fog2-fill", "fog"),
    48: ("Depositing rime fog", "bi-cloud-fog2-fill", "fog"),
    51: ("Light drizzle", "bi-cloud-drizzle-fill", "rain"),
    53: ("Moderate drizzle", "bi-cloud-drizzle-fill", "rain"),
    55: ("Dense drizzle", "bi-cloud-drizzle-fill", "rain"),
    56: ("Light freezing drizzle", "bi-cloud-sleet-fill", "rain"),
    57: ("Dense freezing drizzle", "bi-cloud-sleet-fill", "rain"),
    61: ("Slight rain", "bi-cloud-rain-fill", "rain"),
    63: ("Moderate rain", "bi-cloud-rain-fill", "rain"),
    65: ("Heavy rain", "bi-cloud-rain-heavy-fill", "rain"),
    66: ("Light freezing rain", "bi-cloud-sleet-fill", "rain"),
    67: ("Heavy freezing rain", "bi-cloud-sleet-fill", "rain"),
    71: ("Slight snowfall", "bi-cloud-snow-fill", "snow"),
    73: ("Moderate snowfall", "bi-cloud-snow-fill", "snow"),
    75: ("Heavy snowfall", "bi-cloud-snow-fill", "snow"),
    77: ("Snow grains", "bi-cloud-snow-fill", "snow"),
    80: ("Slight rain showers", "bi-cloud-rain-fill", "rain"),
    81: ("Moderate rain showers", "bi-cloud-rain-fill", "rain"),
    82: ("Violent rain showers", "bi-cloud-rain-heavy-fill", "rain"),
    85: ("Slight snow showers", "bi-cloud-snow-fill", "snow"),
    86: ("Heavy snow showers", "bi-cloud-snow-fill", "snow"),
    95: ("Thunderstorm", "bi-cloud-lightning-rain-fill", "storm"),
    96: ("Thunderstorm with slight hail", "bi-cloud-lightning-rain-fill", "storm"),
    99: ("Thunderstorm with heavy hail", "bi-cloud-lightning-rain-fill", "storm"),
}


def _decode_weather_code(code):
    """Convert WMO weather code to description, icon, and category."""
    info = WMO_CODES.get(code, ("Unknown", "bi-question-circle", "unknown"))
    return {
        "description": info[0],
        "icon": info[1],
        "category": info[2]
    }


def _generate_alerts(current, daily):
    """
    Generate simple rule-based weather advisories.
    These are NOT official warnings — just helpful tips.
    """
    alerts = []

    temp = current.get("temperature_2m", 0)
    precip = current.get("precipitation", 0)
    wind = current.get("wind_speed_10m", 0)
    humidity = current.get("relative_humidity_2m", 0)

    if temp >= 38:
        alerts.append({
            "type": "danger",
            "icon": "bi-thermometer-sun",
            "message": "Extreme heat alert — stay hydrated, avoid walking during peak afternoon hours."
        })
    elif temp >= 33:
        alerts.append({
            "type": "warning",
            "icon": "bi-thermometer-half",
            "message": "High heat — drink plenty of water and rest in shade regularly."
        })

    if precip > 5 or (daily and daily.get("precipitation_probability_max", [0])[0] > 60):
        alerts.append({
            "type": "warning",
            "icon": "bi-umbrella-fill",
            "message": "Rain is expected — carry rain protection and waterproof your belongings."
        })

    if wind > 40:
        alerts.append({
            "type": "warning",
            "icon": "bi-wind",
            "message": "Strong winds expected — secure loose items and take care while walking."
        })
    elif wind > 25:
        alerts.append({
            "type": "info",
            "icon": "bi-wind",
            "message": "Moderate winds — stay aware of surroundings."
        })

    if humidity > 85:
        alerts.append({
            "type": "info",
            "icon": "bi-droplet-half",
            "message": "High humidity — take frequent breaks and stay hydrated."
        })

    return alerts


def get_weather(latitude, longitude):
    """
    Fetch current weather and 7-day forecast from Open-Meteo.

    Args:
        latitude: GPS latitude (-90 to 90).
        longitude: GPS longitude (-180 to 180).

    Returns:
        dict with keys: current, daily, alerts, success, error
    """
    # Validate coordinates
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return {
            "success": False,
            "error": "Invalid coordinates provided."
        }

    if lat < -90 or lat > 90:
        return {"success": False, "error": "Latitude must be between -90 and 90."}
    if lon < -180 or lon > 180:
        return {"success": False, "error": "Longitude must be between -180 and 180."}

    # Build Open-Meteo request
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "precipitation,weather_code,wind_speed_10m,wind_direction_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "apparent_temperature_max,apparent_temperature_min,"
                 "precipitation_sum,precipitation_probability_max,"
                 "wind_speed_10m_max",
        "timezone": "Asia/Kolkata",
        "forecast_days": 7,
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius"
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException, ValueError) as e:
        print(f"Open-Meteo external exception: {e}. Utilizing offline weather fallback.")
        return {
            "success": True,
            "is_fallback": True,
            "current": {
                "temperature": 28.5,
                "apparent_temperature": 30.0,
                "humidity": 65,
                "precipitation": 0.0,
                "wind_speed": 12.0,
                "wind_direction": 180,
                "condition": "Partly cloudy (Offline Mode)",
                "icon": "bi-cloud-sun-fill",
                "category": "cloudy",
                "time": "2026-08-29T12:00"
            },
            "daily": [
                {"date": "2026-08-29", "temp_max": 30.0, "temp_min": 22.0, "apparent_max": 32.0, "apparent_min": 23.0, "precipitation": 0.0, "precipitation_probability": 10, "wind_speed_max": 15.0, "condition": "Partly cloudy", "icon": "bi-cloud-sun-fill", "category": "cloudy"}
            ],
            "alerts": [
                {"type": "info", "icon": "bi-info-circle", "message": "Weather service operating in offline fallback mode."}
            ],
            "location": {"latitude": lat, "longitude": lon},
            "error": None
        }


    # Parse current weather
    current_raw = data.get("current", {})
    weather_code_info = _decode_weather_code(current_raw.get("weather_code", 0))

    current = {
        "temperature": current_raw.get("temperature_2m"),
        "apparent_temperature": current_raw.get("apparent_temperature"),
        "humidity": current_raw.get("relative_humidity_2m"),
        "precipitation": current_raw.get("precipitation"),
        "wind_speed": current_raw.get("wind_speed_10m"),
        "wind_direction": current_raw.get("wind_direction_10m"),
        "condition": weather_code_info["description"],
        "icon": weather_code_info["icon"],
        "category": weather_code_info["category"],
        "time": current_raw.get("time")
    }

    # Parse daily forecast
    daily_raw = data.get("daily", {})
    daily = []
    dates = daily_raw.get("time", [])
    for i, date in enumerate(dates):
        day_code = daily_raw.get("weather_code", [0] * 7)[i] if i < len(daily_raw.get("weather_code", [])) else 0
        day_info = _decode_weather_code(day_code)
        daily.append({
            "date": date,
            "temp_max": daily_raw.get("temperature_2m_max", [None] * 7)[i],
            "temp_min": daily_raw.get("temperature_2m_min", [None] * 7)[i],
            "apparent_max": daily_raw.get("apparent_temperature_max", [None] * 7)[i],
            "apparent_min": daily_raw.get("apparent_temperature_min", [None] * 7)[i],
            "precipitation": daily_raw.get("precipitation_sum", [None] * 7)[i],
            "precipitation_probability": daily_raw.get("precipitation_probability_max", [None] * 7)[i],
            "wind_speed_max": daily_raw.get("wind_speed_10m_max", [None] * 7)[i],
            "condition": day_info["description"],
            "icon": day_info["icon"],
            "category": day_info["category"]
        })

    # Generate alerts
    alerts = _generate_alerts(current_raw, daily_raw)

    return {
        "success": True,
        "current": current,
        "daily": daily,
        "alerts": alerts,
        "location": {"latitude": lat, "longitude": lon},
        "error": None
    }
