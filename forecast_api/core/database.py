"""
Database connection wrapper for FastAPI.
Provides database operations using standalone modules.
"""
from .connection import (
    get_connection,
    close_connector,
    test_connection
)
from .encoding import decode_text
from .forecast_operations import (
    get_cached_forecast,
    list_forecasts,
    get_storage_stats
)


def test_db_connection() -> dict:
    """Test database connection on startup"""
    return test_connection()


def cleanup_db_connection():
    """Close database connector on shutdown"""
    close_connector()


# Export functions for use in routes
__all__ = [
    'get_connection',
    'test_db_connection',
    'cleanup_db_connection',
    'get_cached_forecast',
    'list_forecasts',
    'get_storage_stats',
    'decode_text'
]
