"""Master Orchestrator — chains all agents into a complete intelligence pipeline.

Improvements:
- Per-agent failure isolation via return_exceptions=True
- Weighted confidence (identification + profile weighted higher than persona/intent)
- Threads scraped content into business_signals to reduce hallucination
- Threads timestamps into intent_scorer for recency decay
- Adds analyzed_at timestamp to the result
"""

import asyncio
import datetime
from backend.models.schemas import (
    VisitorSignal, CompanyInput, AccountIntelligence, CompanyIdentification,
    CompanyProfile, PersonaInference, IntentScore, TechStack,
    BusinessSignals, Leadership, ICPScore, OutreachDraft,
)
from backend.agents.company_identifier import (
    identify_company_from_ip, identify_company_from_name,
)
from backend.agents.company_enricher import enrich_company
from backend.agents.tech_detector import detect_tech_stack
from backend.agents.business_signals import detect_business_signals
from backend.agents.leadership import discover_leadership
from backend.agents.persona_inferrer import infer_persona
from backend.agents.intent_scorer import score_intent
from backend.agents.summary_generator import generate_summary
from backend.agents.competitor_detector import detect_competitors_and_icp
from backend.agents.outreach_composer import compose_outreach


# Weights used for the final confidence calculation
_CONFIDENCE_WEIGHTS = {
    "company_id":  0.25,
    "profile":     0.20,
    "tech_stack":  0.10,
    "signals":     0.10,
    "leadership":  0.10,
    "persona":     0.15,
    "intent":      0.10,
}


def _safe(result, default):
    """Return result or default if the task threw an exception."""
    if isinstance(result, BaseException):
        print(f"[AGENT ERROR] {type(result).__name__}: {result}")
        return default
    return result


def _weighted_confidence(
    company_id, profile, tech_stack, signals, leadership, persona, intent
) -> float:
    values = {
        "company_id":  company_id.confidence,
        "profile":     profile.confidence,
        "tech_stack":  tech_stack.confidence,
        "signals":     signals.confidence,
        "leadership":  leadership.confidence,
        "persona":     persona.confidence,
        "intent":      intent.confidence,
    }
    return round(
        sum(_CONFIDENCE_WEIGHTS[k] * v for k, v in values.items()), 2
    )


async def analyze_visitor(visitor: VisitorSignal) -> AccountIntelligence:
    """Full pipeline: visitor signal → complete account intelligence."""

    # Step 1: Identify company from IP (everything else depends on this)
    company_id = await identify_company_from_ip(visitor.ip_address)

    # Step 2: Run all enrichment + visitor-behaviour agents in parallel
    results = await asyncio.gather(
        infer_persona(visitor.pages_visited),
        score_intent(
            pages_visited=visitor.pages_visited,
            time_on_site_seconds=visitor.time_on_site_seconds,
            visits_this_week=visitor.visits_this_week,
            referral_source=visitor.referral_source or "",
            timestamps=visitor.timestamps,
        ),
        enrich_company(company_id.company_name, company_id.domain),
        detect_tech_stack(company_id.company_name, company_id.domain),
        detect_business_signals(company_id.company_name, company_id.domain),
        discover_leadership(company_id.company_name, company_id.domain),
        return_exceptions=True,
    )

    persona   = _safe(results[0], PersonaInference())
    intent    = _safe(results[1], IntentScore())
    profile   = _safe(results[2], CompanyProfile())
    tech_stack = _safe(results[3], TechStack())
    signals   = _safe(results[4], BusinessSignals())
    leadership = _safe(results[5], Leadership())

    # Re-run business_signals with description now that enrichment is done
    if profile.description:
        try:
            signals = await detect_business_signals(
                company_id.company_name,
                company_id.domain,
                company_description=profile.description,
            )
        except Exception as e:
            print(f"[AGENT ERROR] business_signals retry: {e}")

    # Step 3: Summary + ICP + Outreach (parallel, depend on all step-2 data)
    step3 = await asyncio.gather(
        generate_summary(profile, persona, intent, tech_stack, signals, leadership),
        detect_competitors_and_icp(profile),
        compose_outreach(profile, persona, intent, leadership),
        return_exceptions=True,
    )

    summary_result = _safe(step3[0], ("Unable to generate summary.", []))
    icp_score      = _safe(step3[1], ICPScore())
    outreach       = _safe(step3[2], OutreachDraft())

    ai_summary, actions = summary_result

    overall_confidence = _weighted_confidence(
        company_id, profile, tech_stack, signals, leadership, persona, intent
    )

    return AccountIntelligence(
        company_identification=company_id,
        company_profile=profile,
        persona=persona,
        intent=intent,
        tech_stack=tech_stack,
        business_signals=signals,
        leadership=leadership,
        icp_score=icp_score,
        outreach=outreach,
        ai_summary=ai_summary,
        recommended_actions=actions,
        overall_confidence=overall_confidence,
        analyzed_at=datetime.datetime.utcnow().isoformat() + "Z",
    )


async def analyze_company(company: CompanyInput) -> AccountIntelligence:
    """Full pipeline: company name → complete account intelligence."""

    # Step 1: Resolve company identity
    company_id = await identify_company_from_name(
        company.company_name, company.domain or ""
    )

    # Step 2: All enrichment agents in parallel
    results = await asyncio.gather(
        enrich_company(company_id.company_name, company_id.domain),
        detect_tech_stack(company_id.company_name, company_id.domain),
        detect_business_signals(company_id.company_name, company_id.domain),
        discover_leadership(company_id.company_name, company_id.domain),
        return_exceptions=True,
    )

    profile    = _safe(results[0], CompanyProfile())
    tech_stack = _safe(results[1], TechStack())
    signals    = _safe(results[2], BusinessSignals())
    leadership = _safe(results[3], Leadership())

    # Re-run business_signals with description context
    if profile.description:
        try:
            signals = await detect_business_signals(
                company_id.company_name,
                company_id.domain,
                company_description=profile.description,
            )
        except Exception as e:
            print(f"[AGENT ERROR] business_signals retry: {e}")

    # No visitor data — provide neutral defaults
    persona = PersonaInference(
        likely_persona="Unknown — no visitor behavior data",
        department="N/A",
        seniority="N/A",
        confidence=0.0,
        reasoning="Company was provided directly, not through visitor tracking.",
    )
    intent = IntentScore(
        score=0.0,
        stage="N/A — Direct Input",
        signals=["Company provided via direct input (no visitor signals)"],
        confidence=0.0,
    )

    # Step 3: Summary + ICP + Outreach
    step3 = await asyncio.gather(
        generate_summary(profile, persona, intent, tech_stack, signals, leadership),
        detect_competitors_and_icp(profile),
        compose_outreach(profile, persona, intent, leadership),
        return_exceptions=True,
    )

    summary_result = _safe(step3[0], ("Unable to generate summary.", []))
    icp_score      = _safe(step3[1], ICPScore())
    outreach       = _safe(step3[2], OutreachDraft())

    ai_summary, actions = summary_result

    confidences = [
        company_id.confidence, profile.confidence,
        tech_stack.confidence, signals.confidence, leadership.confidence,
    ]
    overall_confidence = round(sum(confidences) / len(confidences), 2)

    return AccountIntelligence(
        company_identification=company_id,
        company_profile=profile,
        persona=persona,
        intent=intent,
        tech_stack=tech_stack,
        business_signals=signals,
        leadership=leadership,
        icp_score=icp_score,
        outreach=outreach,
        ai_summary=ai_summary,
        recommended_actions=actions,
        overall_confidence=overall_confidence,
        analyzed_at=datetime.datetime.utcnow().isoformat() + "Z",
    )


async def analyze_batch(companies: list[CompanyInput]) -> list[AccountIntelligence]:
    """Process multiple companies in parallel."""
    tasks = [analyze_company(c) for c in companies]
    return await asyncio.gather(*tasks)
