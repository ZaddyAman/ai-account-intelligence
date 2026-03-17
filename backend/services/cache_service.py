"""
In-memory TTL cache service with optional disk persistence and analytics.

Used by:
- llm_service (prompt caching)
- firecrawl_service (scrape caching)
- sitemap_service (sitemap caching)
- api_discovery_service (API discovery caching)
"""

import json
import time
import asyncio
import hashlib
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests


class TTLCache:
    """Thread-safe TTL cache with optional disk persistence."""
    
    def __init__(
        self, 
        ttl_seconds: int = 300, 
        max_size: int = 256,
        persist_path: Optional[str] = None,
    ):
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._persist_path = persist_path
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = Lock()
        self._stats = CacheStats()
        
        # Load from disk if path provided
        if persist_path:
            self._load()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            self._stats.total_requests += 1
            
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            
            value, expiry = entry
            if time.monotonic() > expiry:
                del self._store[key]
                self._stats.misses += 1
                return None
            
            self._stats.hits += 1
            return value
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        with self._lock:
            # Evict oldest if at capacity
            if len(self._store) >= self._max_size and key not in self._store:
                oldest_key = min(self._store, key=lambda k: self._store[k][1])
                del self._store[oldest_key]
                self._stats.evictions += 1
            
            self._store[key] = (value, time.monotonic() + self._ttl)
            
            # Persist to disk
            if self._persist_path:
                self._persist()
    
    def _persist(self):
        """Persist cache to disk."""
        try:
            Path(self._persist_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, 'w') as f:
                json.dump(self._store, f)
        except Exception:
            pass  # Fail silently
    
    def _load(self):
        """Load cache from disk."""
        try:
            if Path(self._persist_path).exists():
                with open(self._persist_path, 'r') as f:
                    self._store = json.load(f)
                    # Filter expired entries
                    now = time.monotonic()
                    self._store = {
                        k: v for k, v in self._store.items()
                        if v[1] > now
                    }
        except Exception:
            pass
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._store.clear()
            self._stats = CacheStats()
    
    @property
    def stats(self) -> CacheStats:
        return self._stats
    
    def __len__(self) -> int:
        return len(self._store)


# ── Shared Cache Instances ───────────────────────────────────────────

# LLM prompt cache — 10 min TTL
llm_cache = TTLCache(ttl_seconds=600, max_size=512)

# Web scrape cache — 5 min TTL
scrape_cache = TTLCache(ttl_seconds=300, max_size=128)

# Sitemap cache — 1 hour TTL (sitemaps change infrequently)
sitemap_cache = TTLCache(ttl_seconds=3600, max_size=256)

# API response cache — 5 min TTL
api_cache = TTLCache(ttl_seconds=300, max_size=256)
