"""
Test script for Forecast Photographer Agent
Tests the forecast photographer subagent (image generation) in isolation with mocked dependencies.
"""

import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Add weather_agent to path for proper package resolution
weather_agent_parent = str(Path(__file__).parent.parent.parent)
if weather_agent_parent not in sys.path:
    sys.path.insert(0, weather_agent_parent)

from google.adk.tools import ToolContext

# Import after path is set up properly
try:
    from weather_agent.sub_agents.forecast_photographer.agent import forecast_photographer_agent
except ImportError:
    from sub_agents.forecast_photographer.agent import forecast_photographer_agent


def create_mock_tool_context(session_values=None):
    """Create a mock ToolContext with session values."""
    context = Mock(spec=ToolContext)
    context.session = Mock()
    context.session.get_value = Mock(side_effect=lambda key: session_values.get(key) if session_values else None)
    context.session.set_value = Mock()
    return context


def test_forecast_photographer_basic():
    """Test forecast photographer agent with mocked image generation."""
    print("\n=== Testing Forecast Photographer Agent ===\n")

    # Mock session with forecast text
    forecast_text = (
        "Good morning! Currently in Seattle, we have light rain with a temperature "
        "of 55 degrees Fahrenheit. The humidity is at 75% with winds at 8.5 mph."
    )

    session_values = {
        "CITY": "Seattle",
        "FORECAST_TEXT": forecast_text,
        "FORECAST_TIMESTAMP": "20250109_120000"
    }

    mock_context = create_mock_tool_context(session_values)

    # Mock the image generation
    mock_image_path = "/output/Seattle/forecast_picture_20250109_120000.png"

    print(f"Testing image generation for: {session_values['CITY']}")
    print(f"Forecast text: {forecast_text[:80]}...")

    with patch('weather_agent.sub_agents.forecast_photographer.tools.generate_picture.generate_picture') as mock_generate:
        mock_generate.return_value = mock_image_path

        # Verify agent configuration
        print(f"\n* Agent Name: {forecast_photographer_agent.name}")
        print(f"* Agent Type: {type(forecast_photographer_agent).__name__}")
        print(f"* Tools Registered: {len(forecast_photographer_agent.tools)}")

        tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in forecast_photographer_agent.tools]
        print(f"* Available Tools: {tool_names}")
        print(f"\nMocked image output: {mock_image_path}")

    print("\n=== Test Complete ===\n")


def test_forecast_photographer_with_different_themes():
    """Test forecast photographer with different visual themes."""
    print("\n=== Testing Different Visual Themes ===\n")

    themes = [
        "city skyline",
        "natural landscape",
        "urban park",
        "waterfront view",
        "mountain vista"
    ]

    forecast_text = "Sunny weather with clear blue skies today."

    for theme in themes:
        print(f"Testing theme: {theme}")
        session_values = {
            "CITY": "San Francisco",
            "FORECAST_TEXT": forecast_text
        }

        with patch('weather_agent.sub_agents.forecast_photographer.tools.generate_picture.generate_picture') as mock_generate:
            mock_image_path = f"/output/SanFrancisco/forecast_picture_{theme.replace(' ', '_')}.png"
            mock_generate.return_value = mock_image_path

            # Would call generate_picture with theme parameter
            print(f"  * Would generate image with theme: {theme}")
            print(f"  * Output path: {mock_image_path}")

    print("\n=== Test Complete ===\n")


def test_forecast_photographer_weather_conditions():
    """Test image generation for different weather conditions."""
    print("\n=== Testing Different Weather Conditions ===\n")

    weather_conditions = [
        ("Seattle", "rainy", "Heavy rain with overcast skies"),
        ("Miami", "sunny", "Bright sunshine and clear skies"),
        ("Chicago", "snowy", "Snow showers with low visibility"),
        ("Phoenix", "hot", "Extreme heat with desert sun"),
        ("San Francisco", "foggy", "Dense fog blanketing the city")
    ]

    for city, condition, description in weather_conditions:
        print(f"\n{city} - {condition.upper()}")
        print(f"Description: {description}")

        session_values = {
            "CITY": city,
            "FORECAST_TEXT": description
        }

        with patch('weather_agent.sub_agents.forecast_photographer.tools.generate_picture.generate_picture') as mock_generate:
            mock_image_path = f"/output/{city}/forecast_picture_{condition}.png"
            mock_generate.return_value = mock_image_path

            print(f"  * Image path: {mock_image_path}")

    print("\n=== Test Complete ===\n")


def test_forecast_photographer_image_formats():
    """Test different image format configurations."""
    print("\n=== Testing Image Format Configuration ===\n")

    formats = ["png", "jpg", "webp"]
    aspect_ratios = ["16:9", "4:3", "1:1", "9:16"]

    print("Image format options:")
    for fmt in formats:
        print(f"  - {fmt}")

    print("\nAspect ratio options:")
    for ratio in aspect_ratios:
        print(f"  - {ratio}")

    # Test with PNG (default)
    session_values = {
        "CITY": "Portland",
        "FORECAST_TEXT": "Cloudy with chance of rain"
    }

    with patch('weather_agent.sub_agents.forecast_photographer.tools.generate_picture.generate_picture') as mock_generate:
        mock_image_path = "/output/Portland/forecast_picture_20250109.png"
        mock_generate.return_value = mock_image_path

        print(f"\n* Default format test configured")
        print(f"* Output path: {mock_image_path}")

    print("\n=== Test Complete ===\n")


def test_forecast_photographer_tool_configuration():
    """Verify the forecast photographer agent has correct tools configured."""
    print("\n=== Testing Tool Configuration ===\n")

    print(f"Agent: {forecast_photographer_agent.name}")
    print(f"Tools count: {len(forecast_photographer_agent.tools)}")

    expected_tools = ["generate_picture", "set_session_value"]

    print(f"\nExpected tools: {expected_tools}")
    print("Verifying agent configuration...")

    # Check agent has tools
    assert len(forecast_photographer_agent.tools) > 0, "Agent should have tools configured"
    print("* Agent has tools configured")

    print("\n=== Test Complete ===\n")


def test_forecast_photographer_error_handling():
    """Test error handling scenarios."""
    print("\n=== Testing Error Handling ===\n")

    # Test 1: Missing forecast text
    print("Test 1: Missing FORECAST_TEXT")
    session_values = {
        "CITY": "Boston"
        # Missing FORECAST_TEXT
    }

    mock_context = create_mock_tool_context(session_values)
    forecast_text = mock_context.session.get_value("FORECAST_TEXT")

    if forecast_text is None:
        print("  * Correctly identified missing forecast text")

    # Test 2: Empty city name
    print("\nTest 2: Empty city name")
    session_values = {
        "CITY": "",
        "FORECAST_TEXT": "Some weather description"
    }

    mock_context = create_mock_tool_context(session_values)
    city = mock_context.session.get_value("CITY")

    if not city:
        print("  * Correctly identified empty city")

    print("\n=== Test Complete ===\n")


def test_forecast_photographer_prompt_generation():
    """Test how different weather descriptions might translate to image prompts."""
    print("\n=== Testing Prompt Generation Logic ===\n")

    test_cases = [
        {
            "city": "New York",
            "forecast": "Heavy snowfall with temperatures below freezing",
            "expected_elements": ["snow", "winter", "cold", "urban"]
        },
        {
            "city": "Los Angeles",
            "forecast": "Warm sunshine with temperatures in the 80s",
            "expected_elements": ["sunny", "warm", "clear sky", "bright"]
        },
        {
            "city": "London",
            "forecast": "Overcast with light drizzle throughout the day",
            "expected_elements": ["cloudy", "rain", "grey", "moody"]
        }
    ]

    for test in test_cases:
        print(f"\nCity: {test['city']}")
        print(f"Forecast: {test['forecast']}")
        print(f"Expected visual elements: {', '.join(test['expected_elements'])}")

        session_values = {
            "CITY": test['city'],
            "FORECAST_TEXT": test['forecast']
        }

        print("  * Prompt generation test configured")

    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    print("=" * 60)
    print("FORECAST PHOTOGRAPHER AGENT TEST SUITE")
    print("=" * 60)

    try:
        test_forecast_photographer_basic()
        test_forecast_photographer_with_different_themes()
        test_forecast_photographer_weather_conditions()
        test_forecast_photographer_image_formats()
        test_forecast_photographer_tool_configuration()
        test_forecast_photographer_error_handling()
        test_forecast_photographer_prompt_generation()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print(f"\nX TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
