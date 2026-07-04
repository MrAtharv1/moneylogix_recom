"""cache.py — In-memory TTL cache with max size."""
import asyncio
import time
from datetime import datetime

class TTLCache:
    def __init__(self, ttl_seconds: int = 60, max_entries: int = 100):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache = {}
        self._order = []
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict | None:
        async with self._lock:
            if key not in self._cache:
                return None
            entry = self._cache[key]
            if time.time() - entry['time'] > self.ttl_seconds:
                del self._cache[key]
                self._order.remove(key)
                return None
            return entry['value']

    async def set(self, key: str, value: dict) -> None:
        async with self._lock:
            if key in self._cache:
                self._order.remove(key)
            elif len(self._cache) >= self.max_entries:
                oldest = self._order.pop(0)
                del self._cache[oldest]
            self._cache[key] = {'value': value, 'time': time.time()}
            self._order.append(key)

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._order.remove(key)

    async def get_age_seconds(self, key: str) -> float | None:
        async with self._lock:
            if key not in self._cache:
                return None
            return time.time() - self._cache[key]['time']

    async def get_timestamp(self, key: str) -> str | None:
        async with self._lock:
            if key not in self._cache:
                return None
            return datetime.utcnow().isoformat()

option_chain_cache = TTLCache(ttl_seconds=60, max_entries=100)