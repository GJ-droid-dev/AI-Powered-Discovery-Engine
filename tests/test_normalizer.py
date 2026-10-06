"""Unit tests for the DataNormalizer.

Tests:
    - Schema compliance: output conforms to UnifiedRecord
    - PII stripping: emails, phones, mentions removed
    - Date parsing: Unix timestamps, ISO strings, datetime objects
    - Rating validation: 1-5 range
    - Short text rejection
"""

import pytest
from datetime import datetime, timezone

from collectors.normalizer import DataNormalizer
from core.errors import ParseError
from core.schemas import SourceType


@pytest.fixture
def normalizer():
    return DataNormalizer(min_text_length=10, use_spacy=False)


class TestSchemaCompliance:
    """Verify output conforms to UnifiedRecord schema."""

    def test_basic_record(self, normalizer):
        raw = {
            "raw_text": "I can't find my old photos from vacation last year",
            "source_url": "https://reddit.com/r/googlephotos/test",
            "date": 1692000000.0,
            "subreddit": "googlephotos",
        }
        record = normalizer.normalize(raw, "reddit")

        assert record.source_type == SourceType.REDDIT
        assert record.raw_text == raw["raw_text"]
        assert record.source_url == raw["source_url"]
        assert record.record_id  # UUID should be generated
        assert record.collected_at  # Timestamp should be set

    def test_google_play_record(self, normalizer):
        raw = {
            "raw_text": "Search doesn't work for finding old photos",
            "source_url": "https://play.google.com/...",
            "rating": 2,
            "date": datetime(2025, 8, 14, tzinfo=timezone.utc),
        }
        record = normalizer.normalize(raw, "google_play")

        assert record.source_type == SourceType.GOOGLE_PLAY
        assert record.rating == 2

    def test_context_metadata_preserved(self, normalizer):
        raw = {
            "raw_text": "I know this photo exists but can't find it anywhere",
            "subreddit": "googlephotos",
            "thread_title": "Search problems",
            "reply_depth": 2,
        }
        record = normalizer.normalize(raw, "reddit")

        assert record.context_metadata.subreddit == "googlephotos"
        assert record.context_metadata.thread_title == "Search problems"
        assert record.context_metadata.reply_depth == 2


class TestPIIStripping:
    """Verify PII is removed from text."""

    def test_email_stripped(self, normalizer):
        raw = {"raw_text": "Contact me at user@example.com for more details about the bug"}
        record = normalizer.normalize(raw, "reddit")
        assert "user@example.com" not in record.raw_text
        assert "[EMAIL]" in record.raw_text

    def test_phone_stripped(self, normalizer):
        raw = {"raw_text": "My number is +1-555-123-4567 and I need help finding photos"}
        record = normalizer.normalize(raw, "reddit")
        assert "555-123-4567" not in record.raw_text
        assert "[PHONE]" in record.raw_text

    def test_mention_stripped(self, normalizer):
        raw = {"raw_text": "Hey @username have you tried the new search in Google Photos?"}
        record = normalizer.normalize(raw, "reddit")
        assert "@username" not in record.raw_text
        assert "[USER]" in record.raw_text

    def test_url_tokens_stripped(self, normalizer):
        raw = {"raw_text": "Check this link https://example.com?token=abc123&auth=secret for the issue"}
        record = normalizer.normalize(raw, "reddit")
        assert "token=abc123" not in record.raw_text
        assert "auth=secret" not in record.raw_text

    def test_clean_text_unchanged(self, normalizer):
        text = "I can't find old vacation photos from last summer"
        raw = {"raw_text": text}
        record = normalizer.normalize(raw, "reddit")
        assert record.raw_text == text


class TestDateParsing:
    """Verify date parsing handles multiple formats."""

    def test_unix_timestamp(self, normalizer):
        raw = {"raw_text": "This is a test review for photo search", "date": 1692000000.0}
        record = normalizer.normalize(raw, "reddit")
        assert record.date is not None
        assert record.date.year == 2023

    def test_iso_string(self, normalizer):
        raw = {"raw_text": "This is a test review for photo search", "date": "2025-08-14T00:00:00Z"}
        record = normalizer.normalize(raw, "reddit")
        assert record.date is not None
        assert record.date.year == 2025
        assert record.date.month == 8

    def test_datetime_object(self, normalizer):
        dt = datetime(2024, 3, 15, tzinfo=timezone.utc)
        raw = {"raw_text": "This is a test review for photo search", "date": dt}
        record = normalizer.normalize(raw, "reddit")
        assert record.date == dt

    def test_none_date(self, normalizer):
        raw = {"raw_text": "This is a test review for photo search"}
        record = normalizer.normalize(raw, "reddit")
        assert record.date is None


class TestRatingValidation:
    """Verify rating parsing and validation."""

    def test_valid_rating(self, normalizer):
        raw = {"raw_text": "Bad search functionality in Google Photos", "rating": 2}
        record = normalizer.normalize(raw, "google_play")
        assert record.rating == 2

    def test_rating_out_of_range(self, normalizer):
        raw = {"raw_text": "Bad search functionality in Google Photos", "rating": 6}
        record = normalizer.normalize(raw, "google_play")
        assert record.rating is None

    def test_no_rating(self, normalizer):
        raw = {"raw_text": "Bad search functionality in Google Photos"}
        record = normalizer.normalize(raw, "google_play")
        assert record.rating is None


class TestEdgeCases:
    """Test error handling and edge cases."""

    def test_missing_text_raises(self, normalizer):
        with pytest.raises(ParseError):
            normalizer.normalize({}, "reddit")

    def test_empty_text_raises(self, normalizer):
        with pytest.raises(ParseError):
            normalizer.normalize({"raw_text": ""}, "reddit")

    def test_short_text_raises(self, normalizer):
        with pytest.raises(ParseError):
            normalizer.normalize({"raw_text": "too short"}, "reddit")

    def test_unknown_source_type(self, normalizer):
        raw = {"raw_text": "This is a test review for photo search purposes"}
        record = normalizer.normalize(raw, "unknown_source")
        assert record.source_type == SourceType.OTHER
