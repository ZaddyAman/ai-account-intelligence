"""Leadership Discovery Agent — identifies key decision makers."""

import datetime
from backend.models.schemas import Leadership, LeaderContact
from backend.services.firecrawl_service import scrape_company_about
from backend.services.llm_service import llm_json_query


async def discover_leadership(company_name: str, domain: str) -> Leadership:
    """Find key decision makers at the company."""

    # Get current date for up-to-date information
    current_date = datetime.datetime.now().strftime("%B %Y")
    
    scraped_content = ""
    if domain:
        result = await scrape_company_about(domain)
        if result.success:
            scraped_content = result.markdown[:4000]  # Increased for more content

    prompt = f"""Identify key decision makers and leadership at this company as of {current_date}.

Company: {company_name}
Domain: {domain}
Current Date: {current_date}

{"About/Team Page Content (scraped from website):" if scraped_content else "No team page content available. Use your web search knowledge:"}
{scraped_content}

IMPORTANT: This is {current_date} - use your web search knowledge to find CURRENT leadership.
If scraped content doesn't have names or is stale, search for recent information about:
- CEO/President/Founder
- CTO/VP Engineering  
- CFO
- VP of Sales / Chief Revenue Officer
- VP of Marketing
- VP of Operations
- Head of Business Development

Return JSON with real names if possible. If you truly cannot find current names, provide the TYPICAL roles that would exist at a company like this with lower confidence.
{{
    "leaders": [
        {{"name": "John Smith", "title": "CEO", "department": "Executive", "confidence": 0.8}},
        ...
    ],
    "confidence": 0.0-1.0
}}"""

    result = await llm_json_query(
        prompt,
        "You are a B2B sales intelligence researcher with access to current information. Find real current leaders. If unknown, provide likely roles with low confidence."
    )

    leaders = []
    for l in result.get("leaders", []):
        leaders.append(LeaderContact(
            name=l.get("name", ""),
            title=l.get("title", ""),
            department=l.get("department", ""),
            confidence=l.get("confidence", 0.3),
        ))

    return Leadership(
        leaders=leaders,
        confidence=result.get("confidence", 0.4),
    )
