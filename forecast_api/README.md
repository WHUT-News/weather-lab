# Weather Forecast API

A standalone FastAPI REST API server for retrieving weather forecasts from Cloud SQL PostgreSQL database.

## Features

- **FastAPI Framework**: Modern, fast, with automatic OpenAPI/Swagger documentation
- **Direct Cloud SQL Access**: Direct PostgreSQL connection for optimal performance
- **4 REST Endpoints**: Latest forecast, history, statistics, and health check
- **Base64 Audio**: Audio data included in JSON responses
- **Auto-Generated Docs**: Interactive API documentation at `/docs`
- **CORS Enabled**: Configured for cross-origin requests
- **Docker Ready**: Containerized for easy deployment

## API Endpoints

### 1. GET /weather/{city}
Get the latest valid forecast for a city.

**Parameters:**
- `city` (path): City name (case-insensitive)
- `language` (query, optional): ISO 639-1 language code (e.g., 'en', 'es', 'ja')

**Example:**
```bash
curl http://localhost:8000/weather/chicago
curl http://localhost:8000/weather/tokyo?language=ja
```

### 2. GET /weather/{city}/history
Get historical forecasts for a city.

**Parameters:**
- `city` (path): City name
- `limit` (query, optional): Max results (1-100, default 10)
- `include_expired` (query, optional): Include expired forecasts (default false)

**Example:**
```bash
curl http://localhost:8000/weather/chicago/history?limit=5
curl http://localhost:8000/weather/chicago/history?include_expired=true
```

### 3. GET /stats
Get database storage statistics.

**Example:**
```bash
curl http://localhost:8000/stats
```

### 4. GET /health
Health check endpoint for monitoring.

**Example:**
```bash
curl http://localhost:8000/health
```

## Installation

### Prerequisites
- Python 3.11+
- Google Cloud SQL PostgreSQL database
- GCP credentials with Cloud SQL access

### Local Development

1. **Install dependencies:**
```bash
cd forecast_api
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your Cloud SQL credentials
```

3. **Run the server:**
```bash
uvicorn main:app --reload --port 8000
```

4. **Access the API:**
- API Root: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## Testing

The API includes comprehensive test coverage. See [TESTING.md](TESTING.md) for detailed testing guide.

### Quick Test Commands

**Run unit tests:**
```bash
pytest
# or
./run_tests.sh
# or (Windows)
run_tests.bat
```

**Run manual integration tests:**
```bash
# Start the server first
uvicorn main:app --reload --port 8000

# In another terminal
python tests/manual_test.py
# or
./run_tests.sh manual
```

**Run specific test suites:**
```bash
pytest tests/test_weather.py  # Weather endpoints
pytest tests/test_stats.py    # Statistics endpoint
pytest tests/test_health.py   # Health endpoint
```

**Generate coverage report:**
```bash
pytest --cov=. --cov-report=html
# or
./run_tests.sh coverage
```

### Test Structure

- `tests/test_weather.py` - Unit tests for weather endpoints (mocked)
- `tests/test_stats.py` - Unit tests for statistics endpoint (mocked)
- `tests/test_health.py` - Unit tests for health endpoint (mocked)
- `tests/manual_test.py` - Integration tests against running server
- `tests/conftest.py` - Pytest fixtures and configuration

## Deployment

### Docker Deployment

1. **Build the image:**
```bash
docker build -t weather-forecast-api .
```

2. **Run the container:**
```bash
docker run -p 8000:8000 --env-file .env weather-forecast-api
```

### Google Cloud Run Deployment

```bash
gcloud run deploy weather-forecast-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=your-project-id \
  --set-env-vars CLOUD_SQL_PASSWORD=your-password \
  --allow-unauthenticated
```

## Configuration

All configuration is managed via environment variables. See [.env.example](.env.example) for available options.

**Required Variables:**
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID
- `CLOUD_SQL_PASSWORD`: Database password

**Optional Variables:**
- `API_TITLE`: API title (default: "Weather Forecast API")
- `HOST`: Server host (default: "0.0.0.0")
- `PORT`: Server port (default: 8000)
- `GOOGLE_CLOUD_LOCATION`: GCP region (default: "us-central1")
- `CLOUD_SQL_INSTANCE`: Instance name (default: "weather-forecasts")
- `CLOUD_SQL_DB`: Database name (default: "weather")
- `CLOUD_SQL_USER`: Database user (default: "postgres")
- `LOG_LEVEL`: Logging level (default: "INFO")

## Project Structure

```
forecast_api/
├── main.py                      # FastAPI app entry point
├── config.py                    # Settings management
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── Dockerfile                   # Container configuration
├── api/
│   ├── routes/
│   │   ├── weather.py          # Weather endpoints
│   │   ├── stats.py            # Statistics endpoint
│   │   └── health.py           # Health check endpoint
│   └── models/
│       └── responses.py        # Pydantic response schemas
└── core/
    ├── database.py             # Database wrapper
    └── exceptions.py           # Custom exceptions
```

## Response Examples

### Latest Forecast Response
```json
{
  "status": "success",
  "city": "chicago",
  "forecast": {
    "text": "Weather forecast text content...",
    "audio_base64": "UklGRiQAAABXQVZF...",
    "forecast_at": "2025-12-27T15:00:00+00:00",
    "expires_at": "2025-12-27T15:30:00+00:00",
    "age_seconds": 120,
    "metadata": {
      "encoding": "utf-8",
      "language": "en",
      "locale": "en-US",
      "sizes": {
        "text_bytes": 1024,
        "audio_bytes": 51200
      }
    }
  }
}
```

### Error Response
```json
{
  "status": "error",
  "message": "No valid forecast found for city: chicago"
}
```

## Dependencies

The API includes standalone database modules in the `core` package:

- `core/connection.py` - Cloud SQL connector
- `core/forecast_operations.py` - Database operations
- `core/encoding.py` - Text encoding utilities

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
The project follows standard Python conventions and uses type hints throughout.

## License

Part of the weather-lab project.
