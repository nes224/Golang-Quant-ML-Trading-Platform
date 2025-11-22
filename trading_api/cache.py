import time
from functools import wraps
from typing import Dict, Any, Optional

class SimpleCache:
    """
    Simple in-memory cache with TTL (Time To Live).
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if time.time() > entry['expires_at']:
            # Expired, remove it
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl_seconds: int = 5):
        """Set cache value with TTL."""
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl_seconds
        }
    
    def clear(self):
        """Clear all cache."""
        self._cache.clear()
    
    def remove(self, key: str):
        """Remove specific key."""
        if key in self._cache:
            del self._cache[key]

# Global cache instance
cache = SimpleCache()

def cached(ttl_seconds: int = 5):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Time to live in seconds (default 5)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Not in cache, call function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl_seconds)
            
            return result
        return wrapper
    return decorator
