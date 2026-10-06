"""Pydantic schemas for all data shapes in the pipeline.

These models define the contracts between pipeline stages:
    Layer 1 (Collection)  → UnifiedRecord
    Layer 2A (Relevance)  → RelevanceResult
    Layer 2B (Categories) → CategorizationResult
    Layer 2C (Memory)     → MemoryModel
    Layer 2D (Aggregation)→ AggregationResult
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    REDDIT = "reddit"
    GOOGLE_PLAY = "google_play"
    APP_STORE = "app_store"
    SUPPORT_FORUM = "support_forum"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    OTHER = "other"


class FailureCategory(str, Enum):
    CONTEXTUAL_EPISODIC = "contextual_episodic"
    TEMPORAL_APPROXIMATION = "temporal_approximation"
    VISUAL_DETAIL = "visual_detail"
    PEOPLE_EVENT = "people_event"
    DOCUMENT_SCREENSHOT = "document_screenshot"
    OBJECT_IN_SCENE = "object_in_scene"
    EMOTIONAL_ASSOCIATION = "emotional_association"
    EMERGENT = "emergent"


# ---------------------------------------------------------------------------
# Layer 1: Collection Schemas
# ---------------------------------------------------------------------------

class ContextMetadata(BaseModel):
    """Source-specific metadata (subreddit, thread title, etc.)."""
    subreddit: str | None = None
    thread_title: str | None = None
    reply_depth: int | None = None
    parent_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class UnifiedRecord(BaseModel):
    """Normalized record schema — the contract between Layer 1 and Layer 2.

    Every record, regardless of source, conforms to this shape.
    """
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: SourceType
    source_url: str | None = None
    raw_text: str
    date: datetime | None = None
    rating: int | None = Field(None, ge=1, le=5)
    author_hash: str | None = None
    context_metadata: ContextMetadata = Field(default_factory=ContextMetadata)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Layer 2A: Relevance Filter Schemas
# ---------------------------------------------------------------------------

class RelevanceResult(BaseModel):
    """Output of the relevance filter for a single record."""
    record_id: str
    is_relevant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


# ---------------------------------------------------------------------------
# Layer 2B: Failure Categorization Schemas
# ---------------------------------------------------------------------------

class CategorizationResult(BaseModel):
    """Output of the failure categorizer for a single record."""
    record_id: str
    failure_types: list[str] = Field(default_factory=list)
    description: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


# ---------------------------------------------------------------------------
# Layer 2C: Memory Model Schemas
# ---------------------------------------------------------------------------

class RememberedAttributes(BaseModel):
    """What the user remembers about the photo."""
    people: list[str] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    temporal_cues: list[str] = Field(default_factory=list)
    location_cues: list[str] = Field(default_factory=list)
    visual_cues: list[str] = Field(default_factory=list)
    event_context: list[str] = Field(default_factory=list)
    object_cues: list[str] = Field(default_factory=list)


class ForgottenAttributes(BaseModel):
    """What the user has forgotten or cannot articulate."""
    exact_date: bool = False
    exact_location: bool = False
    album: bool = False
    keywords_to_search: bool = False
    file_name: bool = False


class SearchAttempts(BaseModel):
    """How the user attempted to find the photo."""
    keywords_tried: list[str] = Field(default_factory=list)
    strategies: list[str] = Field(default_factory=list)
    workarounds: list[str] = Field(default_factory=list)


class MemoryModel(BaseModel):
    """Full memory model extraction for a single record."""
    record_id: str
    remembered: RememberedAttributes = Field(default_factory=RememberedAttributes)
    forgotten: ForgottenAttributes = Field(default_factory=ForgottenAttributes)
    search_attempts: SearchAttempts = Field(default_factory=SearchAttempts)


# ---------------------------------------------------------------------------
# Layer 2D: Aggregation Schemas
# ---------------------------------------------------------------------------

class CategoryAggregation(BaseModel):
    """Aggregated metrics for a single failure category."""
    category: str
    volume_count: int = 0
    volume_percentage: float = 0.0
    severity_score: float = 0.0
    opportunity_score: float = 0.0
    representative_quotes: list[dict[str, str]] = Field(default_factory=list)
    remembered_frequency: dict[str, int] = Field(default_factory=dict)
    forgotten_frequency: dict[str, int] = Field(default_factory=dict)
    common_search_strategies: list[str] = Field(default_factory=list)


class AggregationResult(BaseModel):
    """Full aggregation output — the contract between Layer 2 and Layer 3."""
    total_records_collected: int = 0
    total_records_relevant: int = 0
    total_records_discarded: int = 0
    sources_analyzed: list[str] = Field(default_factory=list)
    date_range: dict[str, str] = Field(default_factory=dict)
    categories: list[CategoryAggregation] = Field(default_factory=list)
    analysis_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Enriched Record (carries all analysis through the pipeline)
# ---------------------------------------------------------------------------

class EnrichedRecord(BaseModel):
    """A fully analyzed record carrying data from all pipeline stages."""
    record: UnifiedRecord
    relevance: RelevanceResult | None = None
    categorization: CategorizationResult | None = None
    memory_model: MemoryModel | None = None
