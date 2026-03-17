"""Intent Scoring Agent — scores buying intent from visitor behavior.

Improvements:
- Timestamp recency decay: older visits contribute less weight
- Expanded referral source list (G2, Trustradius, etc.)
"""

import math
import datetime
from backend.models.schemas import IntentScore


# Weighted scoring rules
PAGE_WEIGHTS = {
    "/pricing": 3.0,
    "/demo-request": 4.0,
    "/contact-sales": 4.0,
    "/case-studies": 2.0,
    "/ai-sales-agent": 2.0,
    "/features": 1.5,
    "/integrations": 1.5,
    "/security": 1.5,
    "/docs/api": 1.0,
    "/docs/webhooks": 1.0,
    "/docs/sdk": 1.0,
    "/blog": 0.3,
    "/resources": 0.5,
    "/about": 0.2,
    "/careers": -1.0,  # Negative — likely a job seeker
    "/changelog": 0.5,
}

STAGE_THRESHOLDS = [
    (8.0, "Decision"),
    (6.0, "Evaluation"),
    (4.0, "Consideration"),
    (2.0, "Interest"),
    (0.0, "Awareness"),
]

# High-intent paid / review-site referrals
HIGH_INTENT_SOURCES = {
    "google-ads", "bing-ads", "linkedin-ad", "facebook-ad",
    "capterra", "g2", "trustradius", "product-hunt", "typeform",
    "getapp", "software-advice",
}


def _recency_weight(timestamp_str: str) -> float:
    """Return a decay multiplier (0.3 – 1.0) based on how recent a visit was.

    Visits within 24 h → 1.0, decaying exponentially towards 0.3 at 30 days.
    """
    try:
        visit_time = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        age_hours = max(0, (now - visit_time).total_seconds() / 3600)
        # Half-life of 72 h, floor at 0.3
        decay = math.exp(-age_hours / 72)
        return max(0.3, decay)
    except Exception:
        return 1.0  # No timestamp → treat as fresh


async def score_intent(
    pages_visited: list[str],
    time_on_site_seconds: int = 0,
    visits_this_week: int = 0,
    referral_source: str = "",
    timestamps: list[str] | None = None,
) -> IntentScore:
    """Calculate a 0-10 intent score based on visitor behavior signals."""

    signals = []
    raw_score = 0.0
    timestamps = timestamps or []

    # 1. Page visit scoring (with optional recency decay)
    for idx, page in enumerate(pages_visited):
        ts_weight = _recency_weight(timestamps[idx]) if idx < len(timestamps) else 1.0
        for pattern, weight in PAGE_WEIGHTS.items():
            if pattern in page:
                raw_score += weight * ts_weight
                if weight >= 2.0:
                    signals.append(f"Visited {page} (high-intent page)")
                break

    # 2. Repeat visit bonus
    if visits_this_week >= 5:
        raw_score += 3.0
        signals.append(f"Heavy repeat visitor ({visits_this_week} visits this week)")
    elif visits_this_week >= 3:
        raw_score += 2.0
        signals.append(f"Returning visitor ({visits_this_week} visits this week)")
    elif visits_this_week >= 2:
        raw_score += 1.0
        signals.append(f"Repeat visitor ({visits_this_week} visits this week)")

    # 3. Dwell time bonus
    if time_on_site_seconds >= 300:
        raw_score += 2.0
        signals.append(f"Long session ({time_on_site_seconds // 60}m {time_on_site_seconds % 60}s)")
    elif time_on_site_seconds >= 120:
        raw_score += 1.0
        signals.append(f"Engaged session ({time_on_site_seconds // 60}m {time_on_site_seconds % 60}s)")

    # 4. Referral source bonus
    if referral_source.lower() in HIGH_INTENT_SOURCES:
        raw_score += 1.0
        signals.append(f"Paid/review-site referral ({referral_source})")

    # 5. Multiple high-intent pages bonus
    high_intent_pages = [
        p for p in pages_visited
        if any(h in p for h in ["/pricing", "/demo", "/contact-sales", "/case-studies"])
    ]
    if len(high_intent_pages) >= 3:
        raw_score += 1.5
        signals.append(f"Multiple high-intent pages visited ({len(high_intent_pages)})")

    # Normalize to 0-10 scale (cap at 0 and 10)
    final_score = round(max(0.0, min(raw_score, 10.0)), 1)

    # Determine stage
    stage = "Awareness"
    for threshold, stage_name in STAGE_THRESHOLDS:
        if final_score >= threshold:
            stage = stage_name
            break

    # Confidence based on signal count
    confidence = min(len(signals) / 5.0, 1.0)

    return IntentScore(
        score=final_score,
        stage=stage,
        signals=signals,
        confidence=round(confidence, 2),
    )
