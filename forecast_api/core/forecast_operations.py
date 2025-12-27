"""
Forecast storage operations for Cloud SQL.

Provides CRUD operations for weather forecasts with binary storage.
"""

import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from .connection import get_connection
from .encoding import encode_text, decode_text, detect_optimal_encoding


def upload_forecast(
    city: str,
    forecast_text: str,
    audio_data: str,
    forecast_at: str,
    ttl_minutes: int = 30,
    encoding: Optional[str] = None,
    language: Optional[str] = None,
    locale: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a complete forecast (text + audio) to Cloud SQL.

    Args:
        city: City name (e.g., 'chicago')
        forecast_text: Generated forecast text content
        audio_data: Base64-encoded audio WAV data
        forecast_at: when was the forecast made. ISO 8601 timestamp (e.g., '2025-12-26T15:00:00Z')
        ttl_minutes: Time-to-live in minutes (default: 30)
        encoding: Text encoding (auto-detect if None)
        language: ISO 639-1 language code (e.g., 'en', 'es', 'ja')
        locale: Full locale (e.g., 'en-US', 'es-MX', 'ja-JP')

    Returns:
        Dictionary with upload status and metadata
    """
    # Auto-detect optimal encoding if not specified
    if encoding is None:
        encoding = detect_optimal_encoding(forecast_text)

    # Encode forecast text
    try:
        text_bytes, text_size, encoding_used = encode_text(forecast_text, encoding)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to encode text: {e}"
        }

    # Decode base64 audio data
    try:
        audio_bytes = base64.b64decode(audio_data)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to decode audio data: {e}"
        }

    # Parse forecast_at timestamp
    try:
        forecast_time = datetime.fromisoformat(forecast_at.replace('Z', '+00:00'))
    except Exception as e:
        return {
            "status": "error",
            "message": f"Invalid forecast_at timestamp format: {e}"
        }

    expires_at = forecast_time + timedelta(minutes=ttl_minutes)

    # Prepare metadata
    metadata = {
        'ttl_minutes': ttl_minutes,
        'character_count': len(forecast_text),
        'encoding_used': encoding_used
    }

    # Insert into database
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO forecasts (
                city, forecast_at, expires_at,
                forecast_text, audio_file,
                text_size_bytes, audio_size_bytes,
                text_encoding, text_language, text_locale,
                audio_format, audio_language,
                metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            city.lower(),
            forecast_time,
            expires_at,
            text_bytes,
            audio_bytes,
            text_size,
            len(audio_bytes),
            encoding_used,
            language,
            locale,
            'wav',
            language,
            metadata
        ))

        result = cursor.fetchone()
        conn.commit()

        # RETURNING id, created_at -> result[0]=id, result[1]=created_at
        return {
            "status": "success",
            "forecast_id": str(result[0]),
            "created_at": result[1].isoformat(),
            "encoding": encoding_used,
            "language": language,
            "locale": locale,
            "sizes": {
                "text": text_size,
                "audio": len(audio_bytes),
                "total": text_size + len(audio_bytes)
            }
        }

    except Exception as e:
        conn.rollback()
        return {
            "status": "error",
            "message": f"Database error: {e}"
        }
    finally:
        cursor.close()
        conn.close()


def get_cached_forecast(
    city: str,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve cached forecast from Cloud SQL if available.

    Args:
        city: City name to query
        language: Optional language filter (e.g., 'en', 'es', 'ja')

    Returns:
        Dictionary with cached forecast or cached=False if not found
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Build query with optional language filter
        query = """
            SELECT
                id, forecast_text, audio_file, forecast_at,
                expires_at, text_size_bytes, audio_size_bytes,
                text_encoding, text_language, text_locale,
                created_at, metadata
            FROM forecasts
            WHERE city = %s
              AND expires_at > NOW()
        """
        params = [city.lower()]

        if language:
            query += " AND text_language = %s"
            params.append(language)

        query += " ORDER BY forecast_at DESC LIMIT 1"

        cursor.execute(query, params)
        result = cursor.fetchone()

        if result:
            # Query columns: id, forecast_text, audio_file, forecast_at, expires_at,
            #               text_size_bytes, audio_size_bytes, text_encoding, text_language,
            #               text_locale, created_at, metadata
            # Indices:      0,  1,             2,          3,           4,
            #               5,               6,                7,             8,
            #               9,          10,         11

            # Decode text
            try:
                forecast_text = decode_text(
                    bytes(result[1]),  # forecast_text
                    encoding=result[7]  # text_encoding
                )
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to decode text: {e}"
                }

            # Calculate age
            age_seconds = (datetime.now(result[3].tzinfo) - result[3]).total_seconds()  # forecast_at

            return {
                "cached": True,
                "forecast_text": forecast_text,
                "audio_data": base64.b64encode(bytes(result[2])).decode('utf-8'),  # audio_file
                "forecast_at": result[3].isoformat(),  # forecast_at
                "expires_at": result[4].isoformat(),  # expires_at
                "age_seconds": int(age_seconds),
                "encoding": result[7],  # text_encoding
                "language": result[8],  # text_language
                "locale": result[9],  # text_locale
                "sizes": {
                    "text": result[5],  # text_size_bytes
                    "audio": result[6]  # audio_size_bytes
                },
                "metadata": result[11]  # metadata
            }

        return {"cached": False}

    except Exception as e:
        return {
            "status": "error",
            "cached": False,
            "message": f"Database error: {e}"
        }
    finally:
        cursor.close()
        conn.close()


def cleanup_expired_forecasts() -> Dict[str, Any]:
    """
    Remove expired forecasts from database.

    Returns:
        Dictionary with cleanup statistics
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Call the cleanup function
        cursor.execute("SELECT cleanup_expired_forecasts()")
        deleted_count = cursor.fetchone()[0]  # Returns single column

        # Get remaining count
        cursor.execute("SELECT COUNT(*) FROM forecasts")
        remaining_count = cursor.fetchone()[0]  # Returns single column

        conn.commit()

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "remaining_count": remaining_count
        }

    except Exception as e:
        conn.rollback()
        return {
            "status": "error",
            "message": f"Cleanup failed: {e}"
        }
    finally:
        cursor.close()
        conn.close()


def get_storage_stats() -> Dict[str, Any]:
    """
    Get database storage statistics.

    Returns:
        Dictionary with storage statistics
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get aggregate statistics
        cursor.execute("SELECT * FROM get_storage_stats()")
        stats = cursor.fetchone()

        # Function returns: total_forecasts, total_text_bytes, total_audio_bytes,
        #                  encodings_used, languages_used
        # Indices:         0,              1,                2,
        #                  3,              4

        # Get per-city breakdown
        cursor.execute("""
            SELECT
                city,
                COUNT(*) as forecast_count,
                SUM(text_size_bytes) as total_text_bytes,
                SUM(audio_size_bytes) as total_audio_bytes,
                MAX(forecast_at) as latest_forecast
            FROM forecasts
            WHERE expires_at > NOW()
            GROUP BY city
            ORDER BY forecast_count DESC
        """)

        # Query columns: city, forecast_count, total_text_bytes, total_audio_bytes, latest_forecast
        # Indices:       0,    1,              2,                3,                 4
        city_stats = [
            {
                "city": row[0],
                "forecast_count": row[1],
                "total_text_bytes": row[2] or 0,
                "total_audio_bytes": row[3] or 0,
                "latest_forecast": row[4].isoformat() if row[4] else None
            }
            for row in cursor.fetchall()
        ]

        return {
            "status": "success",
            "total_forecasts": int(stats[0]) if stats[0] else 0,
            "total_text_bytes": int(stats[1]) if stats[1] else 0,
            "total_audio_bytes": int(stats[2]) if stats[2] else 0,
            "encodings_used": stats[3] or {},
            "languages_used": stats[4] or {},
            "city_breakdown": city_stats
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get stats: {e}"
        }
    finally:
        cursor.close()
        conn.close()


def list_forecasts(
    city: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    List forecast history for a city.

    Args:
        city: City name (optional, lists all if omitted)
        limit: Maximum number of results (default: 10)

    Returns:
        Dictionary with list of forecasts
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT
                id, city, forecast_at, expires_at,
                text_size_bytes, audio_size_bytes,
                text_encoding, text_language, text_locale,
                created_at
            FROM forecasts
        """
        params = []

        if city:
            query += " WHERE city = %s"
            params.append(city.lower())

        query += " ORDER BY forecast_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)

        # Query columns: id, city, forecast_at, expires_at, text_size_bytes, audio_size_bytes,
        #               text_encoding, text_language, text_locale, created_at
        # Indices:      0,  1,    2,           3,          4,               5,
        #               6,            7,             8,           9
        forecasts = [
            {
                "forecast_id": str(row[0]),  # id
                "city": row[1],  # city
                "forecast_at": row[2].isoformat(),  # forecast_at
                "expires_at": row[3].isoformat(),  # expires_at
                "expired": row[3] < datetime.now(row[3].tzinfo),  # expires_at
                "sizes": {
                    "text": row[4],  # text_size_bytes
                    "audio": row[5]  # audio_size_bytes
                },
                "encoding": row[6],  # text_encoding
                "language": row[7],  # text_language
                "locale": row[8],  # text_locale
                "created_at": row[9].isoformat()  # created_at
            }
            for row in cursor.fetchall()
        ]

        return {
            "status": "success",
            "count": len(forecasts),
            "forecasts": forecasts
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list forecasts: {e}"
        }
    finally:
        cursor.close()
        conn.close()
