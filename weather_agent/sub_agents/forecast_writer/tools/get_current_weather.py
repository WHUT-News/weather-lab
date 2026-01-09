import os
import requests
from typing import Dict, Any

from ....caching.api_call_cache import cached_with_ttl

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = os.getenv("OPENWEATHER_BASE_URL", "https://api.openweathermap.org/data/2.5/weather")

def _format_weather_data(weather_data: Dict[str, Any], units: str = "imperial") -> str:
    """
    Format weather data into a readable string for the agent.

    Args:
        weather_data: Raw weather data from OpenWeather API
        units: Unit system - "imperial" (Fahrenheit) or "metric" (Celsius)

    Returns:
        Formatted string with weather information
    """
    if "error" in weather_data:
        return f"Error: {weather_data['message']}"

    try:
        city = weather_data['name']
        country = weather_data['sys']['country']
        temp = weather_data['main']['temp']
        feels_like = weather_data['main']['feels_like']
        humidity = weather_data['main']['humidity']
        description = weather_data['weather'][0]['description']
        wind_speed = weather_data['wind']['speed']

        # format the values appropriately for the units
        temp = round(temp)
        feels_like = round(feels_like)
        wind_speed = round(wind_speed)

        temp_unit = "°F" if units == "imperial" else "°C"
        wind_unit = "mph" if units == "imperial" else "m/s"

        formatted = f"""Weather in {city}, {country}:
- Temperature: {temp}{temp_unit} (feels like {feels_like}{temp_unit})
- Conditions: {description}
- Humidity: {humidity}%
- Wind Speed: {wind_speed} {wind_unit}"""

        return formatted
    except KeyError as e:
        return f"Error parsing weather data: missing field {e}"


@cached_with_ttl(ttl=900)  # Cache for 15 minutes (900 seconds)
def get_current_weather(city: str, units: str = "imperial") -> Dict[str, Any]:
    """
    Fetch current weather data for a given city using OpenWeather API.

    Results are cached for 15 minutes to reduce API calls and improve response time.

    Args:
        city: Name of the city to get weather for
        units: Unit system - "imperial" (Fahrenheit, default) or "metric" (Celsius)

    Returns:
        Dictionary containing weather data in JSON format
    """
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": units
    }

    try:
        response = requests.get(OPENWEATHER_BASE_URL, params=params)
        response.raise_for_status()
        return _format_weather_data(response.json(), units)
    
    except requests.exceptions.RequestException as e:
        return {
            "error": str(e),
            "message": f"Failed to fetch weather data for {city}"
        }


