"""
cache.py — In-memory TTL cache for option chain data.
Uses threading.Lock for thread safety.
"""
import threading
import time
from datetime import datetime

class TTLCache:
    """Thread-safe in-memory cache with time-to-live expiry."""
    
    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> dict | None:
        """Returns None if key missing or expired."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if time.time() - entry['time'] > self.ttl_seconds:
                del self._cache[key]
                return None
                
            return entry['value']
    
    def set(self, key: str, value: dict) -> None:
        """Stores value with current timestamp."""
        with self._lock:
            self._cache[key] = {
                'value': value,
                'time': time.time(),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def invalidate(self, key: str) -> None:
        """Removes key if present."""
        with self._lock:
            self._cache.pop(key, None)
    
    def get_age_seconds(self, key: str) -> float | None:
        """Returns seconds since cached. None if not in cache."""
        with self._lock:
            if key not in self._cache:
                return None
            return time.time() - self._cache[key]['time']
    
    def get_timestamp(self, key: str) -> str | None:
        """Returns ISO timestamp of when item was cached. None if not in cache."""
        with self._lock:
            if key not in self._cache:
                return None
            return self._cache[key]['timestamp']

# Module-level singleton
option_chain_cache = TTLCache(ttl_seconds=60)