"""
Test script to verify MCP server works via HTTP.

Usage:
    # Test local HTTP server (run MCP server first on localhost:8080)
    # Terminal 1: cd forecast_storage_mcp && MCP_TRANSPORT=http PORT=8080 python server.py
    # Terminal 2: python test_remote_mcp.py local
    python test_remote_mcp.py local
    
    # Test remote Cloud Run deployment
    MCP_SERVER_URL=https://your-service.run.app python test_remote_mcp.py remote
    
    # Test both modes
    python test_remote_mcp.py all
"""

import os
import sys
import json
import base64
import asyncio
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from weather_agent.forecast_storage_client import _call_mcp_tool_remote


def print_test_header(test_name: str):
    """Print a formatted test header."""
    print(f"\n{'='*60}")
    print(f"  {test_name}")
    print(f"{'='*60}")


def print_result(test_name: str, result: Dict[str, Any], success: bool):
    """Print test result."""
    status = "[PASS]" if success else "[FAIL]"
    print(f"\n{status} - {test_name}")
    print(f"Result: {json.dumps(result, indent=2)}")


async def test_local_http(port: int = 8080):
    """Test MCP server via HTTP on localhost."""
    print_test_header(f"Testing Local HTTP Mode (localhost:{port})")

    localhost_url = f"http://localhost:{port}"
    print(f"\nUsing MCP Server URL: {localhost_url}")
    print("WARNING: Make sure MCP server is running:")
    print(f"  cd forecast_storage_mcp && MCP_TRANSPORT=http PORT={port} python server.py\n")

    test_results = {}
    test_audio_path = None

    try:
        # Create a temporary test audio file (minimal WAV file)
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.wav', delete=False) as f:
            # Minimal valid WAV file header (44 bytes + 1 sample)
            # RIFF header
            f.write(b'RIFF')
            f.write((36).to_bytes(4, 'little'))  # File size - 8
            f.write(b'WAVE')
            # fmt chunk
            f.write(b'fmt ')
            f.write((16).to_bytes(4, 'little'))  # fmt chunk size
            f.write((1).to_bytes(2, 'little'))   # Audio format (PCM)
            f.write((1).to_bytes(2, 'little'))   # Num channels
            f.write((22050).to_bytes(4, 'little'))  # Sample rate
            f.write((44100).to_bytes(4, 'little'))  # Byte rate
            f.write((2).to_bytes(2, 'little'))   # Block align
            f.write((16).to_bytes(2, 'little'))  # Bits per sample
            # data chunk
            f.write(b'data')
            f.write((2).to_bytes(4, 'little'))   # Data size
            f.write(b'\x00\x00')  # Minimal audio data
            test_audio_path = f.name

        # Test 1: Connection test
        print("\nTest 1: Testing database connection...")
        result = await _call_mcp_tool_remote("test_connection", {})
        success = result.get("status") == "success"
        print_result("Connection Test", result, success)
        test_results["test_connection"] = success
        if not success:
            print("⚠️  Database connection failed - remaining tests may fail")

        # Test 2: Upload forecast
        print("\nTest 2: Testing upload_forecast...")
        forecast_time = datetime.now(timezone.utc).isoformat()

        # Read and encode audio file as base64
        with open(test_audio_path, 'rb') as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        result = await _call_mcp_tool_remote("upload_forecast", {
            "city": "test-city-upload",
            "forecast_text": "Test forecast: Sunny, 75°F, light winds from the northwest.",
            "audio_data": audio_base64,
            "forecast_at": forecast_time,
            "ttl_minutes": 30,
            "language": "en",
            "locale": "en-US"
        })
        success = result.get("status") == "success"
        print_result("Upload Forecast", result, success)
        test_results["upload_forecast"] = success

        # Test 3: Get storage stats
        print("\nTest 3: Testing get_storage_stats...")
        result = await _call_mcp_tool_remote("get_storage_stats", {})
        success = result.get("status") == "success"
        print_result("Storage Stats", result, success)
        test_results["get_storage_stats"] = success

        # Test 4: List forecasts
        print("\nTest 4: Testing list_forecasts (all cities)...")
        result = await _call_mcp_tool_remote("list_forecasts", {"limit": 5})
        success = result.get("status") == "success"
        print_result("List Forecasts (all)", result, success)
        test_results["list_forecasts_all"] = success

        # Test 5: List forecasts for specific city
        print("\nTest 5: Testing list_forecasts (specific city)...")
        result = await _call_mcp_tool_remote("list_forecasts", {"city": "chicago", "limit": 3})
        success = result.get("status") == "success"
        print_result("List Forecasts (chicago)", result, success)
        test_results["list_forecasts_city"] = success

        # Test 6: Get cached forecast (expect cache miss for test city)
        print("\nTest 6: Testing get_cached_forecast (cache miss expected)...")
        result = await _call_mcp_tool_remote("get_cached_forecast", {"city": "nonexistent-test-city"})
        success = "cached" in result and result.get("cached") == False
        print_result("Get Cached Forecast (miss)", result, success)
        test_results["get_cached_forecast_miss"] = success

        # Test 7: Get cached forecast for real city (may hit or miss)
        print("\nTest 7: Testing get_cached_forecast (chicago)...")
        result = await _call_mcp_tool_remote("get_cached_forecast", {"city": "chicago"})
        success = "cached" in result  # Just check the field exists
        cached = result.get("cached", False)
        cache_status = "HIT" if cached else "MISS"
        print_result(f"Get Cached Forecast (chicago) - {cache_status}", result, success)
        test_results["get_cached_forecast_chicago"] = success

        # Test 8: Cleanup expired forecasts
        print("\nTest 8: Testing cleanup_expired_forecasts...")
        result = await _call_mcp_tool_remote("cleanup_expired_forecasts", {})
        success = result.get("status") == "success"
        print_result("Cleanup Expired Forecasts", result, success)
        test_results["cleanup_expired_forecasts"] = success

        # Print individual test summary
        print(f"\n{'='*60}")
        print("  Individual Test Results")
        print(f"{'='*60}")
        passed = sum(1 for r in test_results.values() if r)
        total = len(test_results)
        print(f"Passed: {passed}/{total}")
        for test_name, success in test_results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {test_name}")

        return all(test_results.values())

    except Exception as e:
        print(f"\n[FAIL] - Local HTTP test failed: {str(e)}")
        print("\nTroubleshooting:")
        print(f"  1. Is MCP server running? Check: curl http://localhost:{port}/messages")
        print(f"  2. Start server: cd forecast_storage_mcp && MCP_TRANSPORT=http PORT={port} python server.py")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup temp audio file
        if test_audio_path and os.path.exists(test_audio_path):
            os.unlink(test_audio_path)


async def test_remote_cloud_run():
    """Test MCP server in remote Cloud Run mode."""
    print_test_header("Testing Remote Cloud Run Mode")

    mcp_url = os.environ.get("MCP_SERVER_URL", "")

    if not mcp_url or "localhost" in mcp_url:
        print("\nWARNING - MCP_SERVER_URL not set or points to localhost.")
        print("Set MCP_SERVER_URL environment variable to test Cloud Run deployment.")
        print("Example: export MCP_SERVER_URL=https://forecast-mcp-server-xxxxx-uc.a.run.app")
        return False

    print(f"\nUsing MCP Server URL: {mcp_url}")

    test_results = {}
    test_audio_path = None

    try:
        # Create a temporary test audio file (minimal WAV file)
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.wav', delete=False) as f:
            # Minimal valid WAV file header
            f.write(b'RIFF')
            f.write((36).to_bytes(4, 'little'))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write((16).to_bytes(4, 'little'))
            f.write((1).to_bytes(2, 'little'))
            f.write((1).to_bytes(2, 'little'))
            f.write((22050).to_bytes(4, 'little'))
            f.write((44100).to_bytes(4, 'little'))
            f.write((2).to_bytes(2, 'little'))
            f.write((16).to_bytes(2, 'little'))
            f.write(b'data')
            f.write((2).to_bytes(4, 'little'))
            f.write(b'\x00\x00')
            test_audio_path = f.name

        # Test 1: Connection test
        print("\nTest 1: Testing database connection...")
        result = await _call_mcp_tool_remote("test_connection", {})
        success = result.get("status") == "success"
        print_result("Connection Test", result, success)
        test_results["test_connection"] = success
        if not success:
            print("⚠️  Database connection failed - remaining tests may fail")

        # Test 2: Upload forecast
        print("\nTest 2: Testing upload_forecast...")
        forecast_time = datetime.now(timezone.utc).isoformat()

        # Read and encode audio file as base64
        with open(test_audio_path, 'rb') as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        result = await _call_mcp_tool_remote("upload_forecast", {
            "city": "test-city-remote-upload",
            "forecast_text": "Remote test forecast: Cloudy, 68°F, moderate winds.",
            "audio_data": audio_base64,
            "forecast_at": forecast_time,
            "ttl_minutes": 30,
            "language": "en",
            "locale": "en-US"
        })
        success = result.get("status") == "success"
        print_result("Upload Forecast", result, success)
        test_results["upload_forecast"] = success

        # Test 3: Get storage stats
        print("\nTest 3: Testing get_storage_stats...")
        result = await _call_mcp_tool_remote("get_storage_stats", {})
        success = result.get("status") == "success"
        print_result("Storage Stats", result, success)
        test_results["get_storage_stats"] = success

        # Test 4: List forecasts
        print("\nTest 4: Testing list_forecasts (all cities)...")
        result = await _call_mcp_tool_remote("list_forecasts", {"limit": 5})
        success = result.get("status") == "success"
        print_result("List Forecasts (all)", result, success)
        test_results["list_forecasts_all"] = success

        # Test 5: List forecasts for specific city
        print("\nTest 5: Testing list_forecasts (specific city)...")
        result = await _call_mcp_tool_remote("list_forecasts", {"city": "chicago", "limit": 3})
        success = result.get("status") == "success"
        print_result("List Forecasts (chicago)", result, success)
        test_results["list_forecasts_city"] = success

        # Test 6: Get cached forecast (expect cache miss)
        print("\nTest 6: Testing get_cached_forecast (cache miss expected)...")
        result = await _call_mcp_tool_remote("get_cached_forecast", {"city": "nonexistent-test-city"})
        success = "cached" in result and result.get("cached") == False
        print_result("Get Cached Forecast (miss)", result, success)
        test_results["get_cached_forecast_miss"] = success

        # Test 7: Get cached forecast for real city
        print("\nTest 7: Testing get_cached_forecast (chicago)...")
        result = await _call_mcp_tool_remote("get_cached_forecast", {"city": "chicago"})
        success = "cached" in result
        cached = result.get("cached", False)
        cache_status = "HIT" if cached else "MISS"
        print_result(f"Get Cached Forecast (chicago) - {cache_status}", result, success)
        test_results["get_cached_forecast_chicago"] = success

        # Test 8: Cleanup expired forecasts
        print("\nTest 8: Testing cleanup_expired_forecasts...")
        result = await _call_mcp_tool_remote("cleanup_expired_forecasts", {})
        success = result.get("status") == "success"
        print_result("Cleanup Expired Forecasts", result, success)
        test_results["cleanup_expired_forecasts"] = success

        # Print individual test summary
        print(f"\n{'='*60}")
        print("  Individual Test Results")
        print(f"{'='*60}")
        passed = sum(1 for r in test_results.values() if r)
        total = len(test_results)
        print(f"Passed: {passed}/{total}")
        for test_name, success in test_results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {test_name}")

        return all(test_results.values())

    except Exception as e:
        print(f"\n[FAIL] - Cloud Run test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup temp audio file
        if test_audio_path and os.path.exists(test_audio_path):
            os.unlink(test_audio_path)


def print_summary(results: Dict[str, bool]):
    """Print test summary."""
    print_test_header("Test Summary")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    print("\nDetailed Results:")
    for test_name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} - {test_name}")

    if failed == 0:
        print("\nAll tests passed!")
    else:
        print(f"\nWARNING: {failed} test(s) failed")
    
    return failed == 0


def print_usage():
    """Print usage instructions."""
    print(__doc__)


async def async_main(mode: str):
    """Async main function to run tests."""
    # Save original URL
    original_url = os.environ.get("MCP_SERVER_URL", "")
    
    results = {}
    
    try:
        if mode in ["local", "all"]:
            # Test localhost HTTP
            port = int(os.environ.get("TEST_MCP_PORT", "8100"))
            os.environ["MCP_SERVER_URL"] = f"http://localhost:{port}"
            results["Local HTTP (localhost)"] = await test_local_http(port)
        
        if mode in ["remote", "all"]:
            # Test Cloud Run
            if original_url and "localhost" not in original_url:
                os.environ["MCP_SERVER_URL"] = original_url
                results["Remote (Cloud Run)"] = await test_remote_cloud_run()
            elif mode == "remote":
                print("\nWARNING: Skipping remote test - MCP_SERVER_URL not set")
                print("Set MCP_SERVER_URL to your Cloud Run URL to test remote mode")
        
        # Print summary
        all_passed = print_summary(results)
        
        return 0 if all_passed else 1
        
    finally:
        # Restore original URL
        os.environ["MCP_SERVER_URL"] = original_url


def main():
    """Main test runner."""
    # Check for help flag
    if len(sys.argv) >= 2 and sys.argv[1] in ["-h", "--help", "help"]:
        print_usage()
        sys.exit(0)

    # Default to "local" if no argument provided
    mode = sys.argv[1] if len(sys.argv) >= 2 else "local"

    if mode not in ["local", "remote", "all"]:
        print(f"Error: Unknown mode '{mode}'")
        print_usage()
        sys.exit(1)

    exit_code = asyncio.run(async_main(mode))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
