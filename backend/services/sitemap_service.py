"""
Sitemap-based URL discovery service.
Provides instant URL extraction from sitemap.xml and robots.txt.
"""

import re
import httpx
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

try:
    import bs4
except ImportError:
    bs4 = None


@dataclass
class SitemapResult:
    """Result from sitemap discovery."""
    urls: list[str]
    source: str  # 'sitemap_xml', 'robots_txt', 'none'
    page_count: int
    is_valid: bool


class SitemapDiscovery:
    """Discovers and parses sitemaps for URL extraction."""
    
    COMMON_SITEMAP_LOCATIONS = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap.xml.gz",
        "/sitemaps/sitemap.xml",
        "/sitemap-news.xml",
        "/sitemap1.xml",
        "/sitemap2.xml",
        "/sitemap_index.xml",
        "/sitemap/main.xml",
        "/sitemaps.xml",
        "/sitemap/sitemap.xml",
    ]
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def discover(self, domain: str) -> SitemapResult:
        """
        Main entry point: attempt sitemap discovery for a domain.
        
        Returns SitemapResult with discovered URLs or empty list.
        """
        # Normalize domain - handle redirects
        if not domain.startswith(("http://", "https://")):
            domain = f"https://{domain}"
        
        base_url = domain.rstrip("/")
        
        # Try both with and without www
        domains_to_try = [base_url]
        parsed = urlparse(base_url)
        if not parsed.netloc.startswith("www."):
            domains_to_try.append(base_url.replace(parsed.netloc, f"www.{parsed.netloc}"))
        
        for base_url in domains_to_try:
            # Priority 1: Check robots.txt for sitemap directives
            robots_urls = await self._check_robots_txt(base_url)
            if robots_urls:
                # Filter for relevant company URLs
                relevant = self._filter_relevant_urls(robots_urls)
                if relevant:
                    return SitemapResult(
                        urls=relevant,
                        source="robots_txt",
                        page_count=len(relevant),
                        is_valid=True
                    )
            
            # Priority 2: Check common sitemap locations
            for location in self.COMMON_SITEMAP_LOCATIONS:
                sitemap_url = base_url + location
                urls = await self._parse_sitemap(sitemap_url)
                if urls:
                    # Filter for relevant company URLs
                    relevant = self._filter_relevant_urls(urls)
                    if relevant:
                        return SitemapResult(
                            urls=relevant,
                            source="sitemap_xml",
                            page_count=len(relevant),
                            is_valid=True
                        )
            
            # Priority 3: Try to find sitemap from homepage links
            homepage_urls = await self._find_sitemap_from_homepage(base_url)
            if homepage_urls:
                return SitemapResult(
                    urls=homepage_urls,
                    source="homepage_scan",
                    page_count=len(homepage_urls),
                    is_valid=True
                )
        
        # No sitemap found
        return SitemapResult(
            urls=[],
            source="none",
            page_count=0,
            is_valid=False
        )
    
    def _filter_relevant_urls(self, urls: list[str]) -> list[str]:
        """Filter URLs to keep only relevant company pages."""
        import re
        
        # Combine all patterns
        all_patterns = []
        for patterns in COMPANY_URL_PATTERNS.values():
            all_patterns.extend(patterns)
        
        relevant = []
        for url in urls:
            for pattern in all_patterns:
                if re.search(pattern, url, re.I):
                    relevant.append(url)
                    break
        
        # If no relevant URLs found, return all URLs (let the scraper decide)
        return relevant if relevant else urls[:50]
    
    async def _find_sitemap_from_homepage(self, base_url: str) -> list[str]:
        """Try to find sitemap links from the homepage."""
        if bs4 is None:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(base_url, headers=self._headers)
                if resp.status_code != 200:
                    return []
                
                soup = bs4.BeautifulSoup(resp.text, "html.parser")
                
                # Look for sitemap links in the footer or header
                sitemap_links = []
                for link in soup.find_all("a", href=True):
                    href = link["href"].lower()
                    if "sitemap" in href:
                        full_url = href if href.startswith("http") else base_url + href
                        sitemap_links.append(full_url)
                
                # Try parsing any found sitemap links
                for sitemap_url in sitemap_links[:3]:
                    urls = await self._parse_sitemap(sitemap_url)
                    if urls:
                        return urls
                        
        except Exception:
            pass
        
        return []
    
    async def _check_robots_txt(self, base_url: str) -> list[str]:
        """Parse robots.txt for Sitemap directives."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{base_url}/robots.txt", headers=self._headers)
                if resp.status_code != 200:
                    return []
                
                # Find all Sitemap: directives
                sitemap_pattern = re.compile(r'^Sitemap:\s*(.+)$', re.MULTILINE)
                matches = sitemap_pattern.findall(resp.text)
                
                urls = []
                for match in matches:
                    sitemap_url = match.strip()
                    # Parse this sitemap
                    parsed_urls = await self._parse_sitemap(sitemap_url)
                    urls.extend(parsed_urls)
                
                return urls
        except Exception:
            return []
    
    async def _parse_sitemap(self, sitemap_url: str) -> list[str]:
        """Parse XML sitemap and extract all URLs."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(sitemap_url, headers=self._headers)
                if resp.status_code != 200:
                    return []
                
                content = resp.text
                
                # Handle gzipped sitemaps
                if sitemap_url.endswith('.gz'):
                    import gzip
                    content = gzip.decompress(content).decode('utf-8')
                
                return self._extract_urls_from_xml(content, sitemap_url)
                
        except Exception:
            return []
    
    def _extract_urls_from_xml(self, xml_content: str, base_url: str) -> list[str]:
        """Extract URL loc entries from XML sitemap."""
        urls = []
        
        try:
            # Try parsing as XML
            root = ET.fromstring(xml_content)
            
            # Handle sitemap index (contains other sitemaps)
            if 'sitemapindex' in root.tag.lower():
                for sitemap in root.findall('.//{*}sitemap'):
                    loc = sitemap.find('{*}loc')
                    if loc is not None:
                        # Recursively parse nested sitemaps
                        # (simplified: just add the sitemap URL)
                        urls.append(loc.text)
            
            # Handle regular sitemap
            elif 'urlset' in root.tag.lower():
                for url in root.findall('.//{*}url'):
                    loc = url.find('{*}loc')
                    if loc is not None:
                        urls.append(loc.text)
                        
        except ET.ParseError:
            # Not valid XML, try parsing as text sitemap
            urls = self._parse_text_sitemap(xml_content)
        
        return urls
    
    def _parse_text_sitemap(self, content: str) -> list[str]:
        """Parse text-format sitemap (one URL per line)."""
        urls = []
        for line in content.split('\n'):
            line = line.strip()
            if line and line.startswith('http'):
                urls.append(line)
        return urls
    
    def filter_urls(self, urls: list[str], patterns: list[str]) -> list[str]:
        """
        Filter URLs by regex patterns.
        
        Args:
            urls: List of URLs to filter
            patterns: List of regex patterns to match
            
        Returns:
            Filtered list of URLs
        """
        filtered = []
        for url in urls:
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    filtered.append(url)
                    break
        return filtered


# Common URL patterns for company scraping
COMPANY_URL_PATTERNS = {
    "about": [r"/about", r"/about-us", r"/company", r"/who-we-are"],
    "team": [r"/team", r"/leadership", r"/our-team", r"/people"],
    "contact": [r"/contact", r"/reach-us"],
    "blog": [r"/blog", r"/news", r"/insights", r"/resources"],
    "careers": [r"/careers", r"/jobs", r"/join-us", r"/work-with-us"],
    "products": [r"/products", r"/solutions", r"/services"],
}


# Module-level instance
sitemap_discovery = SitemapDiscovery()
