"""Unit tests for RelevanceFilter."""

from unittest.mock import MagicMock
import pytest

from core.config import AnalysisConfig
from core.schemas import RelevanceResult, SourceType, UnifiedRecord
from analysis.relevance_filter import RelevanceFilter


@pytest.fixture
def analysis_config():
    return AnalysisConfig(
        relevance_threshold=0.7,
        review_threshold=0.4,
        min_text_length=20,
    )


@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.classify.return_value = {
        "record_id": "test_id",
        "is_relevant": True,
        "confidence": 0.85,
        "reason": "Clear photo retrieval failure",
    }
    return mock


class TestKeywordPreFilter:
    def test_detects_retrieval_keywords(self, analysis_config):
        rf = RelevanceFilter(analysis_config, llm_client=MagicMock())
        assert rf.fast_keyword_check("I cannot find my old photos from vacation")
        assert rf.fast_keyword_check("Search is not working for red dress")
        assert rf.fast_keyword_check("Having to scroll through 10,000 photos is painful")
        assert rf.fast_keyword_check("Lost receipt screenshot for tax deduction")

    def test_rejects_unrelated_feedback(self, analysis_config):
        rf = RelevanceFilter(analysis_config, llm_client=MagicMock())
        assert not rf.fast_keyword_check("App crashed immediately upon launching on Android 14")
        assert not rf.fast_keyword_check("Too expensive monthly subscription fee")
        assert not rf.fast_keyword_check("Short")  # Below min_text_length


class TestThresholdLogic:
    def test_high_confidence_is_relevant(self, analysis_config):
        rf = RelevanceFilter(analysis_config, llm_client=MagicMock())
        res = RelevanceResult(record_id="1", is_relevant=True, confidence=0.85)
        assert rf.evaluate_decision(res) == "relevant"

    def test_medium_confidence_is_review(self, analysis_config):
        rf = RelevanceFilter(analysis_config, llm_client=MagicMock())
        res = RelevanceResult(record_id="2", is_relevant=True, confidence=0.55)
        assert rf.evaluate_decision(res) == "review"

    def test_low_confidence_is_discarded(self, analysis_config):
        rf = RelevanceFilter(analysis_config, llm_client=MagicMock())
        res = RelevanceResult(record_id="3", is_relevant=False, confidence=0.9)
        assert rf.evaluate_decision(res) == "discarded"


class TestFullClassification:
    def test_calls_llm_when_keyword_matches(self, analysis_config, mock_llm):
        rf = RelevanceFilter(analysis_config, llm_client=mock_llm)
        rec = UnifiedRecord(
            source_type=SourceType.REDDIT,
            raw_text="I tried searching for my dog photo by the lake but it failed completely.",
        )
        res = rf.classify_record(rec)
        assert res.is_relevant is True
        assert res.confidence == 0.85
        mock_llm.classify.assert_called_once()

    def test_skips_llm_when_keyword_absent(self, analysis_config, mock_llm):
        rf = RelevanceFilter(analysis_config, llm_client=mock_llm)
        rec = UnifiedRecord(
            source_type=SourceType.GOOGLE_PLAY,
            raw_text="App keeps crashing every single day after updating OS.",
        )
        res = rf.classify_record(rec)
        assert res.is_relevant is False
        assert res.confidence == 0.1
        mock_llm.classify.assert_not_called()
