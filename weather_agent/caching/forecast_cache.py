"""
Root-level complete forecast caching using filesystem as source of truth.

This module checks the actual output files (text + audio) in the OUTPUT_DIR to determine
if a recent forecast exists. Files with timestamps within the TTL are considered valid cache.

Cache Logic:
- Scans OUTPUT_DIR/{city}/ for forecast_text_*.txt and forecast_audio_*.wav files
- Parses timestamps from filenames (format: forecast_text_YYYYMMDD_HHMMSS.txt)
- Returns most recent pair if both text and audio files exist within TTL
- TTL: Configurable via CACHE_TTL env var in hours (default: 1 hour)

Benefits:
- No in-memory state to manage
- Survives application restarts
- Filesystem is the single source of truth
- Easy to debug and inspect
"""

import os
import time
import glob
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from google.adk.tools import ToolContext


# Cache TTL: configurable via environment variable in hours (default: 1 hour)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL", "1")) * 3600

# Get output directory from environment
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")


def _parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """
    Parse timestamp from forecast filename.

    Expected formats:
    - forecast_text_YYYYMMDD_HHMMSS.txt
    - forecast_audio_YYYYMMDD_HHMMSS.wav

    Args:
        filename: Filename to parse

    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Extract timestamp part: YYYY-MM-DD_HHMMSS
        # Example: forecast_text_2025-12-25_143022.txt -> 2025-12-25_143022
        parts = filename.split('_')
        if len(parts) >= 3:
            # Handle format: forecast_text_2025-12-25_143022.txt
            # parts = ['forecast', 'text', '2025-12-25', '143022.txt']
            date_part = parts[-2]  # 2025-12-25
            time_part = parts[-1].split('.')[0]  # 143022 (remove extension)
            timestamp_str = f"{date_part}_{time_part}"
            return datetime.strptime(timestamp_str, "%Y-%m-%d_%H%M%S")
    except (ValueError, IndexError):
        pass
    return None


def _get_file_age_seconds(filepath: str) -> Optional[float]:
    """
    Get age of file in seconds based on filename timestamp.

    Args:
        filepath: Full path to file

    Returns:
        Age in seconds or None if timestamp couldn't be parsed
    """
    filename = os.path.basename(filepath)
    file_dt = _parse_timestamp_from_filename(filename)

    if file_dt:
        current_dt = datetime.now(timezone.utc)
        age = (current_dt - file_dt).total_seconds()
        return age

    return None


def get_forecast_from_cache(tool_context: ToolContext, city: str) -> Dict[str, Any]:
    """
    Check if a complete forecast (text + audio) exists in filesystem for the given city.

    Scans the OUTPUT_DIR/{city}/ folder for forecast files and checks if they're within TTL.

    Args:
        tool_context: The tool context (required by ADK)
        city: City name to check

    Returns:
        Dictionary with:
        - 'cached': bool - True if valid cache exists
        - 'forecast_text': str or None - Cached forecast text
        - 'text_file_path': str or None - Path to text file
        - 'audio_file_path': str or None - Path to audio file
        - 'age_seconds': int - Age of cached files
    """
    city_dir = os.path.join(OUTPUT_DIR, city)

    # Check if city directory exists
    if not os.path.exists(city_dir):
        return {
            'cached': False,
            'forecast_text': None,
            'text_file_path': None,
            'audio_file_path': None,
            'age_seconds': None
        }

    # Find all text and audio files
    text_files = glob.glob(os.path.join(city_dir, "forecast_text_*.txt"))
    audio_files = glob.glob(os.path.join(city_dir, "forecast_audio_*.wav"))

    if not text_files or not audio_files:
        return {
            'cached': False,
            'forecast_text': None,
            'text_file_path': None,
            'audio_file_path': None,
            'age_seconds': None
        }

    # Find most recent text file within TTL
    valid_text_file = None
    text_age = None
    for text_file in sorted(text_files, reverse=True):  # Most recent first
        age = _get_file_age_seconds(text_file)
        if age is not None and age < CACHE_TTL_SECONDS:
            valid_text_file = text_file
            text_age = age
            break

    if not valid_text_file:
        return {
            'cached': False,
            'forecast_text': None,
            'text_file_path': None,
            'audio_file_path': None,
            'age_seconds': None
        }

    # Find corresponding audio file with same or similar timestamp
    text_filename = os.path.basename(valid_text_file)
    text_timestamp = _parse_timestamp_from_filename(text_filename)

    valid_audio_file = None
    for audio_file in audio_files:
        audio_age = _get_file_age_seconds(audio_file)
        if audio_age is not None and audio_age < CACHE_TTL_SECONDS:
            # Check if audio timestamp matches text timestamp (within 1 minute)
            audio_filename = os.path.basename(audio_file)
            audio_timestamp = _parse_timestamp_from_filename(audio_filename)

            if text_timestamp and audio_timestamp:
                time_diff = abs((text_timestamp - audio_timestamp).total_seconds())
                if time_diff < 60:  # Within 1 minute of each other
                    valid_audio_file = audio_file
                    break

    if not valid_audio_file:
        return {
            'cached': False,
            'forecast_text': None,
            'text_file_path': None,
            'audio_file_path': None,
            'age_seconds': None
        }

    # Read forecast text from file
    try:
        with open(valid_text_file, 'r', encoding='utf-8') as f:
            forecast_text = f.read()
    except Exception:
        forecast_text = None

    return {
        'cached': True,
        'forecast_text': forecast_text,
        'text_file_path': valid_text_file,
        'audio_file_path': valid_audio_file,
        'age_seconds': int(text_age)
    }


def cache_forecast(
    tool_context: ToolContext,
    city: str,
    forecast_text: str,
    text_file_path: str,
    audio_file_path: str
) -> Dict[str, str]:
    """
    No-op function for filesystem-based caching.

    Since files are already written to disk by sub-agents, this function
    simply confirms the files exist and returns status.

    Args:
        tool_context: The tool context (required by ADK)
        city: City name
        forecast_text: The generated forecast text (not used)
        text_file_path: Path to the text file
        audio_file_path: Path to the audio file

    Returns:
        Dictionary with status
    """
    text_exists = os.path.exists(text_file_path) if text_file_path else False
    audio_exists = os.path.exists(audio_file_path) if audio_file_path else False

    return {
        'status': 'files_exist' if (text_exists and audio_exists) else 'incomplete',
        'text_file': text_file_path,
        'audio_file': audio_file_path,
        'text_exists': str(text_exists),
        'audio_exists': str(audio_exists),
        'ttl_readable': f'{CACHE_TTL_SECONDS // 60} minutes'
    }


def get_cache_stats(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get statistics about forecast files in the filesystem.

    Args:
        tool_context: The tool context (required by ADK)

    Returns:
        Dictionary with cache statistics
    """
    if not os.path.exists(OUTPUT_DIR):
        return {
            'total_cities': 0,
            'cities_with_valid_cache': 0,
            'cached_cities': [],
            'ttl_seconds': CACHE_TTL_SECONDS,
            'ttl_readable': f'{CACHE_TTL_SECONDS // 60} minutes'
        }

    # Scan all city directories
    city_dirs = [d for d in os.listdir(OUTPUT_DIR)
                 if os.path.isdir(os.path.join(OUTPUT_DIR, d))]

    cities_with_valid_cache = []

    for city in city_dirs:
        # Check if this city has valid cache
        result = get_forecast_from_cache(tool_context, city)
        if result['cached']:
            cities_with_valid_cache.append(city)

    return {
        'total_cities': len(city_dirs),
        'cities_with_valid_cache': len(cities_with_valid_cache),
        'cached_cities': cities_with_valid_cache,
        'ttl_seconds': CACHE_TTL_SECONDS,
        'ttl_readable': f'{CACHE_TTL_SECONDS // 60} minutes'
    }


def cleanup_expired(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Remove expired forecast files from the filesystem.

    Deletes text and audio files older than TTL (30 minutes).

    Args:
        tool_context: The tool context (required by ADK)

    Returns:
        Dictionary with cleanup stats
    """
    if not os.path.exists(OUTPUT_DIR):
        return {
            'status': 'no_cache_dir',
            'expired_removed': 0,
            'remaining_files': 0
        }

    expired_removed = 0
    remaining_files = 0

    # Scan all city directories
    for city in os.listdir(OUTPUT_DIR):
        city_dir = os.path.join(OUTPUT_DIR, city)
        if not os.path.isdir(city_dir):
            continue

        # Check all forecast files
        all_files = (glob.glob(os.path.join(city_dir, "forecast_*.txt")) +
                     glob.glob(os.path.join(city_dir, "forecast_*.wav")))

        for file in all_files:
            age = _get_file_age_seconds(file)
            if age is not None and age >= CACHE_TTL_SECONDS:
                os.remove(file)
                expired_removed += 1
            else:
                remaining_files += 1

    return {
        'status': 'cleaned',
        'expired_removed': expired_removed,
        'remaining_files': remaining_files
    }
