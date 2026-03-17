"""Company Enrichment Agent — scrapes and enriches company profiles.

Uses current date awareness for accurate company information.
"""

import datetime
from backend.models.schemas import CompanyProfile
from backend.services.scraper_service import scrape_company_site, get_sitemap_urls, discover_apis


async def enrich_company(company_name: str, domain: str) -> CompanyProfile:
    """Scrape a company's website and extract structured profile data."""
    
    # Get current date for up-to-date information
    current_date = datetime.datetime.now().strftime("%B %Y")
    
    # First, discover available data sources
    sitemap_urls = []
    apis = {}
    
    if domain:
        # Get sitemap URLs for discovery
        sitemap_urls = await get_sitemap_urls(domain)
        
        # Discover APIs
        apis = await discover_apis(domain)
        
        # Scrape the website using local scraper (Playwright + BS4)
        scrape_result = await scrape_company_site(domain)
        
        # Use the new ScrapeResult format
        if scrape_result.success:
            # Limit content to avoid token overflow
            scraped_content = scrape_result.markdown[:4000]
        else:
            scraped_content = ""
    else:
        scraped_content = ""

    # Import here to avoid circular imports
    from backend.services.llm_service import llm_json_query

    prompt = f"""Analyze the following company and provide a structured company profile as of {current_date}.

Company Name: {company_name}
Domain: {domain}
Current Date: {current_date}

Available Data Sources:
- Sitemap URLs discovered: {len(sitemap_urls)}
- API endpoints found: {len(apis.get('endpoints', []))}

{"Website Content (scraped from website):" if scraped_content else "No website content available — use your web search knowledge:"}
{scraped_content}

IMPORTANT: This is {current_date} - use current information for accurate founding year, company size, etc.

Return a JSON object with these fields:
{{
    "company_name": "{company_name}",
    "domain": "{domain}",
    "industry": "specific industry category",
    "company_size": "approximate employee count range (e.g., '100-500 employees')",
    "headquarters": "city, state/country",
    "founding_year": "year or null",
    "description": "2-3 sentence business description",
    "website_url": "https://...",
    "confidence": 0.0-1.0
}}"""

    result = await llm_json_query(
        prompt,
        "You are a B2B company research analyst. Extract accurate company information using current data. If you're unsure about a field, make your best estimate and lower the confidence score."
    )

    return CompanyProfile(
        company_name=result.get("company_name", company_name),
        domain=result.get("domain", domain),
        industry=result.get("industry", ""),
        company_size=result.get("company_size", ""),
        headquarters=result.get("headquarters", ""),
        founding_year=str(result.get("founding_year")) if result.get("founding_year") else None,
        description=result.get("description", ""),
        website_url=result.get("website_url", f"https://{domain}" if domain else ""),
        confidence=result.get("confidence", 0.5),
    )
