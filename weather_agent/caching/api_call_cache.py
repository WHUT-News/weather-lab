"""
Caching infrastructure for weather agent optimization.

This module provides:
- TTLCache: Time-based cache with automatic expiration
- cached_with_ttl: Decorator for caching function results with TTL
"""

import os
import time
from functools import wraps
from typing import Callable, Any, Dict, Tuple

# Default TTL: 1 hour, configurable via environment variable in hours
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL", "1")) * 3600


class TTLCache:
    """
    Time-To-Live cache that automatically expires entries after a specified duration.

    Thread-safe for basic operations. For high-concurrency scenarios, consider
    adding threading.Lock() for cache modifications.
    """

    def __init__(self):
        # Store tuples of (value, timestamp)
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str, ttl: int) -> Any | None:
        """
        Retrieve a cached value if it exists and hasn't expired.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            Cached value if valid, None if expired or not found
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            current_time = time.time()

            # Check if cache entry is still valid
            if current_time - timestamp < ttl:
                return value

            # Cache expired, remove it
            del self._cache[key]

        return None

    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def size(self) -> int:
        """Return the number of cached entries (including expired ones)."""
        return len(self._cache)

    def cleanup_expired(self, ttl: int) -> int:
        """
        Remove all expired entries from the cache.

        Args:
            ttl: Time-to-live in seconds

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


def cached_with_ttl(ttl: int = None):
    """
    Decorator that caches function results with time-based expiration.

    Args:
        ttl: Time-to-live in seconds (default: 1 hour, configurable via CACHE_TTL env var in hours)

    Usage:
        @cached_with_ttl(ttl=900)
        def expensive_function(arg1, arg2):
            # Expensive computation here
            return result

    Note: Cache key is generated from function name and arguments.
    Functions with complex arguments (objects, etc.) may not cache correctly.
    Best used with simple arguments (strings, numbers, tuples).
    """
    if ttl is None:
        ttl = CACHE_TTL_SECONDS
    cache = TTLCache()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            # Convert args and kwargs to a hashable representation
            args_key = str(args)
            kwargs_key = str(sorted(kwargs.items()))
            cache_key = f"{func.__name__}:{args_key}:{kwargs_key}"

            # Try to get from cache
            cached_result = cache.get(cache_key, ttl)
            if cached_result is not None:
                return cached_result

            # Cache miss - execute function
            result = func(*args, **kwargs)

            # Store result in cache
            cache.set(cache_key, result)

            return result

        # Attach cache management methods to wrapper
        wrapper.cache = cache  # type: ignore
        wrapper.cache_clear = cache.clear  # type: ignore
        wrapper.cache_size = cache.size  # type: ignore

        return wrapper

    return decorator
