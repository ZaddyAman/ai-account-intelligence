"""
API discovery service for finding hidden JSON endpoints.
Uses network analysis patterns to discover APIs without browser automation.
"""

import re
import httpx
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin


@dataclass
class APIEndpoint:
    """Discovered API endpoint."""
    url: str
    method: str
    params: list[str]
    response_type: str  # 'json', 'graphql', 'xml'
    auth_required: bool


@dataclass
class APIResult:
    """Result from API discovery."""
    endpoints: list[APIEndpoint]
    has_public_api: bool
    graphql_endpoint: Optional[str]
    rest_base_url: Optional[str]


class APIDiscovery:
    """Discovers hidden APIs on websites."""
    
    # Common API URL patterns
    API_PATTERNS = [
        r"/api/v\d*/.*",
        r"/api/.*",
        r"/v\d+/.*",
        r"/graphql",
        r"/graphql/v\d*",
        r"/_next/data/.*\.json",
        r"/wp-json/.*",
        r"/rest/.*",
        r"/internal/api/.*",
    ]
    
    # Known public API patterns for common platforms
    PLATFORM_API_PATTERNS = {
        "shopify": [r"/products\.json", r"/collections\.json"],
        "wordpress": [r"/wp-json/wp/v2/.*"],
        "nextjs": [r"/_next/data/.*\.json"],
        "gatsby": [r"/page-data/.*\.json"],
    }
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
        }
    
    async def discover(self, domain: str) -> APIResult:
        """
        Main entry point: discover APIs on a domain.
        
        Returns APIResult with discovered endpoints.
        """
        if not domain.startswith(("http://", "https://")):
            domain = f"https://{domain}"
        
        endpoints = []
        graphql_endpoint = None
        rest_base_url = None
        
        # Check common API locations
        api_locations = [
            "/api",
            "/api/v1",
            "/api/v2",
            "/graphql",
            "/graphql/v1",
            "/_next/data",
        ]
        
        for location in api_locations:
            url = f"{domain.rstrip('/')}{location}"
            endpoint = await self._test_endpoint(url)
            if endpoint:
                endpoints.append(endpoint)
                
                if "graphql" in location.lower():
                    graphql_endpoint = url
                elif "/api/" in location:
                    rest_base_url = url.rsplit('/', 2)[0] + "/"
        
        # Check for platform-specific APIs
        platform_apis = await self._check_platform_apis(domain)
        endpoints.extend(platform_apis)
        
        return APIResult(
            endpoints=endpoints,
            has_public_api=len(endpoints) > 0,
            graphql_endpoint=graphql_endpoint,
            rest_base_url=rest_base_url,
        )
    
    async def _test_endpoint(self, url: str) -> Optional[APIEndpoint]:
        """Test if a URL responds with JSON/API data."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                # Try GET request
                resp = await client.get(url, headers=self._headers)
                
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "")
                    
                    if "application/json" in content_type:
                        return APIEndpoint(
                            url=url,
                            method="GET",
                            params=self._extract_params(resp.text),
                            response_type="json",
                            auth_required=False,
                        )
                    
                    # Check if response looks like JSON even without proper content-type
                    if self._looks_like_json(resp.text):
                        return APIEndpoint(
                            url=url,
                            method="GET",
                            params=self._extract_params(resp.text),
                            response_type="json",
                            auth_required=False,
                        )
                        
        except Exception:
            pass
        
        return None
    
    def _looks_like_json(self, text: str) -> bool:
        """Check if text appears to be JSON."""
        text = text.strip()
        return (text.startswith('{') and text.endswith('}')) or \
               (text.startswith('[') and text.endswith(']'))
    
    def _extract_params(self, json_text: str) -> list[str]:
        """Extract parameter names from JSON response."""
        try:
            import json
            data = json.loads(json_text)
            if isinstance(data, dict):
                return list(data.keys())
        except:
            pass
        return []
    
    async def _check_platform_apis(self, domain: str) -> list[APIEndpoint]:
        """Check for platform-specific API patterns."""
        endpoints = []
        
        for platform, patterns in self.PLATFORM_API_PATTERNS.items():
            for pattern in patterns:
                url = f"{domain.rstrip('/')}{pattern}"
                endpoint = await self._test_endpoint(url)
                if endpoint:
                    endpoints.append(endpoint)
        
        return endpoints
    
    async def fetch_company_data(self, domain: str, data_type: str = "about") -> Optional[dict]:
        """
        Fetch company data via discovered API.
        
        Args:
            domain: Company domain
            data_type: Type of data to fetch ('about', 'team', 'products', etc.)
            
        Returns:
            JSON data from API or None
        """
        result = await self.discover(domain)
        
        if not result.has_public_api:
            return None
        
        # Try to fetch data based on type
        for endpoint in result.endpoints:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    # Try common endpoint patterns for the data type
                    patterns = [
                        f"{domain}/{data_type}",
                        f"{domain}/api/{data_type}",
                        f"{result.rest_base_url}{data_type}" if result.rest_base_url else None,
                    ]
                    
                    for url in patterns:
                        if url:
                            resp = await client.get(url, headers=self._headers)
                            if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
                                return resp.json()
                                
            except Exception:
                continue
        
        return None


# Module-level instance
api_discovery = APIDiscovery()
