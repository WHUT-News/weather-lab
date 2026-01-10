"""
MCP Client Wrapper for Forecast Storage.

Provides simple functions for the weather agent to interact with the
forecast storage MCP server without dealing with MCP protocol details.
"""

import os
import json
import asyncio
from typing import Dict, Any

from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext

import logging
import google.cloud.logging
import httpx
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

from .write_file import write_audio_file
from .caching.forecast_file_cleanup import cleanup_old_forecast_files_async

# MCP Server URL - base URL for MCP server
# Set to localhost for local development or Cloud Run URL for production
# Example: http://localhost:8080 or https://forecast-mcp-server-xxxxx.run.app
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080")


async def _call_mcp_tool_remote(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call MCP server via SSE transport using official MCP client.

    Args:
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments as dictionary

    Returns:
        Tool result as dictionary
    """
    try:
        # Connect using SSE transport - MCP client expects the /sse endpoint
        base_url = MCP_SERVER_URL.rstrip('/')
        sse_url = f"{base_url}/sse"

        async with sse_client(sse_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()

                # Call the tool
                result = await session.call_tool(tool_name, arguments)

                # Parse result - MCP returns list of TextContent objects
                if result and len(result.content) > 0:
                    # Extract text from first content item
                    text_content = result.content[0].text
                    if not text_content or text_content.strip() == "":
                        logging.error(f"Empty text content from MCP server for tool: {tool_name}")
                        return {
                            "status": "error",
                            "message": "Empty text content from MCP server"
                        }
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse MCP response as JSON: {text_content[:200]}")
                        return {
                            "status": "error",
                            "message": f"Invalid JSON response from server: {str(e)}"
                        }

                return {
                    "status": "error",
                    "message": "Empty response from MCP server"
                }

    except httpx.ConnectError as e:
        return {
            "status": "error",
            "message": f"Cannot connect to MCP server at {MCP_SERVER_URL}. Make sure the server is running."
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"MCP call error: {error_details}")
        return {
            "status": "error",
            "message": f"MCP call failed: {str(e)}",
            "details": error_details
        }


async def upload_forecast_to_storage(
    callback_context: CallbackContext
) -> None:
    """
    Upload complete forecast (text + audio) to Cloud SQL storage.

    This is an ADK tool that wraps the MCP upload_forecast tool.

    Args:
        callback_context: Agent callback context

    Returns:
        None
    """
    import base64

    city = callback_context.state["CITY"]
    forecast_text = callback_context.state["FORECAST_TEXT"]
    audio_file_path = callback_context.state["FORECAST_AUDIO"]
    forecast_at = callback_context.state["FORECAST_TIMESTAMP"]
    ttl_minutes = 30  # Default TTL in minutes

    # Read audio file and encode as base64 (MCP server may be remote and can't access local files)
    try:
        with open(audio_file_path, 'rb') as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        logging.error(f"Failed to read audio file {audio_file_path}: {e}")
        return

    # Read picture file if available and encode as base64
    picture_file_path = callback_context.state.get("FORECAST_PICTURE")
    picture_base64 = None
    picture_format = "png"

    if picture_file_path:
        try:
            with open(picture_file_path, 'rb') as f:
                picture_bytes = f.read()
                picture_base64 = base64.b64encode(picture_bytes).decode('utf-8')

            # Extract format from file extension
            _, ext = os.path.splitext(picture_file_path)
            picture_format = ext.lstrip('.')  # Remove leading dot
        except Exception as e:
            logging.error(f"Failed to read picture file {picture_file_path}: {e}")
            # Continue without picture - it's optional

    result = await _call_mcp_tool_remote("upload_forecast", {
        "city": city,
        "forecast_text": forecast_text,
        "audio_data": audio_base64,
        "picture_data": picture_base64,
        "picture_format": picture_format,
        "forecast_at": forecast_at,
        "ttl_minutes": ttl_minutes,
        "language": "en",  # Could be made configurable
        "locale": "en-US"
    })
    
    # callback doesn't support any return. Use logging instead.
    logging_client = google.cloud.logging.Client()
    logging_client.setup_logging()

    if result.get("status") == "success":
        logging.info({
            "status": "success",
            "message": f"Forecast uploaded to Cloud SQL storage",
            "forecast_id": result.get("forecast_id", ""),
            "storage_info": json.dumps(result.get("sizes", {}))
        })
        
    else:
        logging.error({
            "status": "error",
            "message": f"Upload failed: {result.get('message', 'Unknown error')}"
        })
        
    # Fire-and-forget async cleanup (no await, no return value needed)
    # This runs in the background and doesn't block the upload response
    asyncio.create_task(cleanup_old_forecast_files_async())


async def download_and_write_picture(
    tool_context: ToolContext,
    city: str,
    picture_url: str
) -> str | None:
    """
    Download picture from GCS URL and write to local file.

    Args:
        tool_context: ADK tool context
        city: City name
        picture_url: GCS URL (gs://bucket/path/file.png)

    Returns:
        Local file path or None if download failed
    """
    try:
        from google.cloud import storage

        # Parse gs://bucket/path/file.png
        if not picture_url.startswith("gs://"):
            logging.error(f"Invalid GCS URL format: {picture_url}")
            return None

        parts = picture_url[5:].split("/", 1)
        bucket_name = parts[0]
        blob_name = parts[1]

        # Download from GCS
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        picture_bytes = blob.download_as_bytes()

        # Write locally using existing write_picture_file
        _, ext = os.path.splitext(picture_url)
        format = ext.lstrip('.') or 'png'

        from .write_file import write_picture_file
        result = write_picture_file(tool_context, city, picture_bytes, format)
        return result.get("file_path")

    except Exception as e:
        logging.error(f"Failed to download picture from {picture_url}: {e}")
        return None


async def get_cached_forecast_from_storage(
    tool_context: ToolContext,
    city: str
) -> Dict[str, Any]:
    """
    Retrieve cached forecast from Cloud SQL storage if available.

    This is an ADK tool that wraps the MCP get_cached_forecast tool.

    Args:
        tool_context: ADK tool context
        city: City name to check

    Returns:
        Dictionary with cache status and forecast data if cached
    """
    result = await _call_mcp_tool_remote("get_cached_forecast", {
        "city": city
    })
    
    if result.get("cached"):
        # Cache hit - return forecast data
        # store audio_data into a file using write_audio_file tool
        audio_file = write_audio_file(tool_context, city, result.get("audio_data", ""))

        # Download picture from GCS if available
        picture_url = result.get("picture_url")
        picture_filepath = None

        if picture_url:
            picture_filepath = await download_and_write_picture(
                tool_context,
                city,
                picture_url
            )

        return {
            "cached": True,
            "forecast_text": result.get("forecast_text", ""),
            "audio_filepath": audio_file.get("file_path", None),
            "picture_filepath": picture_filepath,
            "age_seconds": result.get("age_seconds", 0),
            "forecast_at": result.get("forecast_at", ""),
            "expires_at": result.get("expires_at", ""),
        }
    else:
        # Cache miss
        return {
            "cached": False,
            "forecast_text": None,
            "audio_filepath": None,
            "picture_filepath": None,
        }


async def get_storage_stats_from_mcp(
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get storage statistics from Cloud SQL.

    This is an ADK tool that wraps the MCP get_storage_stats tool.

    Args:
        tool_context: ADK tool context

    Returns:
        Dictionary with storage statistics
    """
    result = await _call_mcp_tool_remote("get_storage_stats", {})
    
    if result.get("status") == "success":
        return {
            "status": "success",
            "total_forecasts": result.get("total_forecasts", 0),
            "total_text_bytes": result.get("total_text_bytes", 0),
            "total_audio_bytes": result.get("total_audio_bytes", 0),
            "city_breakdown": json.dumps(result.get("city_breakdown", []))
        }
    else:
        return {
            "status": "error",
            "message": result.get("message", "Failed to get stats")
        }


async def test_storage_connection(
    tool_context: ToolContext
) -> Dict[str, str]:
    """
    Test connection to Cloud SQL storage.

    This is an ADK tool that wraps the MCP test_connection tool.

    Args:
        tool_context: ADK tool context

    Returns:
        Dictionary with connection status
    """
    result = await _call_mcp_tool_remote("test_connection", {})
    
    if result.get("status") == "success":
        return {
            "status": "connected",
            "message": f"Connected to {result.get('instance', 'Cloud SQL')}",
            "database": result.get("database", ""),
            "table_exists": str(result.get("forecasts_table_exists", False))
        }
    else:
        return {
            "status": "error",
            "message": f"Connection failed: {result.get('error', 'Unknown error')}"
        }
