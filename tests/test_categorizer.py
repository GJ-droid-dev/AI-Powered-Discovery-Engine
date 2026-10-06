"""Unit tests for FailureCategorizer."""

from unittest.mock import MagicMock
import pytest

from core.config import AnalysisConfig
from core.schemas import CategorizationResult, SourceType, UnifiedRecord
from analysis.failure_categorizer import FailureCategorizer


@pytest.fixture
def analysis_config():
    return AnalysisConfig()


@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.classify.return_value = {
        "record_id": "test_id",
        "failure_types": ["visual_detail", "contextual_episodic"],
        "description": "User searched for a yellow suitcase in a hotel room but got generic results.",
        "confidence": 0.90,
    }
    return mock


class TestFailureCategorization:
    def test_categorizes_record_with_mock_llm(self, analysis_config, mock_llm):
        fc = FailureCategorizer(analysis_config, llm_client=mock_llm)
        rec = UnifiedRecord(
            source_type=SourceType.REDDIT,
            raw_text="I took a photo of my yellow suitcase in a hotel room and search failed.",
        )
        res = fc.categorize_record(rec)
        assert "visual_detail" in res.failure_types
        assert res.confidence == 0.90
        assert "yellow suitcase" in res.description
        mock_llm.classify.assert_called_once()

    def test_handles_empty_failure_types_gracefully(self, analysis_config):
        mock = MagicMock()
        mock.classify.return_value = {
            "record_id": "test_id",
            "failure_types": [],
            "description": "Unspecified retrieval issue",
            "confidence": 0.5,
        }
        fc = FailureCategorizer(analysis_config, llm_client=mock)
        rec = UnifiedRecord(source_type=SourceType.GOOGLE_PLAY, raw_text="Can't find old photo.")
        res = fc.categorize_record(rec)
        assert len(res.failure_types) > 0  # Falls back to default category


class TestEmergentClustering:
    def test_clusters_similar_descriptions(self, analysis_config):
        fc = FailureCategorizer(analysis_config, llm_client=MagicMock())
        records = [
            UnifiedRecord(source_type=SourceType.REDDIT, raw_text=f"Sample feedback text {i} for clustering verification")
            for i in range(6)
        ]
        cat_results = [
            CategorizationResult(
                record_id=records[0].record_id,
                description="Unable to find receipt photo for appliance warranty",
            ),
            CategorizationResult(
                record_id=records[1].record_id,
                description="Receipt search failed for Home Depot purchase",
            ),
            CategorizationResult(
                record_id=records[2].record_id,
                description="Lost store receipt for tax return deduction",
            ),
            CategorizationResult(
                record_id=records[3].record_id,
                description="Search for sunset at beach failed",
            ),
            CategorizationResult(
                record_id=records[4].record_id,
                description="Beach sunset pictures not showing up in search",
            ),
            CategorizationResult(
                record_id=records[5].record_id,
                description="Evening sunset photos by the ocean disappeared",
            ),
        ]

        cluster_info = fc.cluster_emergent_failures(records, cat_results, min_cluster_size=2)
        assert "num_clusters" in cluster_info
        assert cluster_info["num_clusters"] >= 1
