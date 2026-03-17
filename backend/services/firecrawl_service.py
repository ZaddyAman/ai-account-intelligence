"""
Firecrawl web scraping service with intelligent tiered fallback.

Tier 1: Sitemap Discovery (60x faster URL discovery)
Tier 2: API Detection (10-100x faster data extraction)  
Tier 3: Firecrawl (rich markdown extraction, handles JS)
Tier 4: BeautifulSoup (always-available fallback)
"""

import asyncio
import hashlib
import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional
from dataclasses import dataclass

from backend.config import FIRECRAWL_API_KEY
from backend.services.cache_service import scrape_cache, sitemap_cache, api_cache
from backend.services.sitemap_service import sitemap_discovery, COMPANY_URL_PATTERNS
from backend.services.api_discovery_service import api_discovery


# Initialize Firecrawl (optional - works without API key for basic features)
try:
    from firecrawl import FirecrawlApp
    firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY else None
except ImportError:
    firecrawl_app = None


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class ScrapeResult:
    """Standardized scrape result."""
    markdown: str
    metadata: dict
    success: bool
    source: str  # 'sitemap', 'api', 'firecrawl', 'bs4'
    urls_discovered: list[str] = None
    
    def __post_init__(self):
        if self.urls_discovered is None:
            self.urls_discovered = []


def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


# ── Tier 1: Sitemap Discovery ───────────────────────────────────────────

async def _tier0_sitemap_discovery(domain: str) -> ScrapeResult:
    """
    Tier 0: Discover URLs via sitemap (fastest method).
    
    Returns discovered URLs for subsequent scraping.
    """
    # Check cache first
    cache_key = f"sitemap:{domain}"
    cached = sitemap_cache.get(cache_key)
    if cached:
        return cached
    
    result = await sitemap_discovery.discover(domain)
    
    response = ScrapeResult(
        markdown="",
        metadata={"urls": result.urls, "source": result.source},
        success=result.is_valid,
        source="sitemap",
        urls_discovered=result.urls if result.is_valid else [],
    )
    
    # Cache successful results
    if result.is_valid:
        sitemap_cache.set(cache_key, response)
    
    return response


# ── Tier 2: API Detection ──────────────────────────────────────────────

async def _tier1_api_detection(domain: str) -> ScrapeResult:
    """
    Tier 1: Check for API endpoints (fast data extraction).
    """
    # Check cache first
    cache_key = f"api:{domain}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    
    api_result = await api_discovery.discover(domain)
    
    if api_result.has_public_api:
        # Try to fetch company data via API
        data = await api_discovery.fetch_company_data(domain, "about")
        if data:
            import json
            response = ScrapeResult(
                markdown=json.dumps(data, indent=2),
                metadata={"endpoints": [e.url for e in api_result.endpoints]},
                success=True,
                source="api",
            )
            api_cache.set(cache_key, response)
            return response
    
    response = ScrapeResult(
        markdown="",
        metadata={},
        success=False,
        source="api",
    )
    api_cache.set(cache_key, response)
    
    return response


# ── Tier 3: Firecrawl ──────────────────────────────────────────────────

async def _tier2_firecrawl(url: str) -> ScrapeResult:
    """
    Tier 2: Firecrawl with intelligent error handling.
    """
    if not firecrawl_app:
        return ScrapeResult(
            markdown="",
            metadata={"error": "No Firecrawl API key"},
            success=False,
            source="firecrawl",
        )
    
    try:
        # Run in thread since SDK is synchronous
        result = await asyncio.to_thread(firecrawl_app.scrape_url, url)
        
        # Handle different response formats
        if hasattr(result, "markdown"):
            md = result.markdown or ""
            meta = getattr(result, "metadata", {}) or {}
        elif isinstance(result, dict):
            md = result.get("markdown", "") or result.get("content", "")
            meta = result.get("metadata", {})
        else:
            md = ""
            meta = {}
        
        if md and len(md) > 50:
            return ScrapeResult(
                markdown=md,
                metadata=meta,
                success=True,
                source="firecrawl",
            )
        
        print(f"[FIRECRAWL EMPTY] {url}")
        
    except Exception as e:
        print(f"[FIRECRAWL ERROR] {url}: {e}")
    
    return ScrapeResult(
        markdown="",
        metadata={},
        success=False,
        source="firecrawl",
    )


# ── Tier 4: BeautifulSoup Fallback ──────────────────────────────────────

async def _tier3_bs4_scrape(url: str) -> ScrapeResult:
    """
    Tier 3: BeautifulSoup fallback - always available.
    """
    try:
        async with httpx.AsyncClient(
            timeout=15, 
            follow_redirects=True, 
            headers=_HEADERS
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Remove clutter
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        
        # Extract main content
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"id": re.compile(r"content|main", re.I)})
            or soup.find("div", {"class": re.compile(r"content|main|body", re.I)})
            or soup.body
        )
        
        if main:
            lines = []
            for tag in main.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
                text = tag.get_text(separator=" ", strip=True)
                if not text or len(text) < 10:
                    continue
                if tag.name in ("h1", "h2"):
                    lines.append(f"\n## {text}\n")
                elif tag.name in ("h3", "h4"):
                    lines.append(f"\n### {text}\n")
                else:
                    lines.append(text)
            md = "\n".join(lines)
        else:
            md = soup.get_text(separator="\n", strip=True)
        
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        
        title = soup.title.string.strip() if soup.title else ""
        
        return ScrapeResult(
            markdown=md,
            metadata={"title": title, "url": url},
            success=bool(md and len(md) > 50),
            source="bs4",
        )
        
    except Exception as e:
        print(f"[BS4 ERROR] {url}: {e}")
        return ScrapeResult(
            markdown="",
            metadata={"error": str(e)},
            success=False,
            source="bs4",
        )


# ── Main Entry Point: Intelligent Tiered Scraping ────────────────────────

async def scrape_url(url: str, force_tier: Optional[int] = None) -> ScrapeResult:
    """
    Scrape a URL with intelligent tiered fallback.
    
    Args:
        url: URL to scrape
        force_tier: Optional tier to force (0=sitemap, 1=api, 2=firecrawl, 3=bs4)
        
    Returns:
        ScrapeResult with content and metadata
        
    Tier Progression:
        0: Sitemap discovery (fastest, for URL collection)
        1: API detection (fast, for structured data)
        2: Firecrawl (medium, handles JS)
        3: BeautifulSoup (slowest, always works)
    """
    # Normalize URL
    if not url.startswith("http"):
        url = f"https://{url}"
    
    # Extract domain for tier 0/1
    domain = url.replace("https://", "").replace("http://", "").split("/")[0]
    
    # Check cache first
    ck = _cache_key(url)
    cached = scrape_cache.get(ck)
    if cached is not None and force_tier is None:
        return ScrapeResult(**cached)
    
    # Determine which tiers to try
    tiers_to_try = []
    
    if force_tier is not None:
        # Force specific tier
        tiers_to_try = [force_tier]
    else:
        # Default tier progression: try firecrawl first, then bs4
        # Optionally can enable sitemap/api discovery as first tiers
        tiers_to_try = [2, 3]
    
    # Execute tiers
    for tier in tiers_to_try:
        result = None
        
        if tier == 0:
            result = await _tier0_sitemap_discovery(domain)
        elif tier == 1:
            result = await _tier1_api_detection(domain)
        elif tier == 2:
            result = await _tier2_firecrawl(url)
        elif tier == 3:
            result = await _tier3_bs4_scrape(url)
        
        if result and result.success:
            # Cache successful results
            if result.markdown:  # Only cache actual content
                cache_data = {
                    "markdown": result.markdown,
                    "metadata": result.metadata,
                    "success": result.success,
                    "source": result.source,
                }
                scrape_cache.set(ck, cache_data)
            return result
    
    # All tiers failed
    return ScrapeResult(
        markdown="",
        metadata={"error": "All scraping tiers failed"},
        success=False,
        source="failed",
    )


# ── Convenience Functions ───────────────────────────────────────────────

async def scrape_company_site(domain: str) -> ScrapeResult:
    """Scrape a company's main website page."""
    return await scrape_url(domain)


async def scrape_company_about(domain: str) -> ScrapeResult:
    """
    Scrape company's about/team page with intelligent URL discovery.
    
    First tries to find relevant URLs via sitemap, then scrapes them.
    """
    # First, discover all URLs on the domain
    sitemap_result = await _tier0_sitemap_discovery(domain)
    
    if sitemap_result.urls_discovered:
        # Filter for about/team pages
        about_patterns = COMPANY_URL_PATTERNS["about"] + COMPANY_URL_PATTERNS["team"]
        
        relevant_urls = []
        for url in sitemap_result.urls_discovered:
            for pattern in about_patterns:
                if re.search(pattern, url, re.I):
                    relevant_urls.append(url)
                    break
        
        # Try scraping each relevant URL with BeautifulSoup (tier 3) - more reliable
        if relevant_urls:
            # Scrape up to 5 URLs in parallel
            results = await scrape_multiple_urls(relevant_urls[:5], max_concurrent=3)
            for result in results:
                if result.success and len(result.markdown) > 100:
                    return result
    
    # Fallback: try common paths directly in parallel
    # Also try with www prefix if original domain didn't work
    fallback_urls = []
    domains_to_try = [domain]
    if not domain.startswith("www."):
        domains_to_try.append(f"www.{domain}")
    
    for base_domain in domains_to_try:
        for path in ["/about", "/about-us", "/team", "/leadership", "/our-team"]:
            fallback_urls.append(f"https://{base_domain}{path}")
    
    # Scrape all fallback URLs in parallel
    if fallback_urls:
        results = await scrape_multiple_urls(fallback_urls[:10], max_concurrent=5)
        for result in results:
            if result.success and len(result.markdown) > 100:
                return result
    
    return ScrapeResult(
        markdown="",
        metadata={},
        success=False,
        source="about",
    )


async def scrape_multiple_urls(urls: list[str], max_concurrent: int = 3) -> list[ScrapeResult]:
    """
    Scrape multiple URLs with concurrency control.
    
    Args:
        urls: List of URLs to scrape
        max_concurrent: Maximum concurrent requests
        
    Returns:
        List of ScrapeResult objects
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def scrape_with_limit(url: str) -> ScrapeResult:
        async with semaphore:
            return await scrape_url(url)
    
    tasks = [scrape_with_limit(url) for url in urls]
    return await asyncio.gather(*tasks)


# ── Legacy Compatibility ───────────────────────────────────────────────

async def get_sitemap_urls(domain: str) -> list[str]:
    """Get all URLs from sitemap for a domain."""
    result = await _tier0_sitemap_discovery(domain)
    return result.urls_discovered if result.urls_discovered else []


async def discover_apis(domain: str) -> dict:
    """Discover API endpoints for a domain."""
    result = await api_discovery.discover(domain)
    return {
        "endpoints": [{"url": e.url, "type": e.response_type} for e in result.endpoints],
        "has_api": result.has_public_api,
        "graphql": result.graphql_endpoint,
    }
