"""
Weather forecast endpoints.
"""
from fastapi import APIRouter, Query, Path
from typing import Optional
import asyncio

from api.models.responses import (
    WeatherResponse,
    WeatherNotFoundResponse,
    HistoryResponse,
    ErrorResponse
)
from core.database import get_cached_forecast, list_forecasts
from core.exceptions import ForecastNotFoundError, DatabaseConnectionError
from datetime import datetime
import vertexai
from vertexai import agent_engines
from config import settings

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

def trigger_forecast_preparation(city: str, language: Optional[str] = None):
    """
    Trigger async forecast preparation using Vertex AI agent engine.

    Args:
        city: City name to prepare forecast for
        language: Optional language code for the forecast
    """
    if not settings.AGENT_ENGINE_ID:
        return

    vertexai.init(
        project=settings.GOOGLE_CLOUD_PROJECT, 
        location=settings.GOOGLE_CLOUD_LOCATION
    )

    try:
        # Get the deployed agent engine
        agent = agent_engines.get(settings.AGENT_ENGINE_ID)

        # Create prompt for forecast generation
        language_spec = f" in {language}" if language else ""
        prompt = f"What is the current weather condition in the city of {city} {language_spec}"

        # Use stream_query since the agent supports 'stream' mode
        session_id = f"user_request_{city}_{language or 'default'}"

        # Collect the streamed response
        response_chunks = []
        for chunk in agent.stream_query(
            input=prompt,
            config={"configurable": {"session_id": session_id}}
        ):
            response_chunks.append(chunk)
            logger.debug(f"Received chunk: {chunk}")

        # Log the complete result
        logger.info(f"Forecast generated for {city}: {response_chunks}")
    except Exception as agent_error:
        # Log agent error but don't fail the request
        logger.warning(f"Failed to trigger forecast for {city}: {str(agent_error)}")
        import traceback
        logger.warning(f"Traceback: {traceback.format_exc()}")


@router.get(
    "/{city}",
    response_model=WeatherResponse,
    responses={
        200: {"description": "Successful response with forecast data"},
        404: {"model": WeatherNotFoundResponse, "description": "Forecast not found"},
        503: {"model": ErrorResponse, "description": "Database connection error"}
    },
    summary="Get latest forecast for a city",
    description="Retrieves the most recent valid (non-expired) forecast for the specified city"
)
async def get_latest_forecast(
    city: str = Path(..., description="City name (case-insensitive)"),
    language: Optional[str] = Query(None, description="ISO 639-1 language code filter")
):
    """Get the latest forecast for a city"""
    try:
        result = get_cached_forecast(city, language)

        if result.get("status") == "error":
            raise DatabaseConnectionError(result.get("message", "Database error"))

        if not result.get("cached"):
            raise ForecastNotFoundError(city)

        return {
            "status": "success",
            "city": city.lower(),
            "forecast": {
                "text": result["forecast_text"],
                "audio_base64": result["audio_data"],
                "forecast_at": result["forecast_at"],
                "expires_at": result["expires_at"],
                "age_seconds": result["age_seconds"],
                "metadata": {
                    "encoding": result["encoding"],
                    "language": result.get("language"),
                    "locale": result.get("locale"),
                    "sizes": result["sizes"]
                }
            }
        }
    except ForecastNotFoundError as e:
        # Trigger async forecast preparation when forecast not found (non-blocking)
        logger.warning(f"triggering forecast preparation for {city}: {str(e)}")
        trigger_forecast_preparation(city, language)

        # Still raise the original error
        raise
    except DatabaseConnectionError:
        raise
    except Exception as e:
        # Log unexpected errors but don't mask their type
        logger.error(f"Unexpected error in get_latest_forecast: {str(e)}", exc_info=True)
        raise


@router.get(
    "/{city}/history",
    response_model=HistoryResponse,
    responses={
        200: {"description": "Successful response with forecast history"},
        503: {"model": ErrorResponse, "description": "Database connection error"}
    },
    summary="Get forecast history for a city",
    description="Retrieves historical forecasts for a city with optional filtering"
)
async def get_forecast_history(
    city: str = Path(..., description="City name"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    include_expired: bool = Query(False, description="Include expired forecasts")
):
    """Get forecast history for a city"""
    try:
        result = list_forecasts(city=city, limit=limit)

        if result.get("status") == "error":
            raise DatabaseConnectionError(result.get("message", "Database error"))

        forecasts = result.get("forecasts", [])

        # Filter expired if requested
        if not include_expired:
            forecasts = [f for f in forecasts if not f.get("expired", False)]

        return {
            "status": "success",
            "city": city.lower(),
            "count": len(forecasts),
            "forecasts": forecasts
        }
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise DatabaseConnectionError(f"Unexpected error: {str(e)}")
