"""Persona Inference Agent — infers visitor role from browsing behavior."""

from backend.models.schemas import PersonaInference


# Page-to-persona mapping rules
PAGE_SIGNALS = {
    "/pricing": {"persona": "Buyer / Decision Maker", "department": "Operations", "seniority": "Senior", "weight": 3},
    "/demo-request": {"persona": "Buyer / Decision Maker", "department": "Operations", "seniority": "Senior", "weight": 4},
    "/contact-sales": {"persona": "Buyer / Decision Maker", "department": "Sales", "seniority": "Senior", "weight": 4},
    "/case-studies": {"persona": "Business Evaluator", "department": "Operations", "seniority": "Mid-Senior", "weight": 2.5},
    "/ai-sales-agent": {"persona": "Sales Leader", "department": "Sales", "seniority": "Senior", "weight": 2},
    "/features": {"persona": "Product Evaluator", "department": "Product", "seniority": "Mid", "weight": 1.5},
    "/integrations": {"persona": "Technical Evaluator", "department": "Engineering", "seniority": "Mid", "weight": 2},
    "/docs/api": {"persona": "Developer / Technical Lead", "department": "Engineering", "seniority": "Mid", "weight": 2},
    "/docs/webhooks": {"persona": "Developer / Technical Lead", "department": "Engineering", "seniority": "Mid", "weight": 2},
    "/docs/sdk": {"persona": "Developer / Technical Lead", "department": "Engineering", "seniority": "Mid", "weight": 2},
    "/security": {"persona": "IT / Compliance Decision Maker", "department": "IT", "seniority": "Senior", "weight": 2},
    "/blog": {"persona": "Researcher / Analyst", "department": "Marketing", "seniority": "Junior-Mid", "weight": 0.5},
    "/resources": {"persona": "Researcher / Analyst", "department": "Marketing", "seniority": "Junior-Mid", "weight": 0.5},
    "/about": {"persona": "General Visitor", "department": "Unknown", "seniority": "Unknown", "weight": 0.3},
    "/careers": {"persona": "Job Seeker", "department": "N/A", "seniority": "N/A", "weight": 0},
    "/changelog": {"persona": "Developer / Current User", "department": "Engineering", "seniority": "Mid", "weight": 1},
}


async def infer_persona(pages_visited: list[str]) -> PersonaInference:
    """Infer the likely persona from the pages visited."""
    if not pages_visited:
        return PersonaInference(
            likely_persona="Unknown Visitor",
            department="Unknown",
            seniority="Unknown",
            confidence=0.0,
            reasoning="No page visit data available.",
        )

    # Score each persona category
    scores: dict[str, float] = {}
    matched_signals = []

    for page in pages_visited:
        # Match exact or partial paths
        best_match = None
        best_len = 0
        for pattern, signal in PAGE_SIGNALS.items():
            if pattern in page and len(pattern) > best_len:
                best_match = signal
                best_len = len(pattern)

        if best_match:
            persona = best_match["persona"]
            scores[persona] = scores.get(persona, 0) + best_match["weight"]
            matched_signals.append(f"{page} → {persona}")

    if not scores:
        return PersonaInference(
            likely_persona="Unknown Visitor",
            department="Unknown",
            seniority="Unknown",
            confidence=0.2,
            reasoning=f"Visited pages: {', '.join(pages_visited)} — no strong persona signals.",
        )

    # Pick the highest-scored persona
    top_persona = max(scores, key=scores.get)  # type: ignore
    top_score = scores[top_persona]

    # Find the matching signal details for the top persona
    for signal in PAGE_SIGNALS.values():
        if signal["persona"] == top_persona:
            department = signal["department"]
            seniority = signal["seniority"]
            break
    else:
        department = "Unknown"
        seniority = "Unknown"

    # Calculate confidence (normalize score to 0-1 range)
    confidence = min(top_score / 10.0, 1.0)

    # Map to specific titles
    title_map = {
        "Buyer / Decision Maker": "VP of Operations or Head of Sales",
        "Sales Leader": "Head of Sales Operations",
        "Technical Evaluator": "Engineering Manager or Solutions Architect",
        "Developer / Technical Lead": "Senior Developer or CTO",
        "Business Evaluator": "Director of Business Development",
        "Product Evaluator": "Product Manager",
        "IT / Compliance Decision Maker": "IT Director or CISO",
        "Researcher / Analyst": "Marketing Analyst or Content Strategist",
        "Developer / Current User": "Software Engineer",
    }

    likely_title = title_map.get(top_persona, top_persona)
    reasoning = f"Based on page visits: {'; '.join(matched_signals)}"

    return PersonaInference(
        likely_persona=likely_title,
        department=department,
        seniority=seniority,
        confidence=round(confidence, 2),
        reasoning=reasoning,
    )
