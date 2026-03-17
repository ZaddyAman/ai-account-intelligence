"""AI Summary & Sales Action Generator — produces final intelligence report."""

from backend.models.schemas import (
    AccountIntelligence, CompanyProfile, PersonaInference, IntentScore,
    TechStack, BusinessSignals, Leadership, SalesAction,
)
from backend.services.llm_service import llm_json_query


async def generate_summary(
    profile: CompanyProfile,
    persona: PersonaInference,
    intent: IntentScore,
    tech_stack: TechStack,
    signals: BusinessSignals,
    leadership: Leadership,
) -> tuple[str, list[SalesAction]]:
    """Generate an AI intelligence summary and recommended sales actions."""

    # Build context for the LLM
    tech_list = ", ".join([f"{t.technology} ({t.category})" for t in tech_stack.items]) if tech_stack.items else "Unknown"
    signal_list = "; ".join([f"{s.signal_type}: {s.description}" for s in signals.signals]) if signals.signals else "No signals detected"
    leader_list = ", ".join([f"{l.name} - {l.title}" for l in leadership.leaders]) if leadership.leaders else "No leaders identified"

    prompt = f"""Generate an AI account intelligence summary and recommended sales actions.

COMPANY PROFILE:
- Name: {profile.company_name}
- Industry: {profile.industry}
- Size: {profile.company_size}
- HQ: {profile.headquarters}
- Description: {profile.description}

VISITOR BEHAVIOR:
- Likely Persona: {persona.likely_persona} ({persona.department})
- Intent Score: {intent.score}/10 — Stage: {intent.stage}
- Key Signals: {', '.join(intent.signals) if intent.signals else 'None'}

TECH STACK: {tech_list}

BUSINESS SIGNALS: {signal_list}

LEADERSHIP: {leader_list}

Return JSON:
{{
    "ai_summary": "A 3-4 sentence intelligence summary about this account, written for a sales rep. Include key insights and why this account matters.",
    "recommended_actions": [
        {{
            "priority": "high|medium|low",
            "action": "Specific action the sales team should take",
            "reasoning": "Why this action matters"
        }}
    ]
}}

Provide 3-5 recommended actions, ordered by priority."""

    result = await llm_json_query(
        prompt,
        "You are a senior sales strategist. Generate actionable, specific sales intelligence. Be concise and direct."
    )

    summary = result.get("ai_summary", "Unable to generate summary.")
    actions = []
    for a in result.get("recommended_actions", []):
        actions.append(SalesAction(
            priority=a.get("priority", "medium"),
            action=a.get("action", ""),
            reasoning=a.get("reasoning", ""),
        ))

    return summary, actions
