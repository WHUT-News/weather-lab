# Weather Agent Optimization Plan

## Overview
Comprehensive optimization strategy to reduce costs by 80-95%, improve response speed by 60-90%, and achieve near 100% reliability for the weather agent system.

**User Goals:** Cost reduction + Speed improvement + Reliability enhancement
**Approach:** Both incremental quick wins and architectural improvements

---

## Current State Analysis

### Architecture
- **Root Agent** ([agent.py:21-38](c:\source\ai.dev\weather-lab\weather_agent\agent.py#L21-L38)) → **SequentialAgent** (weather_studio_team) → **forecast_writer_agent** → **forecast_speaker_agent**
- All operations are synchronous (no async/await)
- Session state stored in SQLite, shared via `tool_context.state`

### Performance Bottlenecks
1. **NO CACHING** - Every request hits OpenWeather API and regenerates LLM responses
2. **SEQUENTIAL EXECUTION** - Audio generation waits for text file write to complete
3. **NO RETRY LOGIC** - Single-attempt API calls
4. **NO RATE LIMITING** - Risk of hitting API quotas
5. **BLOCKING I/O** - Synchronous file writes and HTTP requests
6. **ALWAYS GENERATES AUDIO** - Even when not requested by user

---

## Phase 1: Quick Wins (Minimal Refactoring)

### 1.1 Weather API Response Caching ⭐ HIGH PRIORITY
**Impact:** 🔴 HIGH cost, 🔴 HIGH speed, 🟡 MEDIUM reliability

**Files to Create:**
- `c:\source\ai.dev\weather-lab\weather_agent\cache.py` - New caching infrastructure

**Files to Modify:**
- [get_current_weather.py](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_writer\tools\get_current_weather.py)

**Implementation:**
1. Create `TTLCache` class with time-based expiration (15-minute TTL)
2. Add `@cached_with_ttl(ttl=900)` decorator to `get_current_weather()` function
3. Cache key: `f"{city.lower()}_{units}"`

**Why 15 minutes?** Weather data updates every 10-30 minutes, so 15-min cache provides good balance.

**Expected Impact:**
- Reduces OpenWeather API calls by 80-95%
- Saves 200-500ms per cached request
- Prevents redundant API costs

---

### 1.2 Retry Logic with Exponential Backoff ⭐ HIGH PRIORITY
**Impact:** 🟢 LOW cost, 🟢 LOW speed, 🔴 HIGH reliability

**Files to Modify:**
- `c:\source\ai.dev\weather-lab\weather_agent\cache.py` - Add retry decorator
- [get_current_weather.py](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_writer\tools\get_current_weather.py#L63)
- [generate_audio.py](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_speaker\tools\generate_audio.py#L36)

**Implementation:**
1. Create `@retry_with_backoff(max_retries=3)` decorator
2. Exponential backoff: 1s → 2s → 4s delays
3. Only retry on transient failures (5xx errors, timeouts)
4. Don't retry on client errors (4xx)

**Expected Impact:**
- Prevents 95% of transient failure issues
- Adds 0-7 seconds only on failures (acceptable tradeoff)
- Production-grade resilience

---

### 1.3 Request Timeouts ⭐ HIGH PRIORITY
**Impact:** 🟢 LOW cost, 🟡 MEDIUM speed, 🔴 HIGH reliability

**Files to Modify:**
- [get_current_weather.py:63](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_writer\tools\get_current_weather.py#L63)

**Implementation:**
Change:
```python
response = requests.get(OPENWEATHER_BASE_URL, params=params)
```
To:
```python
response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=10)
```

**Timeout values:**
- OpenWeather API: 10 seconds
- Gemini TTS API: 30 seconds (larger audio generation)

**Expected Impact:**
- Prevents indefinite hangs on network issues
- Fails fast with clear error messages

---

### 1.4 Connection Pooling for HTTP Requests
**Impact:** 🟡 MEDIUM cost, 🟡 MEDIUM speed, 🟢 LOW reliability

**Files to Modify:**
- [get_current_weather.py](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_writer\tools\get_current_weather.py)

**Implementation:**
1. Create module-level session: `_weather_session = requests.Session()`
2. Replace `requests.get()` with `_weather_session.get()`
3. Reuses TCP connections to same host

**Expected Impact:**
- Reduces connection overhead by 50-100ms per request
- Saves TCP handshake time

---

### 1.5 Rate Limiting Protection
**Impact:** 🟢 LOW cost, 🟢 LOW speed, 🔴 HIGH reliability

**Files to Modify:**
- `c:\source\ai.dev\weather-lab\weather_agent\cache.py` - Add `RateLimiter` class
- [get_current_weather.py](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_writer\tools\get_current_weather.py)

**Implementation:**
1. Token bucket algorithm: 60 calls per 60 seconds
2. Add `@rate_limit(calls=60, period=60)` decorator
3. Gracefully delays requests when approaching limits

**Why 60/min?** OpenWeather free tier limit is 60 calls/minute.

**Expected Impact:**
- Prevents API quota errors in production
- Adds 0-1 second delay only when approaching limits

---

### 1.6 LLM Forecast Response Caching
**Impact:** 🔴 HIGH cost, 🔴 HIGH speed, 🟢 LOW reliability

**Files to Modify:**
- [forecast_writer/agent.py](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_writer\agent.py)

**Implementation:**
Session state approach (simpler than full caching):
1. Add `FORECAST_TIMESTAMP` to session state
2. Check if forecast exists and is < 30 minutes old
3. Skip LLM generation if cached forecast is still fresh

**Expected Impact:**
- Reduces LLM calls by 60-80%
- Saves 1-3 seconds per cached forecast
- Lower LLM costs

---

## Phase 2: Architectural Improvements

### 2.1 Conditional Audio Generation ⭐ HIGHEST PRIORITY
**Impact:** 🔴 HIGH cost, 🔴 HIGH speed, 🟡 MEDIUM reliability

**Files to Modify:**
- [agent.py](c:\source\ai.dev\weather-lab\weather_agent\agent.py)

**Implementation:**
1. **Use the commented-out root_agent** (lines 40-56) instead of current one
2. This version already has conditional logic: "if an audio output is requested"
3. Attach sub-agents directly to root_agent (not via SequentialAgent)
4. Root agent decides whether to invoke forecast_speaker_agent

**Current issue:** SequentialAgent always runs both sub-agents.

**Solution:** The commented code already handles this! Switch to it.

**Expected Impact:**
- Saves 100% of TTS costs when audio not needed (likely 50-70% of requests)
- Reduces response time by 2-5 seconds when audio skipped
- TTS is expensive: ~$0.001-0.01 per request

**Why this is #1 priority:** Biggest single cost/speed win with minimal code changes (just uncomment existing code).

---

### 2.2 Async/Await Refactor (Future Enhancement)
**Impact:** 🔴 HIGH speed, 🟡 MEDIUM cost, 🟡 MEDIUM reliability

**Status:** Investigate Google ADK async support first

**Why deferred:**
- Google ADK may not support async agents
- Phase 1 optimizations provide 70-85% improvements without async
- Can be added later if needed for scale

**If implemented:**
- Use `aiohttp` instead of `requests`
- Async file I/O
- Parallel execution of independent operations

---

## Phase 3: Additional Enhancements

### 3.1 Monitoring and Metrics
**Impact:** 🟢 LOW cost, 🟢 LOW speed, 🔴 HIGH reliability

**Files to Create:**
- `c:\source\ai.dev\weather-lab\weather_agent\utils\metrics.py`

**Implementation:**
1. `MetricsCollector` class to track:
   - API calls count
   - Cache hit/miss rates
   - Average latency
   - Error counts
   - Cost metrics (LLM tokens, TTS calls)
2. Add `@track_latency` decorator to tools
3. Periodic metrics summary logging

**Expected Impact:**
- Enables data-driven optimization
- Identifies bottlenecks proactively
- Measures ROI of optimizations

---

### 3.2 File Cleanup Strategy
**Impact:** 🟢 LOW cost, 🟢 LOW speed, 🟢 LOW reliability

**Files to Create:**
- `c:\source\ai.dev\weather-lab\weather_agent\utils\cleanup.py`

**Files to Modify:**
- [agent.py](c:\source\ai.dev\weather-lab\weather_agent\agent.py) - Call cleanup on init

**Implementation:**
1. Delete forecast files older than 7 days
2. Run on agent initialization or periodic background task
3. Prevents disk space issues over time

---

## Implementation Sequence

### Week 1: Critical Quick Wins
1. ✅ **Conditional Audio** (Phase 2.1) - Uncomment existing code
2. ✅ **Weather API Caching** (Phase 1.1) - Create cache.py
3. ✅ **Request Timeouts** (Phase 1.3) - Add timeout parameter
4. ✅ **Retry Logic** (Phase 1.2) - Add retry decorator

**Expected after Week 1:** 70-80% cost reduction, 50-60% speed improvement

### Week 2: Reliability & Monitoring
5. ✅ **Connection Pooling** (Phase 1.4)
6. ✅ **Rate Limiting** (Phase 1.5)
7. ✅ **Monitoring** (Phase 3.1)
8. ✅ **LLM Caching** (Phase 1.6)

**Expected after Week 2:** 85-90% cost reduction, 60-70% speed improvement, production-ready reliability

### Week 3: Polish
9. ✅ **File Cleanup** (Phase 3.2)
10. ✅ **Performance testing and tuning**

---

## Critical Files Summary

### New Files to Create
1. **cache.py** - Caching, retry, rate limiting infrastructure
2. **utils/metrics.py** - Monitoring and metrics tracking
3. **utils/cleanup.py** - File cleanup utilities

### Files to Modify
1. **[agent.py:40-56](c:\source\ai.dev\weather-lab\weather_agent\agent.py#L40-L56)** - Uncomment conditional audio logic
2. **[get_current_weather.py:63](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_writer\tools\get_current_weather.py#L63)** - Add caching, retry, timeout, pooling
3. **[generate_audio.py:36](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_speaker\tools\generate_audio.py#L36)** - Add retry logic
4. **[forecast_writer/agent.py](c:\source\ai.dev\weather-lab\weather_agent\sub_agents\forecast_writer\agent.py)** - LLM response caching
5. **requirements.txt** - No new dependencies needed! All using built-in capabilities.

---

## Expected Overall Impact

**Phase 1 Complete:**
- 💰 Cost reduction: 70-85%
- ⚡ Speed improvement: 40-60%
- 🛡️ Reliability: +90%

**Phase 2 Complete:**
- 💰 Cost reduction: Additional 20-40% (total: 85-95%)
- ⚡ Speed improvement: Additional 20-30% (total: 60-80%)
- 🛡️ Reliability: +95%

**Phase 3 Complete:**
- 💰 Cost reduction: Total 80-95%
- ⚡ Speed improvement: Total 60-90%
- 🛡️ Reliability: Near 100% uptime

---

## Risk Mitigation

**Low Risk Changes:**
- Conditional audio (existing code)
- Timeouts (simple parameter)
- Connection pooling (drop-in replacement)

**Medium Risk Changes:**
- Caching (test TTL values)
- Retry logic (verify exponential backoff)
- Rate limiting (monitor for false positives)

**Testing Strategy:**
1. Unit test each decorator/utility
2. Integration test full weather request flow
3. Load test with 100 requests/minute
4. Monitor cache hit rates and API call reduction

**Rollback Plan:**
- Each optimization is independent
- Can disable decorators without breaking core functionality
- Phase 1 changes don't modify agent architecture
