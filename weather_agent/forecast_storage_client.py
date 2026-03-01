"""
Direct Supabase Storage Client for Weather Forecasts.

Uploads forecast content directly to Supabase without routing binary data
through an MCP server. Audio and images are stored in Supabase Storage
buckets, and metadata is stored in the Supabase PostgreSQL database.

Schema: see schema.sql for the weather_forecasts table definition.
"""

import os
import uuid
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext
from supabase import create_client, Client
from dotenv import load_dotenv
import httpx

from .write_file import write_audio_file, write_picture_file
from .caching.forecast_file_cleanup import cleanup_old_forecast_files_async

load_dotenv()

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SERVICE_SECRET_KEY")

# Storage bucket names
AUDIO_BUCKET = "weather-audio"
IMAGE_BUCKET = "weather-images"

# Table name
FORECASTS_TABLE = "weather_forecasts"

# Default encoding
TEXT_ENCODING = "utf-8"

# Cache TTL in hours (default 1 hour)
CACHE_TTL = int(os.getenv("CACHE_TTL", "1"))


def _get_supabase_client() -> Optional[Client]:
    """Get Supabase client instance."""
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


def _read_file_bytes(file_path: str) -> Optional[bytes]:
    """Read a file and return its contents as bytes."""
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Failed to read file {file_path}: {e}")
        return None


def _get_content_type(file_path: str) -> str:
    """Get MIME content type from file extension."""
    if not file_path:
        return "application/octet-stream"

    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return content_types.get(ext, "application/octet-stream")


def _get_file_format(file_path: str) -> Optional[str]:
    """Get file format from extension (without dot)."""
    if not file_path:
        return None
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    return ext if ext else None


def _upload_to_storage(
    client: Client,
    bucket: str,
    file_path: str,
    storage_path: str,
) -> tuple[Optional[str], Optional[int]]:
    """
    Upload a file to Supabase Storage.

    Returns tuple of (public_url, file_size_bytes) if successful, (None, None) otherwise.
    """
    file_bytes = _read_file_bytes(file_path)
    if not file_bytes:
        return None, None

    try:
        content_type = _get_content_type(file_path)

        # Upload to storage
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type}
        )

        # Get public URL
        public_url = client.storage.from_(bucket).get_public_url(storage_path)
        file_size = len(file_bytes)
        logger.info(f"Uploaded {file_path} to {bucket}/{storage_path} ({file_size} bytes)")
        return public_url, file_size

    except Exception as e:
        logger.error(f"Failed to upload to storage: {e}")
        return None, None


def _encode_text_to_bytes(text: str, encoding: str = TEXT_ENCODING) -> bytes:
    """Encode text to bytes using specified encoding."""
    return text.encode(encoding)


# Thread pool for async file deletion
_deletion_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="file_cleanup")


def _delete_file(file_path: str) -> None:
    """Delete a single file. Logs errors but does not raise."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted local file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to delete local file {file_path}: {e}")


def _delete_local_files_async(*file_paths: str) -> None:
    """
    Delete local files asynchronously with no delay.

    Submits deletion tasks to a thread pool executor and returns immediately.
    Errors are logged but do not affect the caller.
    """
    for file_path in file_paths:
        if file_path:
            _deletion_executor.submit(_delete_file, file_path)


async def upload_forecast_to_storage(
    callback_context: CallbackContext
) -> None:
    """
    Upload complete forecast (text + audio + picture) directly to Supabase.

    Reads content from agent session state, uploads files to Supabase Storage,
    and stores metadata in the database.

    Args:
        callback_context: Agent callback context
    """
    # Get Supabase client
    client = _get_supabase_client()
    if not client:
        logger.error("Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_SECRET_KEY.")
        return

    city = callback_context.state["CITY"]
    forecast_text = callback_context.state["FORECAST_TEXT"]
    audio_file_path = callback_context.state.get("FORECAST_AUDIO")
    picture_file_path = callback_context.state.get("FORECAST_PICTURE")
    forecast_at = callback_context.state.get("FORECAST_TIMESTAMP")

    # Parse timestamp
    if forecast_at:
        try:
            dt = datetime.strptime(forecast_at, "%Y-%m-%d_%H%M%S")
            dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    published_at = dt.isoformat()
    expires_at = (dt + timedelta(hours=CACHE_TTL)).isoformat()

    # Generate unique ID for this forecast
    forecast_id = str(uuid.uuid4())

    # Encode text content to bytes (schema uses BYTEA for forecast_text)
    content_bytes = _encode_text_to_bytes(forecast_text)
    text_size_bytes = len(content_bytes)

    # Initialize upload results
    audio_url = None
    audio_size_bytes = None
    audio_format = None
    image_url = None
    image_size_bytes = None
    image_format = None

    # Upload audio and image files in parallel
    upload_futures = {}
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="media_upload") as executor:
        # Submit audio upload task
        if audio_file_path and os.path.exists(audio_file_path):
            audio_format = _get_file_format(audio_file_path)
            ext = os.path.splitext(audio_file_path)[1] or ".wav"
            storage_path = f"{forecast_id}/audio{ext}"
            future = executor.submit(_upload_to_storage, client, AUDIO_BUCKET, audio_file_path, storage_path)
            upload_futures[future] = "audio"

        # Submit image upload task
        if picture_file_path and os.path.exists(picture_file_path):
            image_format = _get_file_format(picture_file_path)
            ext = os.path.splitext(picture_file_path)[1] or ".png"
            storage_path = f"{forecast_id}/image{ext}"
            future = executor.submit(_upload_to_storage, client, IMAGE_BUCKET, picture_file_path, storage_path)
            upload_futures[future] = "image"

        # Collect results as uploads complete
        for future in as_completed(upload_futures):
            upload_type = upload_futures[future]
            try:
                url, size_bytes = future.result()
                if upload_type == "audio":
                    audio_url, audio_size_bytes = url, size_bytes
                else:
                    image_url, image_size_bytes = url, size_bytes
            except Exception as e:
                logger.error(f"Failed to upload {upload_type}: {e}")

    # Build metadata
    metadata = {
        "city": city,
        "original_timestamp": forecast_at,
    }
    if audio_file_path:
        metadata["local_audio_path"] = audio_file_path
    if picture_file_path:
        metadata["local_image_path"] = picture_file_path

    # Insert forecast record into database (matching schema.sql)
    try:
        record = {
            "id": forecast_id,
            "city": city,
            "forecast_at": published_at,
            "expires_at": expires_at,
            # Text content as BYTEA - use hex encoding for Supabase
            "forecast_text": f"\\x{content_bytes.hex()}",
            "text_size_bytes": text_size_bytes,
            "text_encoding": TEXT_ENCODING,
            "text_language": "en",
            "text_locale": "en-US",
            # Audio fields
            "audio_url": audio_url,
            "audio_size_bytes": audio_size_bytes,
            "audio_format": audio_format,
            # Image fields
            "image_url": image_url,
            "image_size_bytes": image_size_bytes,
            "image_format": image_format,
            # Metadata
            "metadata": metadata,
        }

        result = client.table(FORECASTS_TABLE).insert(record).execute()

        if not result.data:
            logger.error("Failed to insert forecast record into database.")
            return

        logger.info(f"Uploaded forecast {forecast_id} for {city}")

    except Exception as e:
        logger.error(f"Database insert failed: {e}")
        return

    # Store results in session state
    callback_context.state["CLOUD_FORECAST_ID"] = forecast_id
    if audio_url:
        callback_context.state["CLOUD_AUDIO_URL"] = audio_url
    if image_url:
        callback_context.state["CLOUD_IMAGE_URL"] = image_url

    # Delete local files asynchronously after successful upload
    text_file_path = callback_context.state.get("FORECAST_TEXT_FILE")
    _delete_local_files_async(audio_file_path, picture_file_path, text_file_path)

    # Fire-and-forget async cleanup of old local files
    asyncio.create_task(cleanup_old_forecast_files_async())


async def get_cached_forecast_from_storage(
    tool_context: ToolContext,
    city: str
) -> Dict[str, Any]:
    """
    Retrieve cached forecast from Supabase if available.

    Queries the weather_forecasts table for a non-expired forecast for the given city.
    If found, downloads audio and picture files from Supabase Storage.

    Args:
        tool_context: ADK tool context
        city: City name to check

    Returns:
        Dictionary with cache status and forecast data if cached
    """
    client = _get_supabase_client()
    if not client:
        return {
            "cached": False,
            "forecast_text": None,
            "audio_filepath": None,
            "picture_filepath": None,
        }

    try:
        now = datetime.now(timezone.utc).isoformat()

        # Query for non-expired forecast for this city
        result = client.table(FORECASTS_TABLE) \
            .select("*") \
            .eq("city", city) \
            .gt("expires_at", now) \
            .order("forecast_at", desc=True) \
            .limit(1) \
            .execute()

        if not result.data:
            return {
                "cached": False,
                "forecast_text": None,
                "audio_filepath": None,
                "picture_filepath": None,
            }

        record = result.data[0]

        # Decode forecast text from BYTEA hex
        forecast_text = None
        raw_text = record.get("forecast_text")
        if raw_text:
            try:
                encoding = record.get("text_encoding", "utf-8")
                if isinstance(raw_text, str) and raw_text.startswith("\\x"):
                    forecast_text = bytes.fromhex(raw_text[2:]).decode(encoding)
                else:
                    forecast_text = raw_text
            except Exception as e:
                logger.error(f"Failed to decode forecast text: {e}")

        # Calculate age
        forecast_at = record.get("forecast_at", "")
        age_seconds = 0
        if forecast_at:
            try:
                ft = datetime.fromisoformat(forecast_at)
                age_seconds = int((datetime.now(timezone.utc) - ft).total_seconds())
            except Exception:
                pass

        # Download audio file from Supabase Storage if available
        audio_filepath = None
        audio_url = record.get("audio_url")
        if audio_url:
            audio_filepath = await _download_file_from_url(
                tool_context, city, audio_url, "audio"
            )

        # Download picture file from Supabase Storage if available
        picture_filepath = None
        image_url = record.get("image_url")
        if image_url:
            picture_filepath = await _download_file_from_url(
                tool_context, city, image_url, "image"
            )

        return {
            "cached": True,
            "forecast_text": forecast_text,
            "audio_filepath": audio_filepath,
            "picture_filepath": picture_filepath,
            "age_seconds": age_seconds,
            "forecast_at": forecast_at,
            "expires_at": record.get("expires_at", ""),
        }

    except Exception as e:
        logger.error(f"Failed to query cached forecast: {e}")
        return {
            "cached": False,
            "forecast_text": None,
            "audio_filepath": None,
            "picture_filepath": None,
        }


async def _download_file_from_url(
    tool_context: ToolContext,
    city: str,
    url: str,
    file_type: str
) -> Optional[str]:
    """
    Download a file from a Supabase Storage URL and save locally.

    Args:
        tool_context: ADK tool context
        city: City name (for directory structure)
        url: Public URL to download from
        file_type: "audio" or "image"

    Returns:
        Local file path or None if download failed
    """
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(url, follow_redirects=True)
            response.raise_for_status()
            file_bytes = response.content

        if file_type == "audio":
            # write_audio_file expects base64 string or raw bytes
            # Pass raw WAV bytes directly - the file from storage is already WAV
            result = write_audio_file(tool_context, city, file_bytes)
            return result.get("file_path")
        else:
            # write_picture_file expects image_data as bytes
            # Detect format from URL
            ext = os.path.splitext(url.split("?")[0])[1].lstrip(".")
            fmt = ext if ext else "png"
            result = write_picture_file(tool_context, city, file_bytes, fmt)
            return result.get("file_path")

    except Exception as e:
        logger.error(f"Failed to download {file_type} from {url}: {e}")
        return None
