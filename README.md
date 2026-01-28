# Weather Lab

A multi-agent weather forecasting system built with [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit). It retrieves real-time weather data, generates conversational forecasts using an LLM, converts them to speech, produces weather-themed images, and caches results in Supabase.

## Architecture

```
                         +-----------------+
                         |   Root Agent    |
                         | (Orchestrator)  |
                         +--------+--------+
                                  |
                    +-------------+-------------+
                    |                           |
           +-------v-------+         +---------v---------+
           | Forecast Writer|         |  Supabase Cache   |
           | (Text via LLM) |         | (DB + Storage)    |
           +-------+-------+         +-------------------+
                   |
        +----------+----------+
        |                     |
+-------v-------+    +-------v--------+
|Forecast Speaker|    |Forecast Photog |
| (Google TTS)   |    | (Google Imagen)|
+----------------+    +----------------+
```

**Root Agent** orchestrates the workflow: checks the Supabase cache for a recent forecast, and if none exists, delegates to the **Forecast Writer** (fetches weather data from OpenWeather API and generates text via Gemini), then in parallel to the **Forecast Speaker** (text-to-speech) and **Forecast Photographer** (image generation via Imagen). Results are uploaded to Supabase for future cache hits.

## Tech Stack

- **Python 3.11+** with Google ADK for agent orchestration
- **Google Gemini** for LLM text generation and TTS
- **Google Imagen** for weather-themed image generation
- **OpenWeather API** for real-time weather data
- **Supabase** (PostgreSQL + Storage) for caching forecasts, audio, and images
- **Google Cloud Run** for serverless deployment

## Project Structure

```
weather-lab/
├── weather_agent/
│   ├── agent.py                    # Root agent orchestration
│   ├── tools.py                    # Session management tools
│   ├── forecast_storage_client.py  # Supabase storage client
│   ├── write_file.py               # File I/O utilities
│   ├── caching/
│   │   ├── api_call_cache.py       # TTL-based API caching decorator
│   │   ├── forecast_cache.py       # Filesystem-based forecast cache
│   │   └── forecast_file_cleanup.py
│   ├── sub_agents/
│   │   ├── forecast_writer/        # Text generation agent
│   │   ├── forecast_speaker/       # Audio generation agent
│   │   └── forecast_photographer/  # Image generation agent
│   └── tests/
├── schema.sql                      # Supabase PostgreSQL schema
├── Dockerfile
├── deploy-cloudrun.sh
└── requirements.txt
```

## Setup

### Prerequisites

- Python 3.11+
- A Google Cloud project with Vertex AI enabled
- An [OpenWeather API key](https://openweathermap.org/api)
- A [Supabase](https://supabase.com/) project

### Installation

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy the example env file and fill in your credentials:

```bash
cp weather_agent/.env.example weather_agent/.env
```

Key variables:

| Variable | Description |
|---|---|
| `OPENWEATHER_API_KEY` | OpenWeather API key |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID |
| `GOOGLE_CLOUD_LOCATION` | GCP region (default: `us-central1`) |
| `MODEL` | Gemini model for text (default: `gemini-2.5-flash`) |
| `TTS_MODEL` | Gemini model for TTS (default: `gemini-2.5-flash-tts`) |
| `IMG_MODEL` | Imagen model (default: `imagen-4.0-generate`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_SECRET_KEY` | Supabase service role key |
| `CACHE_TTL` | Forecast cache TTL in hours (default: `1`) |
| `OUTPUT_DIR` | Local output directory (default: `output`) |

### Database Setup

Run [schema.sql](schema.sql) against your Supabase PostgreSQL database to create the `weather_forecasts` table, indexes, and helper functions. Also create two public Storage buckets in the Supabase dashboard:

- `weather-audio` (MIME types: `audio/wav`, `audio/mpeg`, `audio/ogg`)
- `weather-images` (MIME types: `image/png`, `image/jpeg`, `image/webp`)

## Usage

### Run Locally

```bash
adk web --host 0.0.0.0 --port 8000
```

This starts the ADK web interface. Enter a city name when prompted to get a weather forecast with text, audio, and an image.

### Run with Docker

```bash
docker build -t weather-agent:latest .
docker run -p 8000:8000 --env-file weather_agent/.env weather-agent:latest
```

### Deploy to Cloud Run

```bash
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_SECRET_KEY=your-key
./deploy-cloudrun.sh
```

The script builds the Docker image, pushes to GCR, and deploys to Cloud Run with auto-scaling (0-10 instances). The Supabase service key is loaded from Google Secret Manager.

## Testing

```bash
pytest weather_agent/tests/
```
