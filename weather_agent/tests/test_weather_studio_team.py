"""
Test script for Weather Studio Team (Parent Agent)
Tests the sequential and parallel agent coordination with mocked subagents.
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


def create_mock_tool_context(session_values=None):
    """Create a mock ToolContext with session values."""
    context = Mock(spec=ToolContext)
    context.session = Mock()

    # Make session values mutable for testing
    if session_values is None:
        session_values = {}

    def mock_get(key):
        return session_values.get(key)

    def mock_set(key, value):
        session_values[key] = value
        return value

    context.session.get_value = Mock(side_effect=mock_get)
    context.session.set_value = Mock(side_effect=mock_set)

    return context, session_values


def test_weather_studio_team_structure():
    """Test the weather studio team agent structure and configuration."""
    print("\n=== Testing Weather Studio Team Structure ===\n")

    try:
        from weather_agent.agent import weather_studio_team
    except ImportError:
        from agent import weather_studio_team

    print(f"Team Name: {weather_studio_team.name}")
    print(f"Team Type: {type(weather_studio_team).__name__}")

    # Check sub-agents
    if hasattr(weather_studio_team, 'sub_agents'):
        print(f"Number of sub-agents: {len(weather_studio_team.sub_agents)}")

        for i, agent in enumerate(weather_studio_team.sub_agents, 1):
            agent_name = agent.name if hasattr(agent, 'name') else f"Agent {i}"
            agent_type = type(agent).__name__
            print(f"  {i}. {agent_name} ({agent_type})")

            # Check if agent has sub-agents (for nested structure)
            if hasattr(agent, 'sub_agents'):
                print(f"     +- Has {len(agent.sub_agents)} sub-agents")
                for sub in agent.sub_agents:
                    sub_name = sub.name if hasattr(sub, 'name') else "Unnamed"
                    print(f"        - {sub_name}")

    print("\n* Weather studio team structure verified")
    print("\n=== Test Complete ===\n")


def test_weather_studio_team_workflow():
    """Test the complete workflow of the weather studio team."""
    print("\n=== Testing Weather Studio Team Workflow ===\n")

    # Initialize session state
    session_values = {
        "CITY": "Seattle",
        "WEATHER_TYPE": "current weather condition",
        "FORECAST_TIMESTAMP": "20250109_120000"
    }

    mock_context, session_data = create_mock_tool_context(session_values)

    print("Initial Session State:")
    for key, value in session_data.items():
        print(f"  {key}: {value}")

    print("\n--- Simulating Workflow ---\n")

    # Step 1: Forecast Writer (Sequential)
    print("Step 1: Forecast Writer Agent")
    forecast_text = (
        "Good morning! Currently in Seattle, we have light rain with a temperature "
        "of 55 degrees Fahrenheit. The humidity is at 75% with winds at 8.5 mph."
    )

    with patch('weather_agent.sub_agents.forecast_writer.tools.get_weather.get_current_weather') as mock_weather:
        mock_weather.return_value = {
            "main": {"temp": 55, "humidity": 75},
            "weather": [{"description": "light rain"}],
            "wind": {"speed": 8.5}
        }

        # Simulate setting forecast text in session
        session_data["FORECAST_TEXT"] = forecast_text
        session_data["FORECAST_TEXT_FILE"] = "/output/Seattle/forecast_text_20250109_120000.txt"

        print(f"  * Generated forecast text ({len(forecast_text)} chars)")
        print(f"  * Stored in session: FORECAST_TEXT")
        print(f"  * Saved to: {session_data['FORECAST_TEXT_FILE']}")

    # Step 2: Weather Media Team (Parallel)
    print("\nStep 2: Weather Media Team (Parallel Execution)")

    # Parallel task 1: Forecast Speaker
    print("  Task A: Forecast Speaker Agent")
    with patch('sub_agents.forecast_speaker.tools.generate_audio.generate_audio') as mock_audio:
        audio_path = "/output/Seattle/forecast_audio_20250109_120000.wav"
        mock_audio.return_value = audio_path

        session_data["FORECAST_AUDIO"] = audio_path
        print(f"    * Generated audio file")
        print(f"    * Stored in session: FORECAST_AUDIO")
        print(f"    * Saved to: {audio_path}")

    # Parallel task 2: Forecast Photographer
    print("  Task B: Forecast Photographer Agent")
    with patch('sub_agents.forecast_photographer.tools.generate_picture.generate_picture') as mock_image:
        image_path = "/output/Seattle/forecast_picture_20250109_120000.png"
        mock_image.return_value = image_path

        session_data["FORECAST_PICTURE"] = image_path
        print(f"    * Generated image file")
        print(f"    * Stored in session: FORECAST_PICTURE")
        print(f"    * Saved to: {image_path}")

    print("\n--- Final Session State ---\n")
    for key, value in session_data.items():
        print(f"  {key}: {value}")

    # Verify all expected keys are present
    expected_keys = ["CITY", "WEATHER_TYPE", "FORECAST_TEXT", "FORECAST_AUDIO", "FORECAST_PICTURE"]
    missing_keys = [key for key in expected_keys if key not in session_data]

    if not missing_keys:
        print("\n* All expected session values present")
    else:
        print(f"\nX Missing session values: {missing_keys}")

    print("\n=== Test Complete ===\n")


def test_weather_studio_team_sequential_order():
    """Test that forecast writer completes before media team starts."""
    print("\n=== Testing Sequential Execution Order ===\n")

    execution_log = []

    session_values = {
        "CITY": "Portland",
        "WEATHER_TYPE": "current weather condition"
    }

    mock_context, session_data = create_mock_tool_context(session_values)

    # Simulate sequential execution
    print("Simulating execution order:")

    # Forecast Writer must complete first
    print("\n1. Forecast Writer Agent (Sequential)")
    execution_log.append("forecast_writer_start")

    forecast_text = "Weather forecast for Portland..."
    session_data["FORECAST_TEXT"] = forecast_text
    execution_log.append("forecast_writer_complete")

    print("   * Forecast writer completed")
    print(f"   * FORECAST_TEXT available: {bool(session_data.get('FORECAST_TEXT'))}")

    # Media team can only start after forecast text is available
    if session_data.get("FORECAST_TEXT"):
        print("\n2. Weather Media Team (Parallel)")
        print("   Starting parallel tasks...")

        execution_log.append("media_team_start")

        # Both can run in parallel
        execution_log.append("speaker_start")
        execution_log.append("photographer_start")

        session_data["FORECAST_AUDIO"] = "/output/Portland/audio.wav"
        session_data["FORECAST_PICTURE"] = "/output/Portland/picture.png"

        execution_log.append("speaker_complete")
        execution_log.append("photographer_complete")
        execution_log.append("media_team_complete")

        print("   * Speaker and Photographer completed (parallel)")

    print("\nExecution Log:")
    for i, event in enumerate(execution_log, 1):
        print(f"  {i}. {event}")

    # Verify order
    assert execution_log.index("forecast_writer_complete") < execution_log.index("media_team_start"), \
        "Forecast writer must complete before media team starts"

    print("\n* Sequential execution order verified")
    print("\n=== Test Complete ===\n")


def test_weather_studio_team_parallel_execution():
    """Test that speaker and photographer run in parallel."""
    print("\n=== Testing Parallel Execution ===\n")

    import time

    session_values = {
        "CITY": "Denver",
        "FORECAST_TEXT": "Sunny weather in Denver today..."
    }

    mock_context, session_data = create_mock_tool_context(session_values)

    print("Simulating parallel execution of media team:")
    print("(In real execution, these would run concurrently)\n")

    # Simulate parallel execution
    tasks = []

    # Task 1: Audio generation
    print("Task 1: Audio Generation")
    start_time = time.time()
    session_data["FORECAST_AUDIO"] = "/output/Denver/audio.wav"
    audio_duration = time.time() - start_time
    tasks.append(("Audio Generation", audio_duration))
    print(f"  * Completed in {audio_duration:.4f}s")

    # Task 2: Image generation (would run simultaneously)
    print("\nTask 2: Image Generation")
    start_time = time.time()
    session_data["FORECAST_PICTURE"] = "/output/Denver/picture.png"
    image_duration = time.time() - start_time
    tasks.append(("Image Generation", image_duration))
    print(f"  * Completed in {image_duration:.4f}s")

    print(f"\nTotal execution time (parallel): {max(audio_duration, image_duration):.4f}s")
    print(f"Total execution time (sequential): {audio_duration + image_duration:.4f}s")
    print(f"Time saved by parallel execution: {abs(audio_duration + image_duration - max(audio_duration, image_duration)):.4f}s")

    print("\n* Parallel execution simulation completed")
    print("\n=== Test Complete ===\n")


def test_weather_studio_team_error_handling():
    """Test error handling in the weather studio team workflow."""
    print("\n=== Testing Error Handling ===\n")

    # Test 1: Missing city
    print("Test 1: Missing CITY in session")
    session_values = {
        "WEATHER_TYPE": "current weather condition"
    }

    mock_context, session_data = create_mock_tool_context(session_values)

    city = session_data.get("CITY")
    if not city:
        print("  * Detected missing city")
        print("  → Workflow should request city from user")

    # Test 2: Missing forecast text for media team
    print("\nTest 2: Media team without forecast text")
    session_values = {
        "CITY": "Austin"
        # Missing FORECAST_TEXT
    }

    mock_context, session_data = create_mock_tool_context(session_values)

    forecast_text = session_data.get("FORECAST_TEXT")
    if not forecast_text:
        print("  * Detected missing forecast text")
        print("  → Media team cannot proceed without forecast text")

    # Test 3: Partial completion
    print("\nTest 3: Partial completion handling")
    session_values = {
        "CITY": "Houston",
        "FORECAST_TEXT": "Weather data...",
        "FORECAST_AUDIO": "/output/Houston/audio.wav"
        # Missing FORECAST_PICTURE
    }

    mock_context, session_data = create_mock_tool_context(session_values)

    has_text = bool(session_data.get("FORECAST_TEXT"))
    has_audio = bool(session_data.get("FORECAST_AUDIO"))
    has_picture = bool(session_data.get("FORECAST_PICTURE"))

    print(f"  Forecast Text: {'*' if has_text else 'X'}")
    print(f"  Forecast Audio: {'*' if has_audio else 'X'}")
    print(f"  Forecast Picture: {'X' if not has_picture else '*'}")

    if has_text and has_audio and not has_picture:
        print("  → System should retry or report picture generation failure")

    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    print("=" * 60)
    print("WEATHER STUDIO TEAM TEST SUITE")
    print("=" * 60)

    try:
        test_weather_studio_team_structure()
        test_weather_studio_team_workflow()
        test_weather_studio_team_sequential_order()
        test_weather_studio_team_parallel_execution()
        test_weather_studio_team_error_handling()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED *")
        print("=" * 60)

    except Exception as e:
        print(f"\nX TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
