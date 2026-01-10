# Weather Agent Test Suite

Comprehensive test scripts for testing individual agents and subagents in isolation with mocked dependencies.

## Test Files

### Individual Agent Tests

1. **test_forecast_writer_agent.py**
   - Tests the Forecast Writer subagent
   - Mocks OpenWeather API responses
   - Verifies forecast text generation
   - Tests with multiple cities
   - Tests tool configuration

2. **test_forecast_speaker_agent.py**
   - Tests the Forecast Speaker subagent (TTS)
   - Mocks audio generation
   - Tests different voice tones
   - Tests with various text lengths
   - Tests error handling for missing forecast text

3. **test_forecast_photographer_agent.py**
   - Tests the Forecast Photographer subagent (Image generation)
   - Mocks image generation
   - Tests different visual themes
   - Tests various weather conditions
   - Tests image format configurations
   - Tests prompt generation logic

4. **test_weather_studio_team.py**
   - Tests the Weather Studio Team parent agent
   - Verifies sequential and parallel execution
   - Tests agent coordination
   - Tests session state management
   - Tests error handling and partial completion

5. **test_root_agent.py**
   - Tests the main root agent orchestration
   - Tests caching integration (cache hit/miss scenarios)
   - Tests storage upload callbacks
   - Tests complete end-to-end workflow
   - Tests error scenarios and recovery

### Test Runner

**run_all_agent_tests.py**
- Master test runner that executes all test scripts
- Provides consolidated test summary
- Reports pass/fail status for each test suite
- Exits with appropriate status code

## Running the Tests

### Run All Tests

```bash
# From the weather_agent directory
python tests/run_all_agent_tests.py
```

### Run Individual Test Suites

```bash
# Test Forecast Writer Agent
python tests/test_forecast_writer_agent.py

# Test Forecast Speaker Agent
python tests/test_forecast_speaker_agent.py

# Test Forecast Photographer Agent
python tests/test_forecast_photographer_agent.py

# Test Weather Studio Team
python tests/test_weather_studio_team.py

# Test Root Agent
python tests/test_root_agent.py
```

## Test Architecture

### Mocking Strategy

All tests use Python's `unittest.mock` to create isolated test environments:

- **ToolContext**: Mock ADK tool context with session state
- **CallbackContext**: Mock callback context for after_agent callbacks
- **External APIs**: Mock OpenWeather API, Gemini TTS, Imagen API
- **Storage**: Mock MCP client and Cloud SQL storage operations
- **File I/O**: Mock file writing operations

### Session State Testing

Tests verify proper session state management:
- Initial state setup
- State mutations during agent execution
- State passing between sequential agents
- State access in parallel agents

### Test Coverage

Each test suite covers:
- ✓ Basic functionality
- ✓ Configuration verification
- ✓ Multiple scenarios (cities, weather conditions, etc.)
- ✓ Error handling
- ✓ Edge cases

## Test Output

Each test script provides detailed output:
- Test section headers
- Step-by-step execution logs
- Verification checkmarks (✓)
- Session state snapshots
- Error indicators (✗)
- Final pass/fail status

Example output:
```
==============================================================
FORECAST WRITER AGENT TEST SUITE
==============================================================

=== Testing Forecast Writer Agent ===

Testing forecast generation for: Seattle
Weather type: current weather condition

Mocked weather data:
  - Temperature: 55.4°F
  - Conditions: light rain
  - Humidity: 75%
  - Wind speed: 8.5 mph

✓ Agent Name: forecast_writer_agent
✓ Agent Type: Agent
✓ Tools Registered: 3
✓ Available Tools: [...]

=== Test Complete ===

==============================================================
ALL TESTS PASSED ✓
==============================================================
```

## Dependencies

These test scripts require:
- `google-adk` - Google Agent Development Kit
- Standard library modules: `unittest.mock`, `pathlib`, `sys`, `asyncio`

## Integration with CI/CD

The test suite is designed for CI/CD integration:
- Returns proper exit codes (0 = success, 1 = failure)
- Runs in isolated environments
- No external API calls (all mocked)
- Fast execution (no network delays)
- Comprehensive output for debugging

## Adding New Tests

To add tests for a new agent:

1. Create a new test file: `test_<agent_name>.py`
2. Follow the existing test patterns
3. Use `create_mock_tool_context()` for session mocking
4. Add the test file to `run_all_agent_tests.py`

Example template:
```python
"""
Test script for <Agent Name>
Tests the <agent> in isolation with mocked dependencies.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.genai.adk import ToolContext
from <module> import <agent>

def create_mock_tool_context(session_values=None):
    # ... mock setup ...

def test_<agent>_basic():
    print("\n=== Testing <Agent> ===\n")
    # ... test implementation ...
    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    try:
        test_<agent>_basic()
        # ... more tests ...
        print("\nALL TESTS PASSED ✓")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
```

## Troubleshooting

**Import Errors**:
- Ensure you're running from the correct directory
- Check that all agent modules are properly installed

**Mock Issues**:
- Verify mock patches match actual import paths
- Check that session state is properly initialized

**Test Failures**:
- Review detailed output for specific assertion failures
- Check that agent structure hasn't changed
- Verify tool configurations match expectations

## Future Enhancements

Potential improvements:
- [ ] Add pytest integration
- [ ] Add code coverage reporting
- [ ] Add performance benchmarks
- [ ] Add integration tests with real APIs (optional)
- [ ] Add test fixtures for common scenarios
- [ ] Add parameterized tests for data-driven testing
