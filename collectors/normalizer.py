"""Data normalizer — maps source-specific schemas to UnifiedRecord.

Responsibilities:
    1. Convert source-specific raw dicts to the unified schema.
    2. Strip PII (emails, phone numbers via regex + spaCy NER for PERSON).
    3. Validate minimum text length.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

from core.errors import ParseError
from core.schemas import ContextMetadata, SourceType, UnifiedRecord

logger = logging.getLogger("discovery_engine")

# ---------------------------------------------------------------------------
# PII Regex Patterns
# ---------------------------------------------------------------------------
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
URL_TOKEN_PATTERN = re.compile(r"(token|key|secret|password|auth)=[^\s&]+", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"@\w+")

# Minimum text length to consider a record useful
MIN_TEXT_LENGTH = 20


class DataNormalizer:
    """Normalizes raw records from any source into UnifiedRecord."""

    def __init__(self, min_text_length: int = MIN_TEXT_LENGTH, use_spacy: bool = False):
        """Initialize the normalizer.

        Args:
            min_text_length: Minimum character count to keep a record.
            use_spacy: Whether to use spaCy NER for PII detection.
                       Set to False for speed; True for deeper PII removal.
        """
        self.min_text_length = min_text_length
        self._nlp = None
        self._use_spacy = use_spacy

    def _get_nlp(self):
        """Lazily load the spaCy model for NER-based PII stripping."""
        if self._nlp is None and self._use_spacy:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
            except Exception:
                logger.warning("spaCy model not available, skipping NER PII stripping")
                self._use_spacy = False
        return self._nlp

    def normalize(self, raw: dict[str, Any], source_type: str) -> UnifiedRecord:
        """Convert a raw source-specific dict to a UnifiedRecord.

        Args:
            raw: Source-specific dict (must contain at least 'raw_text').
            source_type: The source type string (e.g., 'reddit', 'google_play').

        Returns:
            A validated UnifiedRecord.

        Raises:
            ParseError: If the record cannot be normalized.
        """
        text = raw.get("raw_text", "")
        if not text or not isinstance(text, str):
            raise ParseError("Missing or invalid raw_text field")

        # Strip PII from text
        cleaned_text = self.strip_pii(text)

        # Check minimum length after cleaning
        if len(cleaned_text.strip()) < self.min_text_length:
            raise ParseError(
                f"Text too short after cleaning ({len(cleaned_text.strip())} chars, "
                f"min={self.min_text_length})"
            )

        # Parse date
        date = self._parse_date(raw.get("date"))

        # Map source type
        try:
            src_type = SourceType(source_type)
        except ValueError:
            src_type = SourceType.OTHER

        # Build context metadata
        context = ContextMetadata(
            subreddit=raw.get("subreddit"),
            thread_title=raw.get("thread_title"),
            reply_depth=raw.get("reply_depth"),
            extra={k: v for k, v in raw.items() if k not in {
                "raw_text", "source_url", "date", "rating",
                "author_hash", "subreddit", "thread_title", "reply_depth",
            }},
        )

        return UnifiedRecord(
            source_type=src_type,
            source_url=raw.get("source_url"),
            raw_text=cleaned_text,
            date=date,
            rating=self._parse_rating(raw.get("rating")),
            author_hash=raw.get("author_hash"),
            context_metadata=context,
        )

    def strip_pii(self, text: str) -> str:
        """Remove personally identifiable information from text.

        Steps:
            1. Regex: emails, phone numbers, URL tokens, @mentions
            2. spaCy NER: PERSON entities (if enabled)

        Args:
            text: Raw text to clean.

        Returns:
            Text with PII removed.
        """
        # Regex-based PII removal
        cleaned = EMAIL_PATTERN.sub("[EMAIL]", text)
        cleaned = PHONE_PATTERN.sub("[PHONE]", cleaned)
        cleaned = URL_TOKEN_PATTERN.sub("[REDACTED]", cleaned)
        cleaned = MENTION_PATTERN.sub("[USER]", cleaned)

        # spaCy NER-based PII removal (optional)
        if self._use_spacy:
            nlp = self._get_nlp()
            if nlp:
                doc = nlp(cleaned)
                # Replace PERSON entities with [PERSON]
                for ent in reversed(doc.ents):
                    if ent.label_ == "PERSON":
                        cleaned = cleaned[:ent.start_char] + "[PERSON]" + cleaned[ent.end_char:]

        return cleaned

    def _parse_date(self, date_val: Any) -> datetime | None:
        """Parse various date formats to datetime."""
        if date_val is None:
            return None
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, (int, float)):
            # Unix timestamp (e.g., from Reddit)
            try:
                return datetime.fromtimestamp(date_val, tz=timezone.utc)
            except (ValueError, OSError):
                return None
        if isinstance(date_val, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
            except ValueError:
                pass
        return None

    def _parse_rating(self, rating: Any) -> int | None:
        """Parse and validate a rating value (1-5)."""
        if rating is None:
            return None
        try:
            r = int(rating)
            if 1 <= r <= 5:
                return r
        except (ValueError, TypeError):
            pass
        return None
