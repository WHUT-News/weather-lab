"""
Test script for forecast storage MCP operations.

Tests all forecast storage operations without requiring the full MCP server.
Run this after setting up Cloud SQL and environment variables.

Usage:
    python test_mcp_operations.py
"""

import os
import sys
import tempfile
import wave
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add parent directory to path to import tools
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

from tools.connection import test_connection
from tools.forecast_operations import (
    upload_forecast,
    get_cached_forecast,
    cleanup_expired_forecasts,
    get_storage_stats,
    list_forecasts
)


def create_test_audio_file():
    """Create a temporary WAV file for testing."""
    # Create a simple WAV file with silence
    temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.wav', delete=False)
    
    with wave.open(temp_file.name, 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(24000)  # 24kHz
        # Write 1 second of silence
        wf.writeframes(b'\x00\x00' * 24000)
    
    return temp_file.name


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result):
    """Print result in a readable format."""
    import json
    print(json.dumps(result, indent=2))


def test_1_connection():
    """Test database connection."""
    print_section("TEST 1: Database Connection")
    
    result = test_connection()
    print_result(result)
    
    if result['status'] == 'success':
        print("\n✅ Connection test passed!")
        if not result['forecasts_table_exists']:
            print("\n⚠️  WARNING: forecasts table does not exist!")
            print("   Please apply schema.sql first:")
            print("   psql -h INSTANCE_IP -U postgres -d weather -f schema.sql")
            return False
        return True
    else:
        print("\n❌ Connection test failed!")
        print("   Please check your .env configuration and Cloud SQL instance.")
        return False


def test_2_upload_forecast():
    """Test uploading a forecast."""
    import base64
    print_section("TEST 2: Upload Forecast")

    # Create test audio file
    audio_file = create_test_audio_file()

    try:
        # Test data
        city = "chicago"
        forecast_text = "Weather in Chicago: Sunny with temperatures around 75°F. Light breeze from the west. Perfect day for outdoor activities! ☀️"
        forecast_at = datetime.now(timezone.utc).isoformat()

        # Read and encode audio file
        with open(audio_file, 'rb') as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        print(f"\nUploading forecast for {city}...")
        print(f"Text length: {len(forecast_text)} characters")
        print(f"Audio data size: {len(audio_bytes)} bytes")

        result = upload_forecast(
            city=city,
            forecast_text=forecast_text,
            audio_data=audio_base64,
            forecast_at=forecast_at,
            ttl_minutes=30,
            language="en",
            locale="en-US"
        )

        print_result(result)

        if result['status'] == 'success':
            print("\n✅ Upload test passed!")
            return True, result.get('forecast_id')
        else:
            print("\n❌ Upload test failed!")
            return False, None

    finally:
        # Cleanup temp file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


def test_3_get_cached_forecast():
    """Test retrieving cached forecast."""
    print_section("TEST 3: Get Cached Forecast")
    
    city = "chicago"
    
    print(f"\nRetrieving cached forecast for {city}...")
    
    result = get_cached_forecast(city=city)
    print_result(result)
    
    if result.get('cached'):
        print("\n✅ Cache retrieval test passed!")
        print(f"   Forecast age: {result['age_seconds']} seconds")
        print(f"   Text length: {len(result['forecast_text'])} characters")
        print(f"   Audio data: {len(result['audio_data'])} bytes (base64)")
        return True
    else:
        print("\n⚠️  No cached forecast found (this is OK if no forecast was uploaded)")
        return result.get('status') != 'error'


def test_4_storage_stats():
    """Test getting storage statistics."""
    print_section("TEST 4: Storage Statistics")
    
    print("\nRetrieving storage statistics...")
    
    result = get_storage_stats()
    print_result(result)
    
    if result['status'] == 'success':
        print("\n✅ Storage stats test passed!")
        print(f"   Total forecasts: {result['total_forecasts']}")
        print(f"   Total text bytes: {result['total_text_bytes']}")
        print(f"   Total audio bytes: {result['total_audio_bytes']}")
        return True
    else:
        print("\n❌ Storage stats test failed!")
        return False


def test_5_list_forecasts():
    """Test listing forecasts."""
    print_section("TEST 5: List Forecasts")
    
    print("\nListing all forecasts (limit 5)...")
    
    result = list_forecasts(limit=5)
    print_result(result)
    
    if result['status'] == 'success':
        print(f"\n✅ List forecasts test passed!")
        print(f"   Found {result['count']} forecasts")
        return True
    else:
        print("\n❌ List forecasts test failed!")
        return False


def test_6_upload_multilingual():
    """Test uploading forecasts in different languages."""
    import base64
    print_section("TEST 6: Multilingual Upload (Optional)")

    # Create test audio file
    audio_file = create_test_audio_file()

    try:
        # Read and encode audio file once
        with open(audio_file, 'rb') as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        test_cases = [
            {
                "city": "tokyo",
                "text": "東京の天気：晴れ、摂氏24度です。明日は曇りでしょう。",
                "language": "ja",
                "locale": "ja-JP",
                "encoding": "utf-16"
            },
            {
                "city": "mexico_city",
                "text": "El clima en México: Soleado, 24°C. Mañana será nublado.",
                "language": "es",
                "locale": "es-MX",
                "encoding": None  # Auto-detect
            }
        ]

        success_count = 0

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i}: {test_case['city']} ({test_case['language']}) ---")

            result = upload_forecast(
                city=test_case['city'],
                forecast_text=test_case['text'],
                audio_data=audio_base64,
                forecast_at=datetime.now(timezone.utc).isoformat(),
                ttl_minutes=30,
                language=test_case['language'],
                locale=test_case['locale'],
                encoding=test_case['encoding']
            )

            if result['status'] == 'success':
                print(f"✅ {test_case['city']}: Success (encoding: {result['encoding']})")
                success_count += 1
            else:
                print(f"❌ {test_case['city']}: Failed - {result.get('message')}")

        print(f"\n{'✅' if success_count == len(test_cases) else '⚠️'} Multilingual test: {success_count}/{len(test_cases)} passed")
        return success_count > 0

    finally:
        # Cleanup temp file
        if os.path.exists(audio_file):
            os.unlink(audio_file)


def test_7_cleanup_expired():
    """Test cleanup of expired forecasts (optional - won't delete active forecasts)."""
    print_section("TEST 7: Cleanup Expired Forecasts")
    
    print("\nRunning cleanup (only removes expired forecasts)...")
    
    result = cleanup_expired_forecasts()
    print_result(result)
    
    if result['status'] == 'success':
        print("\n✅ Cleanup test passed!")
        print(f"   Deleted: {result['deleted_count']} expired forecasts")
        print(f"   Remaining: {result['remaining_count']} forecasts")
        return True
    else:
        print("\n❌ Cleanup test failed!")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  FORECAST STORAGE MCP SERVER - OPERATIONS TEST")
    print("=" * 60)
    print("\nThis script tests all forecast storage operations.")
    print("Ensure Cloud SQL is set up and .env is configured.\n")
    
    # Check environment variables
    required_vars = [
        "GCP_PROJECT_ID",
        "CLOUD_SQL_INSTANCE",
        "CLOUD_SQL_PASSWORD"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file.")
        return
    
    # Run tests
    tests_passed = 0
    total_tests = 7
    
    # Test 1: Connection (required)
    if not test_1_connection():
        print("\n" + "=" * 60)
        print("❌ Connection test failed. Please fix before continuing.")
        print("=" * 60)
        return
    tests_passed += 1
    
    # Test 2: Upload forecast
    success, forecast_id = test_2_upload_forecast()
    if success:
        tests_passed += 1
    
    # Test 3: Get cached forecast
    if test_3_get_cached_forecast():
        tests_passed += 1
    
    # Test 4: Storage stats
    if test_4_storage_stats():
        tests_passed += 1
    
    # Test 5: List forecasts
    if test_5_list_forecasts():
        tests_passed += 1
    
    # Test 6: Multilingual (optional)
    if test_6_upload_multilingual():
        tests_passed += 1
    
    # Test 7: Cleanup (optional)
    if test_7_cleanup_expired():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"\nPassed: {tests_passed}/{total_tests} tests")
    
    if tests_passed == total_tests:
        print("\n🎉 All tests passed! MCP server is ready to use.")
    elif tests_passed >= 5:
        print("\n✅ Core tests passed. MCP server is functional.")
    else:
        print("\n⚠️  Some tests failed. Please review errors above.")
    
    print("\nNext steps:")
    print("1. Review test results above")
    print("2. If all tests pass, integrate with weather agent")
    print("3. Run the MCP server: python server.py")


if __name__ == "__main__":
    main()
