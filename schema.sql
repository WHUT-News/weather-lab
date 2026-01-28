-- Weather Forecast Storage - Supabase PostgreSQL Schema
-- This schema stores weather forecasts with text in the database
-- and audio/images in Supabase Storage

-- Enable UUID extension (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Main weather reports table
CREATE TABLE IF NOT EXISTS weather_forecasts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Forecast identification
    city VARCHAR(100) NOT NULL,

    -- Timestamps
    forecast_at TIMESTAMPTZ NOT NULL,       -- When forecast was generated
    expires_at TIMESTAMPTZ NOT NULL,        -- TTL expiration time
    created_at TIMESTAMPTZ DEFAULT NOW(),   -- When record was created

    -- Text content (stored as binary for encoding support)
    forecast_text BYTEA NOT NULL,           -- Encoded forecast content

    -- File metadata (sizes in bytes)
    text_size_bytes INTEGER NOT NULL,

    -- Storage URLs (files stored in Supabase Storage)
    audio_url TEXT,                         -- URL to audio file in Supabase Storage
    image_url TEXT,                         -- URL to image file in Supabase Storage

    -- Audio metadata
    audio_size_bytes INTEGER,
    audio_format VARCHAR(10) DEFAULT 'wav', -- 'wav', 'mp3', 'ogg'
    audio_language VARCHAR(10),             -- Language of spoken audio

    -- Image metadata
    image_size_bytes INTEGER,
    image_format VARCHAR(10),               -- 'png', 'jpg', 'webp'

    -- Internationalization support
    text_encoding VARCHAR(20) DEFAULT 'utf-8',  -- 'utf-8', 'utf-16', 'utf-32'
    text_language VARCHAR(10),              -- ISO 639-1: 'en', 'es', 'ja', 'zh'
    text_locale VARCHAR(20),               -- Full locale: 'en-US', 'es-MX'

    -- Flexible metadata
    metadata JSONB DEFAULT '{}'::jsonb      -- Additional flexible data
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_weather_forecasts_city_expires ON weather_forecasts(city, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_forecasts_expires_at ON weather_forecasts(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_weather_forecasts_forecast_at ON weather_forecasts(forecast_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_forecasts_language ON weather_forecasts(text_language) WHERE text_language IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_weather_forecasts_locale ON weather_forecasts(text_locale) WHERE text_locale IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_weather_forecasts_created_at ON weather_forecasts(created_at DESC);

-- Function to get storage statistics
CREATE OR REPLACE FUNCTION get_forecast_storage_stats()
RETURNS TABLE (
    total_forecasts BIGINT,
    total_text_bytes BIGINT,
    total_audio_bytes BIGINT,
    total_image_bytes BIGINT,
    forecasts_with_audio BIGINT,
    forecasts_with_images BIGINT,
    expired_forecasts BIGINT,
    cities_used JSONB,
    languages_used JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_forecasts,
        COALESCE(SUM(text_size_bytes), 0)::BIGINT as total_text_bytes,
        COALESCE(SUM(audio_size_bytes), 0)::BIGINT as total_audio_bytes,
        COALESCE(SUM(image_size_bytes), 0)::BIGINT as total_image_bytes,
        COUNT(audio_url)::BIGINT as forecasts_with_audio,
        COUNT(image_url)::BIGINT as forecasts_with_images,
        COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at < NOW())::BIGINT as expired_forecasts,
        COALESCE(
            jsonb_object_agg(DISTINCT city, 1) FILTER (WHERE city IS NOT NULL),
            '{}'::jsonb
        ) as cities_used,
        COALESCE(
            jsonb_object_agg(DISTINCT text_language, 1) FILTER (WHERE text_language IS NOT NULL),
            '{}'::jsonb
        ) as languages_used
    FROM weather_forecasts;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired forecasts
CREATE OR REPLACE FUNCTION cleanup_expired_forecasts()
RETURNS TABLE (
    deleted_count BIGINT,
    remaining_count BIGINT,
    deleted_audio_urls TEXT[],
    deleted_image_urls TEXT[]
) AS $$
DECLARE
    v_deleted_count BIGINT;
    v_remaining_count BIGINT;
    v_deleted_audio_urls TEXT[];
    v_deleted_image_urls TEXT[];
BEGIN
    -- Collect URLs of files to delete from storage
    SELECT
        array_agg(audio_url) FILTER (WHERE audio_url IS NOT NULL),
        array_agg(image_url) FILTER (WHERE image_url IS NOT NULL)
    INTO v_deleted_audio_urls, v_deleted_image_urls
    FROM weather_forecasts
    WHERE expires_at IS NOT NULL AND expires_at < NOW();

    -- Delete expired records
    DELETE FROM weather_forecasts
    WHERE expires_at IS NOT NULL AND expires_at < NOW();

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    -- Count remaining records
    SELECT COUNT(*) INTO v_remaining_count FROM weather_forecasts;

    RETURN QUERY SELECT
        v_deleted_count,
        v_remaining_count,
        COALESCE(v_deleted_audio_urls, ARRAY[]::TEXT[]),
        COALESCE(v_deleted_image_urls, ARRAY[]::TEXT[]);
END;
$$ LANGUAGE plpgsql;

-- Function to get forecasts by language
CREATE OR REPLACE FUNCTION get_forecasts_by_language(
    p_language VARCHAR(10),
    p_city VARCHAR(100) DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS SETOF weather_forecasts AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM weather_forecasts
    WHERE text_language = p_language
      AND (p_city IS NULL OR city = p_city)
      AND (expires_at IS NULL OR expires_at > NOW())
    ORDER BY forecast_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Supabase Storage buckets (create via Supabase dashboard or client library)
--
-- Bucket: weather-audio
--   - Public: true (direct URL access)
--   - Allowed MIME types: audio/wav, audio/mpeg, audio/ogg
--   - Max file size: 50MB
--
-- Bucket: weather-images
--   - Public: true (direct URL access)
--   - Allowed MIME types: image/png, image/jpeg, image/webp
--   - Max file size: 10MB

-- Row Level Security (RLS) policies for Supabase
-- Enable RLS on the table
ALTER TABLE weather_forecasts ENABLE ROW LEVEL SECURITY;

-- Policy for authenticated service role (full access)
CREATE POLICY "Service role has full access" ON weather_forecasts
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Policy for anonymous read access (optional, adjust as needed)
CREATE POLICY "Anonymous can read non-expired forecasts" ON weather_forecasts
    FOR SELECT
    USING (expires_at IS NULL OR expires_at > NOW());

-- Comments for documentation
COMMENT ON TABLE weather_forecasts IS 'Stores weather forecasts with text content, metadata, and references to audio/image files in Supabase Storage';
COMMENT ON COLUMN weather_forecasts.forecast_text IS 'Forecast content stored as encoded binary (BYTEA) to support all Unicode characters';
COMMENT ON COLUMN weather_forecasts.audio_url IS 'URL to audio file stored in Supabase Storage bucket "weather-audio"';
COMMENT ON COLUMN weather_forecasts.image_url IS 'URL to image file stored in Supabase Storage bucket "weather-images"';
COMMENT ON COLUMN weather_forecasts.text_encoding IS 'Character encoding used for forecast_text (utf-8, utf-16, utf-32)';
