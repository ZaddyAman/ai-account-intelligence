"""Competitor Detection & ICP Fit Agent.

Given a company profile, uses LLM to:
1. Identify 3-5 competitors in the same space
2. Score the company as an Ideal Customer Profile (ICP) fit (0-10) with reasoning
"""

from backend.models.schemas import CompanyProfile, ICPScore, CompetitorInfo
from backend.services.llm_service import llm_json_query


async def detect_competitors_and_icp(profile: CompanyProfile) -> ICPScore:
    """Identify competitors and score ICP fit for the given company profile."""

    if not profile.company_name:
        return ICPScore()

    prompt = f"""You are a B2B sales strategist analyzing whether a company is an ideal customer prospect.

COMPANY:
- Name: {profile.company_name}
- Industry: {profile.industry}
- Size: {profile.company_size}
- HQ: {profile.headquarters}
- Description: {profile.description}

Your tasks:
1. Identify 3-5 competitors or companies in the same space.
2. Score this company as an ICP (Ideal Customer Profile) fit from 0-10 where:
   - 8-10 = Strong fit (mid-market SaaS, RevOps-aware, tech-forward, 50-500 employees)
   - 5-7  = Moderate fit (some friction — size, industry, or tech maturity mismatch)
   - 0-4  = Weak fit (enterprise, non-tech, or misaligned vertical)
3. Classify similarity of each competitor as: 'direct', 'adjacent', or 'indirect'.

Return JSON:
{{
    "score": 0.0-10.0,
    "fit_level": "strong|moderate|weak",
    "reasoning": "2-3 sentence explanation of why this company is or is not a good ICP fit",
    "competitors": [
        {{"name": "Competitor Name", "domain": "competitor.com", "similarity": "direct"}},
        ...
    ],
    "confidence": 0.0-1.0
}}"""

    result = await llm_json_query(
        prompt,
        "You are a B2B sales strategist with deep knowledge of company profiles and ICP frameworks."
    )

    competitors = []
    for c in result.get("competitors", []):
        competitors.append(CompetitorInfo(
            name=c.get("name", ""),
            domain=c.get("domain", ""),
            similarity=c.get("similarity", "indirect"),
        ))

    return ICPScore(
        score=result.get("score", 0.0),
        fit_level=result.get("fit_level", ""),
        reasoning=result.get("reasoning", ""),
        competitors=competitors,
        confidence=result.get("confidence", 0.5),
    )
