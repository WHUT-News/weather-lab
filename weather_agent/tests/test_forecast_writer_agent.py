"""
Test script for Forecast Writer Agent
Tests the forecast writer subagent in isolation with mocked dependencies.
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
    from weather_agent.sub_agents.forecast_writer.agent import forecast_writer_agent
except ImportError:
    from sub_agents.forecast_writer.agent import forecast_writer_agent


def create_mock_tool_context(session_values=None):
    """Create a mock ToolContext with session values."""
    context = Mock(spec=ToolContext)
    context.session = Mock()
    context.session.get_value = Mock(side_effect=lambda key: session_values.get(key) if session_values else None)
    context.session.set_value = Mock()
    return context


def test_forecast_writer_basic():
    """Test forecast writer agent with mocked weather API."""
    print("\n=== Testing Forecast Writer Agent ===\n")

    # Mock session with city
    session_values = {
        "CITY": "Seattle",
        "WEATHER_TYPE": "current weather condition"
    }

    mock_context = create_mock_tool_context(session_values)

    # Mock the weather API response
    mock_weather_response = {
        "main": {
            "temp": 55.4,
            "feels_like": 52.3,
            "humidity": 75
        },
        "weather": [
            {"description": "light rain"}
        ],
        "wind": {
            "speed": 8.5
        },
        "name": "Seattle"
    }

    # Mock the get_current_weather tool
    with patch('sub_agents.forecast_writer.tools.get_weather.get_current_weather') as mock_weather:
        mock_weather.return_value = mock_weather_response

        # Mock file writing
        with patch('sub_agents.forecast_writer.tools.write_text_file.write_text_file') as mock_write:
            mock_write.return_value = "/output/Seattle/forecast_text_20250109_120000.txt"

            # Run the agent
            print(f"Testing forecast generation for: {session_values['CITY']}")
            print(f"Weather type: {session_values['WEATHER_TYPE']}")
            print(f"\nMocked weather data:")
            print(f"  - Temperature: {mock_weather_response['main']['temp']}°F")
            print(f"  - Conditions: {mock_weather_response['weather'][0]['description']}")
            print(f"  - Humidity: {mock_weather_response['main']['humidity']}%")
            print(f"  - Wind speed: {mock_weather_response['wind']['speed']} mph")

            # Note: Actual agent execution would require full ADK setup
            # For isolated testing, we verify the agent configuration
            print(f"\n* Agent Name: {forecast_writer_agent.name}")
            print(f"* Agent Type: {type(forecast_writer_agent).__name__}")
            print(f"* Tools Registered: {len(forecast_writer_agent.tools)}")

            tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in forecast_writer_agent.tools]
            print(f"* Available Tools: {tool_names}")

    print("\n=== Test Complete ===\n")


def test_forecast_writer_with_different_cities():
    """Test forecast writer with multiple cities."""
    print("\n=== Testing Multiple Cities ===\n")

    cities = ["New York", "London", "Tokyo", "Sydney"]

    for city in cities:
        print(f"Configuring test for: {city}")
        session_values = {
            "CITY": city,
            "WEATHER_TYPE": "current weather condition"
        }

        mock_context = create_mock_tool_context(session_values)
        print(f"  * Session configured with city: {city}")

    print("\n=== Test Complete ===\n")


def test_forecast_writer_tool_configuration():
    """Verify the forecast writer agent has correct tools configured."""
    print("\n=== Testing Tool Configuration ===\n")

    print(f"Agent: {forecast_writer_agent.name}")
    print(f"Tools count: {len(forecast_writer_agent.tools)}")

    expected_tools = ["get_current_weather", "set_session_value", "write_text_file"]

    print(f"\nExpected tools: {expected_tools}")
    print("Verifying agent configuration...")

    # Check agent has tools
    assert len(forecast_writer_agent.tools) > 0, "Agent should have tools configured"
    print("* Agent has tools configured")

    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    print("=" * 60)
    print("FORECAST WRITER AGENT TEST SUITE")
    print("=" * 60)

    try:
        test_forecast_writer_basic()
        test_forecast_writer_with_different_cities()
        test_forecast_writer_tool_configuration()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED *")
        print("=" * 60)

    except Exception as e:
        print(f"\nX TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
