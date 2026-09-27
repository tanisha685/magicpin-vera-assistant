"""
Data models and context schemas for magicpin AI Challenge (Vera).
Defines dataclasses and Pydantic models for CategoryContext, MerchantContext,
CustomerContext, TriggerContext, and HTTP payloads.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# 4-CONTEXT MODELS
# =============================================================================

class OfferTemplate(BaseModel):
    id: Optional[str] = None
    title: str
    value: Optional[str] = None
    audience: Optional[str] = "all"
    type: Optional[str] = "service_at_price"


class VoiceProfile(BaseModel):
    tone: Optional[str] = "peer_clinical"
    register: Optional[str] = "respectful_collegial"
    code_mix: Optional[str] = "hindi_english_natural"
    vocab_allowed: List[str] = Field(default_factory=list)
    vocab_taboo: List[str] = Field(default_factory=list)
    salutation_examples: List[str] = Field(default_factory=list)
    tone_examples: List[str] = Field(default_factory=list)


class PeerStats(BaseModel):
    scope: Optional[str] = None
    avg_rating: Optional[float] = 4.4
    avg_review_count: Optional[int] = 50
    avg_views_30d: Optional[int] = 2000
    avg_calls_30d: Optional[int] = 20
    avg_directions_30d: Optional[int] = 40
    avg_ctr: Optional[float] = 0.030
    retention_6mo_pct: Optional[float] = 0.40


class DigestItem(BaseModel):
    id: Optional[str] = None
    kind: Optional[str] = "research"
    title: str
    source: Optional[str] = None
    trial_n: Optional[int] = None
    patient_segment: Optional[str] = None
    summary: Optional[str] = None
    actionable: Optional[str] = None


class CategoryContext(BaseModel):
    slug: str
    display_name: Optional[str] = None
    voice: VoiceProfile = Field(default_factory=VoiceProfile)
    offer_catalog: List[OfferTemplate] = Field(default_factory=list)
    peer_stats: Optional[Dict[str, Any]] = None
    digest: List[Dict[str, Any]] = Field(default_factory=list)
    patient_content_library: List[Dict[str, Any]] = Field(default_factory=list)
    seasonal_beats: List[Dict[str, Any]] = Field(default_factory=list)
    trend_signals: List[Dict[str, Any]] = Field(default_factory=list)


class MerchantIdentity(BaseModel):
    name: str
    city: Optional[str] = "Delhi"
    locality: Optional[str] = "Central"
    place_id: Optional[str] = None
    verified: Optional[bool] = True
    languages: List[str] = Field(default_factory=lambda: ["en", "hi"])
    owner_first_name: Optional[str] = None
    established_year: Optional[int] = 2020


class Subscription(BaseModel):
    status: Optional[str] = "active"
    plan: Optional[str] = "Pro"
    days_remaining: Optional[int] = 60
    days_since_expiry: Optional[int] = None
    renewed_at: Optional[str] = None


class PerformanceSnapshot(BaseModel):
    window_days: Optional[int] = 30
    views: Optional[int] = 1000
    calls: Optional[int] = 15
    directions: Optional[int] = 30
    ctr: Optional[float] = 0.03
    leads: Optional[int] = 5
    delta_7d: Optional[Dict[str, Any]] = None


class CustomerAggregate(BaseModel):
    total_unique_ytd: Optional[int] = 500
    lapsed_180d_plus: Optional[int] = 50
    retention_6mo_pct: Optional[float] = 0.40
    high_risk_adult_count: Optional[int] = None


class MerchantContext(BaseModel):
    merchant_id: str
    category_slug: str
    identity: MerchantIdentity
    subscription: Optional[Subscription] = None
    performance: Optional[PerformanceSnapshot] = None
    offers: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    customer_aggregate: Optional[Dict[str, Any]] = None
    signals: List[str] = Field(default_factory=list)
    review_themes: List[Dict[str, Any]] = Field(default_factory=list)


class CustomerIdentity(BaseModel):
    name: str
    phone_redacted: Optional[str] = "<phone>"
    language_pref: Optional[str] = "en"
    age_band: Optional[str] = None


class CustomerRelationship(BaseModel):
    first_visit: Optional[str] = None
    last_visit: Optional[str] = None
    visits_total: Optional[int] = 1
    services_received: List[str] = Field(default_factory=list)
    lifetime_value: Optional[int] = 500
    favourite_dish: Optional[str] = None


class CustomerPreferences(BaseModel):
    preferred_slots: Optional[str] = None
    channel: Optional[str] = "whatsapp"
    reminder_opt_in: Optional[bool] = True
    wedding_date: Optional[str] = None
    training_focus: Optional[str] = None
    health_focus: Optional[str] = None
    preferred_stylist: Optional[str] = None


class CustomerContext(BaseModel):
    customer_id: str
    merchant_id: str
    identity: CustomerIdentity
    relationship: Optional[CustomerRelationship] = None
    state: Optional[str] = "active"  # "new", "active", "lapsed_soft", "lapsed_hard", "churned"
    preferences: Optional[Dict[str, Any]] = None
    consent: Optional[Dict[str, Any]] = None


class TriggerContext(BaseModel):
    id: str
    scope: Literal["merchant", "customer"]
    kind: str
    source: Literal["external", "internal"]
    merchant_id: str
    customer_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    urgency: Optional[int] = 2
    suppression_key: Optional[str] = None
    expires_at: Optional[str] = None


# =============================================================================
# HTTP API PAYLOADS & RESPONSES
# =============================================================================

class ContextPushRequest(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: Optional[str] = None


class ContextPushResponse(BaseModel):
    accepted: bool
    ack_id: Optional[str] = None
    reason: Optional[str] = None
    current_version: Optional[int] = None
    stored_at: Optional[str] = None


class TickRequest(BaseModel):
    now: str
    available_triggers: List[str] = Field(default_factory=list)


class ComposedAction(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: Literal["vera", "merchant_on_behalf"]
    trigger_id: str
    template_name: str
    template_params: List[str]
    body: str
    cta: str
    suppression_key: str
    rationale: str


class TickResponse(BaseModel):
    actions: List[ComposedAction] = Field(default_factory=list)


class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str
    message: str
    received_at: Optional[str] = None
    turn_number: int


class ReplyResponse(BaseModel):
    action: Literal["send", "wait", "end"]
    body: Optional[str] = None
    cta: Optional[str] = None
    wait_seconds: Optional[int] = None
    rationale: str


class HealthzResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: int
    contexts_loaded: Dict[str, int]


class MetadataResponse(BaseModel):
    team_name: str
    team_members: List[str]
    model: str
    approach: str
    contact_email: str
    version: str
    submitted_at: str
