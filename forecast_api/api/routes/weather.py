"""
Weather forecast endpoints.
"""
from fastapi import APIRouter, Query, Path
from typing import Optional

from api.models.responses import (
    WeatherResponse,
    WeatherNotFoundResponse,
    HistoryResponse,
    ErrorResponse
)
from core.database import get_cached_forecast, list_forecasts
from core.exceptions import ForecastNotFoundError, DatabaseConnectionError
from datetime import datetime

router = APIRouter()


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
    except (ForecastNotFoundError, DatabaseConnectionError):
        raise
    except Exception as e:
        # Log unexpected errors but don't mask their type
        import logging
        logging.error(f"Unexpected error in get_latest_forecast: {str(e)}", exc_info=True)
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
