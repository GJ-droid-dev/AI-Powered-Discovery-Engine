"""Unit tests for Aggregator and EvidenceLibrary (Phase 3)."""

from pathlib import Path
import tempfile
import pytest

from core.config import AnalysisConfig
from core.schemas import (
    CategorizationResult,
    EnrichedRecord,
    ForgottenAttributes,
    MemoryModel,
    RelevanceResult,
    RememberedAttributes,
    SearchAttempts,
    SourceType,
    UnifiedRecord,
)
from analysis.aggregator import Aggregator
from reports.evidence_library import EvidenceLibrary


@pytest.fixture
def analysis_config():
    return AnalysisConfig()


@pytest.fixture
def sample_enriched_records():
    # Record 1: Severe churn + frustration in people_event
    r1 = EnrichedRecord(
        record=UnifiedRecord(
            record_id="1",
            source_type=SourceType.REDDIT,
            raw_text="I am completely frustrated! Can't find Dave and Sarah wedding photo, it sucks! I am switching to Apple Photos!",
            rating=1,
        ),
        relevance=RelevanceResult(record_id="1", is_relevant=True, confidence=0.95),
        categorization=CategorizationResult(
            record_id="1",
            failure_types=["people_event"],
            description="Failed to search for Dave and Sarah at wedding.",
            confidence=0.9,
        ),
        memory_model=MemoryModel(
            record_id="1",
            remembered=RememberedAttributes(people=["Dave", "Sarah"], event_context=["wedding"]),
            forgotten=ForgottenAttributes(exact_date=True),
            search_attempts=SearchAttempts(keywords_tried=["Dave Sarah wedding"], strategies=["text search"]),
        ),
    )

    # Record 2: Mild visual detail
    r2 = EnrichedRecord(
        record=UnifiedRecord(
            record_id="2",
            source_type=SourceType.GOOGLE_PLAY,
            raw_text="I was trying to find my yellow suitcase photo in the hotel room.",
            rating=3,
        ),
        relevance=RelevanceResult(record_id="2", is_relevant=True, confidence=0.85),
        categorization=CategorizationResult(
            record_id="2",
            failure_types=["visual_detail"],
            description="Cannot search by yellow suitcase visual cue.",
            confidence=0.88,
        ),
        memory_model=MemoryModel(
            record_id="2",
            remembered=RememberedAttributes(visual_cues=["yellow suitcase"], location_cues=["hotel room"]),
            forgotten=ForgottenAttributes(exact_date=True, file_name=True),
            search_attempts=SearchAttempts(keywords_tried=["yellow suitcase"], strategies=["search bar"]),
        ),
    )

    # Record 3: Document screenshot failure
    r3 = EnrichedRecord(
        record=UnifiedRecord(
            record_id="3",
            source_type=SourceType.APP_STORE,
            raw_text="Terrible OCR. Cannot find the receipt for my refrigerator warranty.",
            rating=2,
        ),
        relevance=RelevanceResult(record_id="3", is_relevant=True, confidence=0.9),
        categorization=CategorizationResult(
            record_id="3",
            failure_types=["document_screenshot"],
            description="OCR failed to find receipt.",
            confidence=0.92,
        ),
        memory_model=MemoryModel(
            record_id="3",
            remembered=RememberedAttributes(object_cues=["refrigerator receipt"]),
            forgotten=ForgottenAttributes(exact_date=True),
            search_attempts=SearchAttempts(keywords_tried=["receipt", "refrigerator"]),
        ),
    )

    return [r1, r2, r3]


class TestSeverityScoring:
    def test_high_frustration_and_churn_yields_high_severity(self, analysis_config, sample_enriched_records):
        agg = Aggregator(analysis_config)
        severe_record = sample_enriched_records[0]
        score = agg.calculate_severity(severe_record)
        assert score >= 0.6  # High severity due to churn keywords + frustration + 1 star

    def test_mild_complaint_yields_moderate_severity(self, analysis_config, sample_enriched_records):
        agg = Aggregator(analysis_config)
        mild_record = sample_enriched_records[1]
        score = agg.calculate_severity(mild_record)
        assert score < 0.6


class TestAggregationAndRanking:
    def test_aggregates_records_and_ranks_categories(self, analysis_config, sample_enriched_records):
        agg = Aggregator(analysis_config)
        res = agg.aggregate(sample_enriched_records, total_collected=10, total_discarded=7)

        assert res.total_records_collected == 10
        assert res.total_records_relevant == 3
        assert len(res.categories) == 3

        # Verify sorted by opportunity score descending
        scores = [c.opportunity_score for c in res.categories]
        assert scores == sorted(scores, reverse=True)

        # Check people_event category has top representative quote
        pe_cat = next(c for c in res.categories if c.category == "people_event")
        assert pe_cat.volume_count == 1
        assert len(pe_cat.representative_quotes) == 1
        assert pe_cat.remembered_frequency.get("people") == 2
        assert pe_cat.forgotten_frequency.get("exact_date") == 1


class TestEvidenceLibrary:
    def test_builds_and_searches_library(self, analysis_config, sample_enriched_records):
        agg = Aggregator(analysis_config)
        lib = EvidenceLibrary()
        lib.build_from_records(sample_enriched_records, aggregator=agg)

        assert len(lib.entries) == 3

        # Search by keyword
        matches = lib.search("Dave wedding")
        assert len(matches) >= 1
        assert matches[0]["quote_id"] == "1"

        # Search with category filter
        matches_doc = lib.search("receipt", category="document_screenshot")
        assert len(matches_doc) == 1
        assert matches_doc[0]["quote_id"] == "3"

    def test_export_json_and_csv(self, analysis_config, sample_enriched_records):
        agg = Aggregator(analysis_config)
        lib = EvidenceLibrary()
        lib.build_from_records(sample_enriched_records, aggregator=agg)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "evidence.json"
            csv_path = Path(tmpdir) / "evidence.csv"

            lib.export_json(json_path)
            lib.export_csv(csv_path)

            assert json_path.exists()
            assert csv_path.exists()
            assert json_path.stat().st_size > 0
            assert csv_path.stat().st_size > 0
