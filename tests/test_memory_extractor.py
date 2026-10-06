"""Unit tests for MemoryModelExtractor."""

from unittest.mock import MagicMock
import pytest

from core.config import AnalysisConfig
from core.schemas import MemoryModel, RememberedAttributes, ForgottenAttributes, SearchAttempts, SourceType, UnifiedRecord
from analysis.memory_model_extractor import MemoryModelExtractor


@pytest.fixture
def analysis_config():
    return AnalysisConfig()


@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.extract.return_value = {
        "record_id": "test_id",
        "remembered": {
            "people": ["Dave", "Sarah"],
            "emotions": ["happy", "celebratory"],
            "temporal_cues": ["2021"],
            "location_cues": ["wedding reception"],
            "visual_cues": ["dancing", "formal clothes"],
            "event_context": ["Mark's wedding"],
            "object_cues": [],
        },
        "forgotten": {
            "exact_date": True,
            "exact_location": False,
            "album": True,
            "keywords_to_search": True,
            "file_name": True,
        },
        "search_attempts": {
            "keywords_tried": ["Dave Sarah wedding"],
            "strategies": ["text search"],
            "workarounds": ["scrolling through 2021 timeline"],
        },
    }
    return mock


class TestMemoryModelExtraction:
    def test_extracts_memory_model_correctly(self, analysis_config, mock_llm):
        mme = MemoryModelExtractor(analysis_config, llm_client=mock_llm)
        rec = UnifiedRecord(
            source_type=SourceType.REDDIT,
            raw_text="I wanted to find Dave and Sarah dancing at Mark's wedding in 2021.",
        )
        model = mme.extract_record(rec)

        assert "Dave" in model.remembered.people
        assert "2021" in model.remembered.temporal_cues
        assert model.forgotten.exact_date is True
        assert "Dave Sarah wedding" in model.search_attempts.keywords_tried
        mock_llm.extract.assert_called_once()

    def test_fallback_on_llm_failure(self, analysis_config):
        mock = MagicMock()
        mock.extract.side_effect = RuntimeError("API timeout")
        mme = MemoryModelExtractor(analysis_config, llm_client=mock)

        rec = UnifiedRecord(
            source_type=SourceType.APP_STORE,
            raw_text="Can't find pictures from summer trip.",
        )
        model = mme.extract_record(rec)

        # Should return safe baseline MemoryModel with matching record_id
        assert model.record_id == rec.record_id
        assert isinstance(model.remembered, RememberedAttributes)
