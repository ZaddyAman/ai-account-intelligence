"""
Web Scraping Service - Local Only (No External APIs)

Uses a tiered approach:
- Tier 1: Sitemap Discovery (local HTTP requests)
- Tier 2: API Detection (local HTTP requests)
- Tier 3: Playwright (JavaScript rendering - local)
- Tier 4: BeautifulSoup (HTML parsing - local)

No external API dependencies - fully self-hosted!
"""

import asyncio
import hashlib
import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional
from dataclasses import dataclass

from backend.services.cache_service import scrape_cache, sitemap_cache, api_cache
from backend.services.sitemap_service import sitemap_discovery, COMPANY_URL_PATTERNS
from backend.services.api_discovery_service import api_discovery


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
    source: str  # 'sitemap', 'api', 'playwright', 'bs4'
    urls_discovered: list[str] = None
    
    def __post_init__(self):
        if self.urls_discovered is None:
            self.urls_discovered = []


def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


# ── Playwright Management ─────────────────────────────────────────────────

# Playwright is now used via sync_api in a thread to avoid asyncio issues with Python 3.13


# ── Tier 1: Sitemap Discovery ───────────────────────────────────────────

async def _tier0_sitemap_discovery(domain: str) -> ScrapeResult:
    """
    Tier 0: Discover URLs via sitemap (fastest method).
    """
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
    
    if result.is_valid:
        sitemap_cache.set(cache_key, response)
    
    return response


# ── Tier 2: API Detection ──────────────────────────────────────────────

async def _tier1_api_detection(domain: str) -> ScrapeResult:
    """
    Tier 1: Check for API endpoints (fast data extraction).
    """
    cache_key = f"api:{domain}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    
    api_result = await api_discovery.discover(domain)
    
    if api_result.has_public_api:
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


# ── Tier 3: Playwright (JavaScript Rendering) ───────────────────────────

# NOTE: Playwright is disabled due to Python 3.13 asyncio incompatibility
# The asyncio.subprocess implementation is incomplete in Python 3.13
# Using BeautifulSoup instead which works perfectly

async def _tier2_playwright(url: str) -> ScrapeResult:
    """
    Tier 2: Playwright - JavaScript rendering for dynamic pages.
    Uses thread-based execution to run sync Playwright in async context.
    """
    import logging
    from concurrent.futures import ThreadPoolExecutor
    from playwright.sync_api import sync_playwright
    
    logger = logging.getLogger(__name__)
    
    def _sync_playwright_scrape(url: str) -> tuple[str, dict]:
        """Run sync Playwright in a thread."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Get page title
                title = page.title()
                
                # Extract main content
                content = page.content()
                browser.close()
                
                return content, {"title": title, "url": url}
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return "", {"error": str(e)}
    
    try:
        # Run Playwright in thread to avoid asyncio issues
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            future = executor.submit(_sync_playwright_scrape, url)
            html_content, metadata = future.result(timeout=30)
        
        if not html_content:
            return ScrapeResult(
                markdown="",
                metadata=metadata,
                success=False,
                source="playwright",
            )
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
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
        
        return ScrapeResult(
            markdown=md,
            metadata=metadata,
            success=bool(md and len(md) > 50),
            source="playwright",
        )
    except Exception as e:
        logger.error(f"Playwright failed for {url}: {e}")
        return ScrapeResult(
            markdown="",
            metadata={"error": str(e)},
            success=False,
            source="playwright",
        )


# ── Tier 4: BeautifulSoup Fallback ──────────────────────────────────────

async def _tier3_bs4_scrape(url: str) -> ScrapeResult:
    """
    Tier 3: BeautifulSoup fallback - always available, no external dependencies.
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
    Scrape a URL with intelligent tiered fallback (all local - no external APIs!).
    
    Args:
        url: URL to scrape
        force_tier: Optional tier to force (0=sitemap, 1=api, 2=playwright, 3=bs4)
        
    Returns:
        ScrapeResult with content and metadata
        
    Tier Progression:
        0: Sitemap discovery (URL collection)
        1: API detection (structured data)
        2: Playwright (JavaScript rendering) - SKIPPED due to compatibility issues
        3: BeautifulSoup (HTML parsing - default)
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
        # Try from the specified tier onwards (e.g., force_tier=2 means try 2, then 3)
        tiers_to_try = list(range(force_tier, 4))
    else:
        # Default: Try all tiers - Sitemap (0) -> API (1) -> Playwright (2) -> BeautifulSoup (3)
        tiers_to_try = [0, 1, 2, 3]
    
    # Execute tiers
    for tier in tiers_to_try:
        result = None
        
        if tier == 0:
            result = await _tier0_sitemap_discovery(domain)
        elif tier == 1:
            result = await _tier1_api_detection(domain)
        elif tier == 2:
            result = await _tier2_playwright(url)
        elif tier == 3:
            result = await _tier3_bs4_scrape(url)
        
        if result and result.success:
            # Cache successful results
            if result.markdown:
                cache_data = {
                    "markdown": result.markdown,
                    "metadata": result.metadata,
                    "success": result.success,
                    "source": result.source,
                }
                scrape_cache.set(ck, cache_data)
            return result
    
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
    """
    sitemap_result = await _tier0_sitemap_discovery(domain)
    
    if sitemap_result.urls_discovered:
        about_patterns = COMPANY_URL_PATTERNS["about"] + COMPANY_URL_PATTERNS["team"]
        
        relevant_urls = []
        for url in sitemap_result.urls_discovered:
            for pattern in about_patterns:
                if re.search(pattern, url, re.I):
                    relevant_urls.append(url)
                    break
        
        for url in relevant_urls[:5]:
            result = await scrape_url(url)
            if result.success and len(result.markdown) > 100:
                return result
    
    # Fallback: try common paths
    for path in ["/about", "/about-us", "/team", "/leadership", "/our-team"]:
        result = await scrape_url(f"https://{domain}{path}")
        if result.success and len(result.markdown) > 100:
            return result
    
    return ScrapeResult(
        markdown="",
        metadata={},
        success=False,
        source="about",
    )


async def scrape_multiple_urls(urls: list[str], max_concurrent: int = 3) -> list[ScrapeResult]:
    """Scrape multiple URLs with concurrency control."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def scrape_with_limit(url: str) -> ScrapeResult:
        async with semaphore:
            return await scrape_url(url)
    
    tasks = [scrape_with_limit(url) for url in urls]
    return await asyncio.gather(*tasks)


# ── Utility Functions ───────────────────────────────────────────────────

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


async def cleanup_playwright():
    """Cleanup Playwright browser instances on shutdown."""
    await PlaywrightManager.close()
