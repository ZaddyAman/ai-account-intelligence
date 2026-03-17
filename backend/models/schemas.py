"""Pydantic models for structured output across the entire pipeline."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── Inputs ───────────────────────────────────────────────────────────────────

class VisitorSignal(BaseModel):
    visitor_id: str
    ip_address: str
    pages_visited: list[str] = []
    time_on_site_seconds: int = 0
    visits_this_week: int = 0
    referral_source: Optional[str] = None
    device: Optional[str] = None
    location: Optional[str] = None
    timestamps: list[str] = []


class CompanyInput(BaseModel):
    company_name: str
    domain: Optional[str] = None


class BatchInput(BaseModel):
    companies: list[CompanyInput]


# ── Agent Outputs ────────────────────────────────────────────────────────────

class CompanyIdentification(BaseModel):
    company_name: str = ""
    domain: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    method: str = ""  # "ip_lookup", "direct_input", "llm_inference"


class CompanyProfile(BaseModel):
    company_name: str = ""
    domain: str = ""
    industry: str = ""
    company_size: str = ""
    headquarters: str = ""
    founding_year: Optional[str] = None
    description: str = ""
    website_url: str = ""
    email_pattern: Optional[str] = None  # e.g. 'firstname@domain.com'
    confidence: float = Field(default=0.0, ge=0, le=1)


class PersonaInference(BaseModel):
    likely_persona: str = ""
    department: str = ""
    seniority: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: str = ""


class IntentScore(BaseModel):
    score: float = Field(default=0.0, ge=0, le=10)
    stage: str = ""  # Awareness, Interest, Consideration, Evaluation, Decision
    signals: list[str] = []
    confidence: float = Field(default=0.0, ge=0, le=1)


class TechStackItem(BaseModel):
    category: str = ""  # CRM, Marketing, Analytics, CMS, etc.
    technology: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class TechStack(BaseModel):
    items: list[TechStackItem] = []
    confidence: float = Field(default=0.0, ge=0, le=1)


class BusinessSignal(BaseModel):
    signal_type: str = ""  # hiring, funding, expansion, product_launch
    description: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class BusinessSignals(BaseModel):
    signals: list[BusinessSignal] = []
    confidence: float = Field(default=0.0, ge=0, le=1)


class LeaderContact(BaseModel):
    name: str = ""
    title: str = ""
    department: str = ""
    linkedin_url: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class Leadership(BaseModel):
    leaders: list[LeaderContact] = []
    confidence: float = Field(default=0.0, ge=0, le=1)


class SalesAction(BaseModel):
    priority: str = ""  # high, medium, low
    action: str = ""
    reasoning: str = ""


# ── Master Response ──────────────────────────────────────────────────────────

class OutreachDraft(BaseModel):
    email_subject: str = ""
    email_body: str = ""
    linkedin_note: str = ""


class CompetitorInfo(BaseModel):
    name: str = ""
    domain: str = ""
    similarity: str = ""  # 'direct', 'adjacent', 'indirect'


class ICPScore(BaseModel):
    score: float = Field(default=0.0, ge=0, le=10)
    fit_level: str = ""  # 'strong', 'moderate', 'weak'
    reasoning: str = ""
    competitors: list[CompetitorInfo] = []
    confidence: float = Field(default=0.0, ge=0, le=1)


class AccountIntelligence(BaseModel):
    """Full intelligence report for a single account."""
    company_identification: CompanyIdentification = CompanyIdentification()
    company_profile: CompanyProfile = CompanyProfile()
    persona: PersonaInference = PersonaInference()
    intent: IntentScore = IntentScore()
    tech_stack: TechStack = TechStack()
    business_signals: BusinessSignals = BusinessSignals()
    leadership: Leadership = Leadership()
    icp_score: ICPScore = ICPScore()
    outreach: OutreachDraft = OutreachDraft()
    ai_summary: str = ""
    recommended_actions: list[SalesAction] = []
    overall_confidence: float = Field(default=0.0, ge=0, le=1)
    analyzed_at: Optional[str] = None
