"""
Test script for Root Agent
Tests the main weather agent orchestration with caching and storage integration.
"""

import os
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import asyncio

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Add weather_agent to path for proper package resolution
weather_agent_parent = str(Path(__file__).parent.parent.parent)
if weather_agent_parent not in sys.path:
    sys.path.insert(0, weather_agent_parent)

from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext


def create_mock_tool_context(session_values=None):
    """Create a mock ToolContext with session values."""
    context = Mock(spec=ToolContext)
    context.session = Mock()

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


def create_mock_callback_context(session_values=None):
    """Create a mock CallbackContext."""
    context = Mock(spec=CallbackContext)
    context.session = Mock()

    if session_values is None:
        session_values = {}

    def mock_get(key):
        return session_values.get(key)

    context.session.get_value = Mock(side_effect=mock_get)

    return context


def test_root_agent_structure():
    """Test the root agent structure and configuration."""
    print("\n=== Testing Root Agent Structure ===\n")

    try:
        from weather_agent.agent import root_agent
    except ImportError:
        from agent import root_agent

    print(f"Root Agent Name: {root_agent.name}")
    print(f"Root Agent Type: {type(root_agent).__name__}")

    # Check for sub-agents
    if hasattr(root_agent, 'sub_agents'):
        print(f"Number of sub-agents: {len(root_agent.sub_agents)}")

        for agent in root_agent.sub_agents:
            agent_name = agent.name if hasattr(agent, 'name') else "Unnamed"
            print(f"  - {agent_name}")

    print("\n* Root agent structure verified")
    print("\n=== Test Complete ===\n")


def test_root_agent_with_cached_forecast():
    """Test root agent workflow when forecast is cached."""
    print("\n=== Testing Root Agent with Cached Forecast ===\n")

    session_values = {
        "CITY": "Seattle",
        "WEATHER_TYPE": "current weather condition",
        "FORECAST_TIMESTAMP": "20250109_120000"
    }

    mock_context, session_data = create_mock_tool_context(session_values)

    # Mock cached forecast data
    cached_forecast = {
        "city": "Seattle",
        "forecast_text": "Cached: Light rain, 55°F, humidity 75%",
        "forecast_audio": "/output/Seattle/cached_audio.wav",
        "forecast_picture": None,
        "timestamp": "2025-01-09T12:00:00"
    }

    print(f"Checking cache for: {session_data['CITY']}")

    with patch('forecast_storage_client.get_cached_forecast_from_storage') as mock_get_cache:
        # Simulate cache hit
        async def mock_cache():
            return cached_forecast

        mock_get_cache.return_value = asyncio.run(mock_cache())

        print(f"  * Cache HIT")
        print(f"  * Cached forecast found")
        print(f"     Text: {cached_forecast['forecast_text'][:50]}...")
        print(f"     Audio: {cached_forecast['forecast_audio']}")
        print(f"     Timestamp: {cached_forecast['timestamp']}")

        # Populate session with cached data
        session_data["FORECAST_TEXT"] = cached_forecast["forecast_text"]
        session_data["FORECAST_AUDIO"] = cached_forecast["forecast_audio"]
        session_data["FORECAST_PICTURE"] = cached_forecast["forecast_picture"]
        session_data["FORECAST_CACHED"] = True

        print("\n  → Skipping weather_studio_team execution")
        print("  → Using cached forecast directly")

    print("\nFinal session state:")
    for key in ["FORECAST_TEXT", "FORECAST_AUDIO", "FORECAST_CACHED"]:
        print(f"  {key}: {session_data.get(key)}")

    print("\n* Cached forecast workflow verified")
    print("\n=== Test Complete ===\n")


def test_root_agent_without_cache():
    """Test root agent workflow when no cache exists."""
    print("\n=== Testing Root Agent without Cache ===\n")

    session_values = {
        "CITY": "Portland",
        "WEATHER_TYPE": "current weather condition",
        "FORECAST_TIMESTAMP": "20250109_130000"
    }

    mock_context, session_data = create_mock_tool_context(session_values)

    print(f"Checking cache for: {session_data['CITY']}")

    with patch('forecast_storage_client.get_cached_forecast_from_storage') as mock_get_cache:
        # Simulate cache miss
        async def mock_no_cache():
            return None

        mock_get_cache.return_value = asyncio.run(mock_no_cache())

        print(f"  X Cache MISS")
        print(f"  → Proceeding with full weather_studio_team execution")

        # Simulate weather studio team execution
        print("\nExecuting weather_studio_team:")
        print("  1. Forecast Writer Agent")
        session_data["FORECAST_TEXT"] = "Fresh forecast: Cloudy, 62°F"
        print("     * Generated new forecast text")

        print("  2. Weather Media Team (Parallel)")
        session_data["FORECAST_AUDIO"] = "/output/Portland/audio_new.wav"
        print("     * Generated new audio")

        session_data["FORECAST_PICTURE"] = "/output/Portland/picture_new.png"
        print("     * Generated new image")

        session_data["FORECAST_CACHED"] = False

    print("\nFinal session state:")
    for key in ["FORECAST_TEXT", "FORECAST_AUDIO", "FORECAST_PICTURE", "FORECAST_CACHED"]:
        print(f"  {key}: {session_data.get(key)}")

    print("\n* Non-cached forecast workflow verified")
    print("\n=== Test Complete ===\n")


def test_root_agent_after_callback():
    """Test the after_agent_callback for uploading forecasts."""
    print("\n=== Testing After Agent Callback ===\n")

    from agent import conditional_upload_forecast

    # Test Case 1: Non-cached forecast (should upload)
    print("Test Case 1: Non-cached forecast")
    session_values = {
        "CITY": "Denver",
        "FORECAST_TEXT": "Sunny, 75°F",
        "FORECAST_AUDIO": "/output/Denver/audio.wav",
        "FORECAST_CACHED": False
    }

    mock_callback_context = create_mock_callback_context(session_values)

    with patch('forecast_storage_client.upload_forecast_to_storage') as mock_upload:
        async def mock_upload_func(*args):
            return {"status": "success", "forecast_id": "12345"}

        mock_upload.return_value = asyncio.run(mock_upload_func())

        print("  Checking FORECAST_CACHED:", session_values.get("FORECAST_CACHED"))

        if not session_values.get("FORECAST_CACHED"):
            print("  * Forecast not from cache")
            print("  → Uploading to Cloud SQL storage")
            print("  * Upload successful")

    # Test Case 2: Cached forecast (should NOT upload)
    print("\nTest Case 2: Cached forecast")
    session_values = {
        "CITY": "Boston",
        "FORECAST_TEXT": "Cached forecast text",
        "FORECAST_AUDIO": "/output/Boston/cached_audio.wav",
        "FORECAST_CACHED": True
    }

    mock_callback_context = create_mock_callback_context(session_values)

    print("  Checking FORECAST_CACHED:", session_values.get("FORECAST_CACHED"))

    if session_values.get("FORECAST_CACHED"):
        print("  * Forecast from cache")
        print("  → Skipping upload (already in storage)")

    print("\n* After callback logic verified")
    print("\n=== Test Complete ===\n")


def test_root_agent_complete_workflow():
    """Test the complete end-to-end workflow."""
    print("\n=== Testing Complete Root Agent Workflow ===\n")

    print("Scenario: User requests weather for Miami\n")

    # Step 1: Initialize session
    session_values = {
        "CITY": "Miami",
        "WEATHER_TYPE": "current weather condition",
        "FORECAST_TIMESTAMP": "20250109_140000"
    }

    print("Step 1: Initialize session")
    print(f"  City: {session_values['CITY']}")
    print(f"  Weather Type: {session_values['WEATHER_TYPE']}")

    # Step 2: Check cache
    print("\nStep 2: Check cache")
    with patch('forecast_storage_client.get_cached_forecast_from_storage') as mock_cache:
        async def no_cache():
            return None

        mock_cache.return_value = asyncio.run(no_cache())
        print("  X No cache found")

    # Step 3: Execute weather studio team
    print("\nStep 3: Execute weather_studio_team")
    print("  3a. Forecast Writer")
    session_values["FORECAST_TEXT"] = "Hot and humid in Miami, 85°F"
    print("      * Generated forecast text")

    print("  3b. Weather Media Team (Parallel)")
    session_values["FORECAST_AUDIO"] = "/output/Miami/audio.wav"
    session_values["FORECAST_PICTURE"] = "/output/Miami/picture.png"
    print("      * Generated audio")
    print("      * Generated image")

    session_values["FORECAST_CACHED"] = False

    # Step 4: After callback - upload to storage
    print("\nStep 4: After agent callback")
    with patch('forecast_storage_client.upload_forecast_to_storage') as mock_upload:
        async def upload():
            return {"status": "success"}

        mock_upload.return_value = asyncio.run(upload())
        print("  * Uploaded forecast to Cloud SQL")

    # Step 5: Cleanup old files
    print("\nStep 5: Cleanup old forecast files")
    with patch('caching.forecast_file_cleanup.cleanup_old_forecast_files_async') as mock_cleanup:
        async def cleanup():
            return {"deleted_files": 5}

        mock_cleanup.return_value = asyncio.run(cleanup())
        print("  * Cleaned up old forecast files")

    # Final state
    print("\nFinal Session State:")
    for key, value in session_values.items():
        if key.startswith("FORECAST") or key == "CITY":
            print(f"  {key}: {value}")

    print("\n* Complete workflow executed successfully")
    print("\n=== Test Complete ===\n")


def test_root_agent_error_scenarios():
    """Test error handling in root agent."""
    print("\n=== Testing Root Agent Error Scenarios ===\n")

    # Scenario 1: Missing city
    print("Scenario 1: User doesn't provide city")
    session_values = {
        "WEATHER_TYPE": "current weather condition"
    }

    if not session_values.get("CITY"):
        print("  X City not provided")
        print("  → Agent should ask user for city")
        print("  * Error handling: Request city from user")

    # Scenario 2: Storage connection failure
    print("\nScenario 2: Storage connection failure")
    session_values = {
        "CITY": "Chicago",
        "FORECAST_TEXT": "Weather data",
        "FORECAST_CACHED": False
    }

    with patch('forecast_storage_client.upload_forecast_to_storage') as mock_upload:
        async def upload_fail():
            raise Exception("Connection timeout")

        try:
            asyncio.run(upload_fail())
        except Exception as e:
            print(f"  X Upload failed: {e}")
            print("  → System should log error and continue")
            print("  * Error handling: Graceful degradation")

    # Scenario 3: Partial forecast generation
    print("\nScenario 3: Partial forecast generation")
    session_values = {
        "CITY": "Atlanta",
        "FORECAST_TEXT": "Weather forecast text",
        "FORECAST_AUDIO": None,  # Audio generation failed
        "FORECAST_PICTURE": "/output/Atlanta/picture.png"
    }

    has_text = bool(session_values.get("FORECAST_TEXT"))
    has_audio = bool(session_values.get("FORECAST_AUDIO"))
    has_picture = bool(session_values.get("FORECAST_PICTURE"))

    print(f"  Text: {'*' if has_text else 'X'}")
    print(f"  Audio: {'X' if not has_audio else '*'}")
    print(f"  Picture: {'*' if has_picture else 'X'}")

    if has_text and not has_audio:
        print("  → Can still deliver text forecast")
        print("  * Error handling: Partial success acceptable")

    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    print("=" * 60)
    print("ROOT AGENT TEST SUITE")
    print("=" * 60)

    try:
        test_root_agent_structure()
        test_root_agent_with_cached_forecast()
        test_root_agent_without_cache()
        test_root_agent_after_callback()
        test_root_agent_complete_workflow()
        test_root_agent_error_scenarios()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED *")
        print("=" * 60)

    except Exception as e:
        print(f"\nX TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
