"""Personalized Outreach Composer Agent.

Takes enriched intelligence and generates:
1. A short cold-email subject + body (max 4 sentences)
2. A LinkedIn connection request note (max 300 chars)
"""

from backend.models.schemas import (
    CompanyProfile, PersonaInference, IntentScore,
    Leadership, OutreachDraft,
)
from backend.services.llm_service import llm_json_query


async def compose_outreach(
    profile: CompanyProfile,
    persona: PersonaInference,
    intent: IntentScore,
    leadership: Leadership,
) -> OutreachDraft:
    """Generate personalized email and LinkedIn outreach based on account intelligence."""

    if not profile.company_name:
        return OutreachDraft()

    # Pick the top leader by confidence for personalization
    top_leader = None
    if leadership.leaders:
        top_leader = max(leadership.leaders, key=lambda l: l.confidence)

    leader_info = (
        f"{top_leader.name} ({top_leader.title})" if top_leader and top_leader.name
        else "the relevant decision-maker"
    )

    intent_context = (
        f"Intent Score: {intent.score}/10, Stage: {intent.stage}. Signals: {', '.join(intent.signals[:3])}"
        if intent.signals
        else "No visitor signals (direct company research mode)"
    )

    prompt = f"""You are an expert SDR (Sales Development Rep) writing highly personalized outreach.

ACCOUNT INTELLIGENCE:
- Company: {profile.company_name} | Industry: {profile.industry}
- Size: {profile.company_size} | HQ: {profile.headquarters}
- Description: {profile.description}
- Likely Contact: {leader_info}
- Visitor Persona: {persona.likely_persona} ({persona.department})
- {intent_context}

Write outreach for this specific account. Reference the company's actual situation.
DO NOT use generic templates. Be specific, concise, and value-focused.

Rules:
- Email subject: ≤ 8 words, curiosity-driven
- Email body: exactly 3-4 sentences. Start with a specific hook about their company, then pivot to value, then CTA.
- LinkedIn note: ≤ 300 characters, friendly and professional

Return JSON:
{{
    "email_subject": "...",
    "email_body": "...",
    "linkedin_note": "..."
}}"""

    result = await llm_json_query(
        prompt,
        "You are a top-performing B2B SDR. Write outreach that doesn't feel like a template. Be specific to this exact company and persona."
    )

    return OutreachDraft(
        email_subject=result.get("email_subject", ""),
        email_body=result.get("email_body", ""),
        linkedin_note=result.get("linkedin_note", ""),
    )
