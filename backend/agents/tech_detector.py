"""Tech Stack Detection Agent — identifies technologies from website analysis.

Uses current date awareness for accurate tech inference.
"""

import datetime
from backend.models.schemas import TechStack, TechStackItem
from backend.services.scraper_service import scrape_company_site, get_sitemap_urls


async def detect_tech_stack(company_name: str, domain: str) -> TechStack:
    """Analyze a company's website to detect their technology stack."""
    
    # Get current date for up-to-date information
    current_date = datetime.datetime.now().strftime("%B %Y")

    scraped_content = ""
    sitemap_urls = []
    
    if domain:
        # Get sitemap URLs for additional context
        sitemap_urls = await get_sitemap_urls(domain)
        
        # Scrape the website using local scraper
        scrape_result = await scrape_company_site(domain)
        
        # Use the new ScrapeResult format
        if scrape_result.success:
            scraped_content = scrape_result.markdown[:4000]

    # Import here to avoid circular imports
    from backend.services.llm_service import llm_json_query

    prompt = f"""Analyze the following company and identify their technology stack as of {current_date}.

Company: {company_name}
Domain: {domain}
Current Date: {current_date}
Sitemap URLs discovered: {len(sitemap_urls)}

{"Website Content (scraped from website):" if scraped_content else "No website content available — use your web search knowledge:"}
{scraped_content}

IMPORTANT: This is {current_date} - use current tech trends and your web search knowledge.
Consider the company's industry and age when inferring tech stack.

Identify technologies across these categories:
- CRM (e.g., Salesforce, HubSpot CRM, Pipedrive)
- Marketing Automation (e.g., HubSpot, Marketo, Mailchimp)
- Analytics (e.g., Google Analytics, Mixpanel, Amplitude)
- Website/CMS (e.g., WordPress, Webflow, Custom)
- Cloud/Hosting (e.g., AWS, GCP, Azure)
- Communication (e.g., Slack, Teams, Zoom)
- Other notable technologies

Return JSON:
{{
    "items": [
        {{"category": "CRM", "technology": "Salesforce", "confidence": 0.8}},
        ...
    ],
    "confidence": 0.0-1.0
}}"""

    result = await llm_json_query(
        prompt,
        "You are a technology analyst who specializes in identifying SaaS and technology stacks used by companies. Use current tech trends and web search knowledge."
    )

    items = []
    for item in result.get("items", []):
        items.append(TechStackItem(
            category=item.get("category", "Other"),
            technology=item.get("technology", ""),
            confidence=item.get("confidence", 0.5),
        ))

    return TechStack(
        items=items,
        confidence=result.get("confidence", 0.5),
    )
