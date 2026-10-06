"""Unit tests for the Deduplicator.

Tests:
    - Duplicate detection via content hashing
    - Normalization (case-insensitive, whitespace-collapsed)
    - Cache persistence (save/load)
    - Cross-run deduplication
"""

import json
import pytest
from pathlib import Path

from collectors.deduplicator import Deduplicator
from core.schemas import UnifiedRecord, SourceType


def _make_record(text: str) -> UnifiedRecord:
    """Helper to create a minimal UnifiedRecord for testing."""
    return UnifiedRecord(
        source_type=SourceType.REDDIT,
        raw_text=text,
    )


class TestDuplicateDetection:
    """Test basic duplicate detection."""

    def test_unique_records_not_flagged(self):
        dedup = Deduplicator()
        r1 = _make_record("I can't find my old photos from last summer")
        r2 = _make_record("Search doesn't work for vacation pictures")

        assert dedup.is_duplicate(r1) is False
        assert dedup.is_duplicate(r2) is False

    def test_exact_duplicate_flagged(self):
        dedup = Deduplicator()
        r1 = _make_record("I can't find my old photos from last summer")
        r2 = _make_record("I can't find my old photos from last summer")

        assert dedup.is_duplicate(r1) is False
        assert dedup.is_duplicate(r2) is True

    def test_case_insensitive_dedup(self):
        dedup = Deduplicator()
        r1 = _make_record("Can't find my photos")
        r2 = _make_record("CAN'T FIND MY PHOTOS")

        assert dedup.is_duplicate(r1) is False
        assert dedup.is_duplicate(r2) is True

    def test_whitespace_normalized_dedup(self):
        dedup = Deduplicator()
        r1 = _make_record("Can't find   my    photos")
        r2 = _make_record("Can't find my photos")

        assert dedup.is_duplicate(r1) is False
        assert dedup.is_duplicate(r2) is True


class TestCachePersistence:
    """Test hash cache save/load."""

    def test_save_and_load_cache(self, tmp_path):
        # First run: see some records
        dedup1 = Deduplicator(cache_dir=tmp_path)
        r1 = _make_record("First unique record for testing")
        r2 = _make_record("Second unique record for testing")

        assert dedup1.is_duplicate(r1) is False
        assert dedup1.is_duplicate(r2) is False
        dedup1.save_cache()

        # Verify cache file exists
        cache_file = tmp_path / "seen_hashes.json"
        assert cache_file.exists()

        # Second run: load cache, old records should be detected as dupes
        dedup2 = Deduplicator(cache_dir=tmp_path)
        assert dedup2.is_duplicate(r1) is True
        assert dedup2.is_duplicate(r2) is True

    def test_new_records_not_in_old_cache(self, tmp_path):
        dedup1 = Deduplicator(cache_dir=tmp_path)
        r1 = _make_record("Old record from previous run test")
        dedup1.is_duplicate(r1)
        dedup1.save_cache()

        dedup2 = Deduplicator(cache_dir=tmp_path)
        r2 = _make_record("Brand new record not seen before in testing")
        assert dedup2.is_duplicate(r2) is False


class TestMetrics:
    """Test dedup metrics."""

    def test_total_seen_count(self):
        dedup = Deduplicator()
        dedup.is_duplicate(_make_record("Record one for counting"))
        dedup.is_duplicate(_make_record("Record two for counting"))
        dedup.is_duplicate(_make_record("Record one for counting"))  # dupe

        assert dedup.total_seen == 2
        assert dedup.new_this_run == 2

    def test_empty_dedup(self):
        dedup = Deduplicator()
        assert dedup.total_seen == 0
        assert dedup.new_this_run == 0
