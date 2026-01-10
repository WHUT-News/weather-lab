# GCS Picture Upload Implementation Summary

## Completed - Weather Agent Changes

### 1. Dependencies (✅ Complete)
- Added `google-cloud-storage>=2.10.0` to [requirements.txt](requirements.txt:8)

### 2. Upload Picture Support (✅ Complete)
**File**: [weather_agent/forecast_storage_client.py](weather_agent/forecast_storage_client.py:126-154)

Modified `upload_forecast_to_storage()` to:
- Read picture file from `FORECAST_PICTURE` session state
- Base64 encode picture bytes
- Extract file format from extension
- Send `picture_data` and `picture_format` to MCP server
- Gracefully handle missing pictures (optional feature)

### 3. Download Picture Support (✅ Complete)
**File**: [weather_agent/forecast_storage_client.py](weather_agent/forecast_storage_client.py:179-223)

Added `download_and_write_picture()` helper function to:
- Parse GCS URLs (`gs://bucket/path/file.png`)
- Download picture bytes from GCS using Google Cloud Storage client
- Write locally using existing `write_picture_file()` function
- Return local file path or None on failure

### 4. Cache Retrieval with Pictures (✅ Complete)
**File**: [weather_agent/forecast_storage_client.py](weather_agent/forecast_storage_client.py:251-278)

Modified `get_cached_forecast_from_storage()` to:
- Retrieve `picture_url` from MCP response
- Download picture from GCS if URL exists
- Store local file path in `picture_filepath` return value
- Gracefully handle missing or failed downloads

### 5. Root Agent Instructions (✅ Already Complete)
**File**: [weather_agent/agent.py](weather_agent/agent.py:73)

Agent instructions already mention storing `picture_filepath` in session state.

## Installation

Install the new dependency:
```bash
pip install -r requirements.txt
```

Or specifically:
```bash
pip install google-cloud-storage>=2.10.0
```

## Pending - MCP Server Changes (forecast-storage-mcp repository)

The MCP server needs the following changes to support picture uploads to GCS:

### 1. Add GCS Operations Module
**File**: `forecast_storage_mcp/tools/gcs_operations.py` (NEW)

Functions needed:
- `upload_picture_to_gcs(city, picture_data_base64, forecast_at, file_extension)` → returns GCS URL
- `download_picture_from_gcs(gcs_url)` → returns base64 encoded bytes (optional)
- `delete_picture_from_gcs(gcs_url)` → deletes picture (for cleanup)

### 2. Database Schema Changes
**File**: `forecast_storage_mcp/schema.sql` (MODIFY)

Add column:
```sql
ALTER TABLE forecasts
ADD COLUMN picture_url TEXT DEFAULT NULL;

CREATE INDEX idx_picture_url ON forecasts(picture_url)
WHERE picture_url IS NOT NULL;
```

### 3. Modify upload_forecast Tool
**File**: `forecast_storage_mcp/tools/forecast_operations.py` (MODIFY)

- Add `picture_data` and `picture_format` parameters
- Call `upload_picture_to_gcs()` if picture_data provided
- Store returned GCS URL in `picture_url` column
- Handle upload failures gracefully

### 4. Modify get_cached_forecast Tool
**File**: `forecast_storage_mcp/tools/forecast_operations.py` (MODIFY)

- Add `picture_url` to SELECT query
- Include `picture_url` in response JSON

### 5. Add Dependencies
**File**: `forecast_storage_mcp/requirements.txt` (MODIFY)

```
google-cloud-storage>=2.10.0
```

### 6. Infrastructure Setup

**Create GCS Bucket**:
```bash
gsutil mb -p $GOOGLE_CLOUD_PROJECT \
  -c STANDARD \
  -l us-central1 \
  gs://${GOOGLE_CLOUD_PROJECT}-weather-forecast-pictures
```

**Set Lifecycle Policy** (7-day retention):
```json
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"age": 7}
    }]
  }
}
```

**Set IAM Permissions**:
- MCP server: `roles/storage.objectAdmin`
- Weather agent: `roles/storage.objectViewer`

### 7. Database Cleanup Job (Optional but Recommended)

Add scheduled cleanup to delete forecast records older than 7 days.

See [implementation plan](C:\Users\liang\.claude\plans\cached-stargazing-ocean.md) Phase 3, Section 3.4 for details.

## Testing

Once MCP server changes are complete:

1. **New Forecast with Picture**:
   - Generate forecast for a city
   - Verify picture uploaded to GCS
   - Verify `picture_url` stored in Cloud SQL

2. **Cached Forecast with Picture**:
   - Request same city within 30 minutes
   - Verify picture downloaded from GCS
   - Verify local file created in `output/{city}/`

3. **Picture Generation Failure**:
   - Trigger Imagen quota error
   - Verify forecast succeeds without picture
   - Verify `picture_url = NULL` in database

4. **GCS Upload/Download Failure**:
   - Temporarily break GCS permissions
   - Verify forecast succeeds
   - Verify errors logged but not thrown

## Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│ Picture Upload Flow                                     │
├─────────────────────────────────────────────────────────┤
│ 1. Photographer generates picture → Local file          │
│ 2. Upload: Read file → Base64 encode → Send via MCP    │
│ 3. MCP Server: Decode → Upload to GCS → Get URL        │
│ 4. MCP Server: Store URL in Cloud SQL                   │
│ 5. Cleanup: Local file deleted after 7 days             │
│ 6. Cleanup: GCS picture deleted after 7 days            │
│ 7. Cleanup: Database record deleted after 7 days        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Picture Cache Retrieval Flow                            │
├─────────────────────────────────────────────────────────┤
│ 1. Agent requests cached forecast                       │
│ 2. MCP returns forecast_text, audio_data, picture_url   │
│ 3. Agent downloads picture from GCS URL                 │
│ 4. Agent writes picture to local output/ directory      │
│ 5. Agent stores path in FORECAST_PICTURE state          │
└─────────────────────────────────────────────────────────┘
```

## Error Handling

All picture operations are **non-fatal**:
- If picture generation fails → Forecast succeeds with text + audio only
- If GCS upload fails → Forecast succeeds, `picture_url = NULL`
- If GCS download fails → Cached forecast returns text + audio only
- Errors are logged for investigation but don't block forecast delivery

## Configuration

**Weather Agent** (no new env vars needed):
- Uses existing `GOOGLE_CLOUD_PROJECT` for GCS authentication
- GCS client auto-detects credentials

**MCP Server** (add to `.env`):
```bash
GCS_BUCKET_NAME=your-project-weather-forecast-pictures
```

## File References

### Modified Files
- [requirements.txt](requirements.txt) - Added google-cloud-storage dependency
- [weather_agent/forecast_storage_client.py](weather_agent/forecast_storage_client.py) - Upload/download picture support

### Unchanged Files (Already Compatible)
- [weather_agent/agent.py](weather_agent/agent.py) - Instructions already mention picture_filepath
- [weather_agent/write_file.py](weather_agent/write_file.py) - write_picture_file() already handles bytes
- [weather_agent/sub_agents/forecast_photographer/agent.py](weather_agent/sub_agents/forecast_photographer/agent.py) - Already sets FORECAST_PICTURE state

## Next Steps

1. **Install dependencies**: Run `pip install -r requirements.txt`
2. **Implement MCP server changes** (in forecast-storage-mcp repository)
3. **Create GCS bucket and set lifecycle policy**
4. **Apply database migration** (ADD COLUMN picture_url)
5. **Deploy MCP server** with GCS support
6. **Test end-to-end** with new forecast and cache retrieval

## Detailed Implementation Plan

Full implementation plan with step-by-step instructions: [cached-stargazing-ocean.md](C:\Users\liang\.claude\plans\cached-stargazing-ocean.md)
