"""
Anti-blocking measures for web scraping.
Includes proxy rotation, user-agent rotation, and fingerprint management.
"""

import random
import asyncio
from typing import Optional
from dataclasses import dataclass
import httpx


@dataclass
class RequestConfig:
    """Configuration for request to avoid blocking."""
    headers: dict
    proxy: Optional[str]
    cookies: Optional[dict]
    fingerprint_id: str


class AntiBlocker:
    """Manages anti-blocking measures."""
    
    # Rotating User-Agents
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    ]
    
    # Common proxy sources (would integrate with proxy service in production)
    PROXY_POOL = []  # Add proxy URLs here
    
    def __init__(self):
        self._request_count = 0
        self._last_request_time = 0
    
    def get_config(self) -> RequestConfig:
        """Get configuration for next request."""
        self._request_count += 1
        
        return RequestConfig(
            headers={
                "User-Agent": random.choice(self.USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            },
            proxy=random.choice(self.PROXY_POOL) if self.PROXY_POOL else None,
            cookies=None,
            fingerprint_id=f"fp_{self._request_count}",
        )
    
    async def rate_limit(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """Apply rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < min_delay:
            delay = random.uniform(min_delay, max_delay)
            await asyncio.sleep(delay)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    def should_use_proxy(self) -> bool:
        """Determine if proxy should be used (based on failure rate)."""
        # Could integrate with failure tracking
        return random.random() < 0.1  # 10% of requests use proxy


# Module-level instance
anti_blocker = AntiBlocker()


class ProtectedClient(httpx.AsyncClient):
    """
    HTTP client with built-in anti-blocking measures.
    """
    
    def __init__(self, *args, **kwargs):
        self._anti_blocker = AntiBlocker()
        super().__init__(*args, **kwargs)
    
    async def get(self, url: str, **kwargs):
        """Execute GET request with anti-blocking measures."""
        config = self._anti_blocker.get_config()
        
        # Merge headers
        kwargs.setdefault("headers", {}).update(config.headers)
        
        # Add proxy if needed
        if config.proxy:
            kwargs.setdefault("proxy", config.proxy)
        
        # Apply rate limiting
        await self._anti_blocker.rate_limit()
        
        return await super().get(url, **kwargs)
