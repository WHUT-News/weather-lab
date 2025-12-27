"""
Cloud SQL connection management.

Provides secure connections to Google Cloud SQL PostgreSQL using
the Cloud SQL Python Connector with IAM authentication support.
"""

from typing import Optional
from google.cloud.sql.connector import Connector

from config import settings

# Build instance connection name
if settings.GOOGLE_CLOUD_PROJECT and settings.GOOGLE_CLOUD_LOCATION and settings.CLOUD_SQL_INSTANCE:
    INSTANCE_CONNECTION_NAME = f"{settings.GOOGLE_CLOUD_PROJECT}:{settings.GOOGLE_CLOUD_LOCATION}:{settings.CLOUD_SQL_INSTANCE}"
else:
    INSTANCE_CONNECTION_NAME = None

# Global connector instance (initialized on first use)
_connector: Optional[Connector] = None


def get_connector() -> Connector:
    """
    Get or create the global Cloud SQL connector instance.

    Returns:
        Connector instance
    """
    global _connector
    if _connector is None:
        _connector = Connector()
    return _connector


def get_connection():
    """
    Get a connection to Cloud SQL PostgreSQL using pg8000.

    Returns a raw pg8000 DB-API connection suitable for reading/writing binary data (BYTEA columns).

    Returns:
        pg8000 connection object

    Raises:
        ValueError: If required environment variables are not set
        Exception: If connection fails

    Example:
        >>> conn = get_connection()
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT * FROM forecasts")
        >>> results = cursor.fetchall()
        >>> conn.close()
    """
    if not INSTANCE_CONNECTION_NAME:
        raise ValueError(
            "Missing required Cloud SQL configuration. "
            "Please set GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, and CLOUD_SQL_INSTANCE "
            "environment variables."
        )

    if not settings.CLOUD_SQL_PASSWORD:
        raise ValueError(
            "Missing CLOUD_SQL_PASSWORD environment variable. "
            "Please set the database password."
        )

    connector = get_connector()

    try:
        conn = connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pg8000",
            user=settings.CLOUD_SQL_USER,
            password=settings.CLOUD_SQL_PASSWORD,
            db=settings.CLOUD_SQL_DB
        )
        return conn
    except Exception as e:
        raise Exception(
            f"Failed to connect to Cloud SQL instance {INSTANCE_CONNECTION_NAME}: {e}"
        )


def close_connector():
    """
    Close the global connector and cleanup resources.

    Should be called when shutting down the application.
    """
    global _connector
    if _connector:
        _connector.close()
        _connector = None


def test_connection() -> dict:
    """
    Test the database connection and return status.

    Returns:
        Dictionary with connection status and details
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Test query
        cursor.execute("SELECT version()")
        result = cursor.fetchone()
        version = result[0] if result else "Unknown"

        # Check if forecasts table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'forecasts'
            )
        """)
        table_exists = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "connected": True,
            "instance": INSTANCE_CONNECTION_NAME,
            "database": settings.CLOUD_SQL_DB,
            "version": version,
            "forecasts_table_exists": table_exists
        }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e),
            "instance": INSTANCE_CONNECTION_NAME or "Not configured"
        }
