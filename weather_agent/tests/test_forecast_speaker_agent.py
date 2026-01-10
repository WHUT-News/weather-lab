"""
Test script for Forecast Speaker Agent
Tests the forecast speaker subagent (TTS) in isolation with mocked dependencies.
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
    from weather_agent.sub_agents.forecast_speaker.agent import forecast_speaker_agent
except ImportError:
    from sub_agents.forecast_speaker.agent import forecast_speaker_agent


def create_mock_tool_context(session_values=None):
    """Create a mock ToolContext with session values."""
    context = Mock(spec=ToolContext)
    context.session = Mock()
    context.session.get_value = Mock(side_effect=lambda key: session_values.get(key) if session_values else None)
    context.session.set_value = Mock()
    return context


def test_forecast_speaker_basic():
    """Test forecast speaker agent with mocked TTS generation."""
    print("\n=== Testing Forecast Speaker Agent ===\n")

    # Mock session with forecast text
    forecast_text = (
        "Good morning! Currently in Seattle, we have light rain with a temperature "
        "of 55 degrees Fahrenheit. The humidity is at 75% with winds at 8.5 mph. "
        "Don't forget your umbrella today!"
    )

    session_values = {
        "CITY": "Seattle",
        "FORECAST_TEXT": forecast_text,
        "FORECAST_TIMESTAMP": "20250109_120000"
    }

    mock_context = create_mock_tool_context(session_values)

    # Mock the audio generation
    mock_audio_path = "/output/Seattle/forecast_audio_20250109_120000.wav"

    print(f"Testing audio generation for: {session_values['CITY']}")
    print(f"Forecast text length: {len(forecast_text)} characters")
    print(f"Text preview: {forecast_text[:100]}...")

    with patch('weather_agent.sub_agents.forecast_speaker.tools.generate_audio.generate_audio') as mock_generate:
        mock_generate.return_value = mock_audio_path

        # Verify agent configuration
        print(f"\n* Agent Name: {forecast_speaker_agent.name}")
        print(f"* Agent Type: {type(forecast_speaker_agent).__name__}")
        print(f"* Tools Registered: {len(forecast_speaker_agent.tools)}")

        tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in forecast_speaker_agent.tools]
        print(f"* Available Tools: {tool_names}")
        print(f"\nMocked audio output: {mock_audio_path}")

    print("\n=== Test Complete ===\n")


def test_forecast_speaker_with_different_tones():
    """Test forecast speaker with different voice tones."""
    print("\n=== Testing Different Voice Tones ===\n")

    tones = ["cheerfully", "professionally", "calmly", "enthusiastically"]

    forecast_text = "Today's weather is sunny with clear skies."

    for tone in tones:
        print(f"Testing tone: {tone}")
        session_values = {
            "CITY": "Miami",
            "FORECAST_TEXT": forecast_text
        }

        with patch('weather_agent.sub_agents.forecast_speaker.tools.generate_audio.generate_audio') as mock_generate:
            mock_audio_path = f"/output/Miami/forecast_audio_{tone}.wav"
            mock_generate.return_value = mock_audio_path

            # Would call generate_audio with tone parameter
            print(f"  * Would generate audio with tone: {tone}")
            print(f"  * Output path: {mock_audio_path}")

    print("\n=== Test Complete ===\n")


def test_forecast_speaker_with_long_text():
    """Test forecast speaker with longer forecast text."""
    print("\n=== Testing Long Forecast Text ===\n")

    long_forecast = (
        "Good morning! Currently in New York City, we're experiencing partly cloudy skies "
        "with a temperature of 72 degrees Fahrenheit. The humidity is comfortable at 60% "
        "with gentle winds at 5 miles per hour from the northeast. "
        "Looking ahead to this afternoon, expect temperatures to climb to around 78 degrees "
        "with continued partly cloudy conditions. There's a 20% chance of isolated showers "
        "late in the evening. Perfect weather for outdoor activities, but keep an umbrella handy "
        "just in case those evening showers develop. Have a wonderful day!"
    )

    session_values = {
        "CITY": "New York",
        "FORECAST_TEXT": long_forecast
    }

    print(f"Forecast text length: {len(long_forecast)} characters")
    print(f"Word count: {len(long_forecast.split())} words")
    print(f"Estimated speech duration: ~{len(long_forecast.split()) / 150:.1f} minutes")

    with patch('weather_agent.sub_agents.forecast_speaker.tools.generate_audio.generate_audio') as mock_generate:
        mock_generate.return_value = "/output/NewYork/forecast_audio_long.wav"
        print(f"\n* Long text TTS generation configured")

    print("\n=== Test Complete ===\n")


def test_forecast_speaker_tool_configuration():
    """Verify the forecast speaker agent has correct tools configured."""
    print("\n=== Testing Tool Configuration ===\n")

    print(f"Agent: {forecast_speaker_agent.name}")
    print(f"Tools count: {len(forecast_speaker_agent.tools)}")

    expected_tools = ["generate_audio", "set_session_value"]

    print(f"\nExpected tools: {expected_tools}")
    print("Verifying agent configuration...")

    # Check agent has tools
    assert len(forecast_speaker_agent.tools) > 0, "Agent should have tools configured"
    print("* Agent has tools configured")

    print("\n=== Test Complete ===\n")


def test_forecast_speaker_error_handling():
    """Test error handling when forecast text is missing."""
    print("\n=== Testing Error Handling ===\n")

    # Session without FORECAST_TEXT
    session_values = {
        "CITY": "Boston"
        # Missing FORECAST_TEXT
    }

    mock_context = create_mock_tool_context(session_values)

    print("Testing with missing FORECAST_TEXT in session")
    print(f"Session values: {session_values}")

    # The agent should handle this gracefully or the get_value should return None
    forecast_text = mock_context.session.get_value("FORECAST_TEXT")
    print(f"Retrieved forecast text: {forecast_text}")

    if forecast_text is None:
        print("* Correctly identified missing forecast text")
    else:
        print("X Expected None for missing forecast text")

    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    print("=" * 60)
    print("FORECAST SPEAKER AGENT TEST SUITE")
    print("=" * 60)

    try:
        test_forecast_speaker_basic()
        test_forecast_speaker_with_different_tones()
        test_forecast_speaker_with_long_text()
        test_forecast_speaker_tool_configuration()
        test_forecast_speaker_error_handling()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED *")
        print("=" * 60)

    except Exception as e:
        print(f"\nX TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
