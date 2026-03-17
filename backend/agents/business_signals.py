"""Business Signals Agent — identifies growth and opportunity indicators.

Now receives company description from the enricher for more grounded LLM output.
Uses current date awareness to find recent signals.
"""

import datetime
from backend.models.schemas import BusinessSignals, BusinessSignal
from backend.services.llm_service import llm_json_query


async def detect_business_signals(
    company_name: str,
    domain: str,
    company_description: str = "",
    scraped_content: str = "",
) -> BusinessSignals:
    """Identify business signals like hiring, funding, expansion for a company."""
    
    # Get current date for up-to-date information
    current_date = datetime.datetime.now().strftime("%B %Y")

    context_section = ""
    if company_description:
        context_section += f"Description: {company_description}\n"
    if scraped_content:
        context_section += f"\nWebsite Excerpt:\n{scraped_content[:2000]}\n"

    prompt = f"""Analyze the following company and identify key business signals and growth indicators as of {current_date}.

Company: {company_name}
Domain: {domain}
Current Date: {current_date}
{context_section}
IMPORTANT: This is {current_date} - focus on RECENT signals from the past 6-12 months.
Avoid historical signals older than 18 months.

Identify signals across these categories:
- hiring: Active job postings, team expansion (LAST 6 MONTHS)
- funding: Recent funding rounds, IPO activity (LAST 12 MONTHS)  
- expansion: New market entry, geographic expansion (LAST 12 MONTHS)
- product_launch: New products or features (LAST 6 MONTHS)
- partnership: Strategic partnerships or acquisitions (LAST 12 MONTHS)
- technology: Technology adoption or digital transformation (LAST 12 MONTHS)

Based on your web search knowledge of this company, identify 3-5 RECENT relevant signals.
Be specific with dates if possible. Avoid vague historical statements.

Return JSON:
{{
    "signals": [
        {{"signal_type": "hiring", "description": "Actively hiring for sales and engineering roles in 2024", "confidence": 0.7}},
        ...
    ],
    "confidence": 0.0-1.0
}}"""

    result = await llm_json_query(
        prompt,
        "You are a B2B market intelligence analyst. Focus on RECENT business signals (last 6-12 months). Be specific and avoid stale information."
    )

    signals = []
    for s in result.get("signals", []):
        signals.append(BusinessSignal(
            signal_type=s.get("signal_type", ""),
            description=s.get("description", ""),
            confidence=s.get("confidence", 0.5),
        ))

    return BusinessSignals(
        signals=signals,
        confidence=result.get("confidence", 0.5),
    )
