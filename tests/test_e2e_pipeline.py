"""Integration test — full end-to-end pipeline execution with mock LLM."""

from pathlib import Path
import json
from unittest.mock import MagicMock
import pytest

from core.config import AnalysisConfig, ReportConfig
from core.schemas import UnifiedRecord, SourceType, EnrichedRecord
from analysis.relevance_filter import RelevanceFilter
from analysis.failure_categorizer import FailureCategorizer
from analysis.memory_model_extractor import MemoryModelExtractor
from analysis.aggregator import Aggregator
from reports.evidence_library import EvidenceLibrary
from reports.report_generator import ReportGenerator


class TestEndToEndPipeline:
    def test_full_pipeline_flow(self, tmp_path):
        # 1. Simulate multi-source raw records
        raw_samples = [
            UnifiedRecord(
                source_type=SourceType.REDDIT,
                raw_text="Cannot search for Dave and Sarah at wedding, brings up all photos of Dave ever!",
                rating=1,
            ),
            UnifiedRecord(
                source_type=SourceType.GOOGLE_PLAY,
                raw_text="Where is my yellow suitcase photo in the hotel room? Search fails completely.",
                rating=2,
            ),
            UnifiedRecord(
                source_type=SourceType.APP_STORE,
                raw_text="Cannot find screenshot of refrigerator receipt warranty with OCR search.",
                rating=1,
            ),
            UnifiedRecord(
                source_type=SourceType.SUPPORT_FORUM,
                raw_text="The app keeps crashing when backing up photos to the cloud. Unrelated to search.",
                rating=1,
            ),
        ]

        cfg = AnalysisConfig()

        # Separate mocks for each stage to prevent call order collision
        mock_rel_llm = MagicMock()
        mock_rel_llm.classify.side_effect = [
            {"record_id": raw_samples[0].record_id, "is_relevant": True, "confidence": 0.95, "reason": "Conjunctive search"},
            {"record_id": raw_samples[1].record_id, "is_relevant": True, "confidence": 0.90, "reason": "Visual cue search"},
            {"record_id": raw_samples[2].record_id, "is_relevant": True, "confidence": 0.92, "reason": "OCR screenshot search"},
            {"record_id": raw_samples[3].record_id, "is_relevant": False, "confidence": 0.10, "reason": "Cloud backup issue"},
        ]

        mock_cat_llm = MagicMock()
        mock_cat_llm.classify.side_effect = [
            {"record_id": raw_samples[0].record_id, "failure_types": ["people_event"], "description": "Conjunctive search failure", "confidence": 0.9},
            {"record_id": raw_samples[1].record_id, "failure_types": ["visual_detail"], "description": "Visual detail yellow suitcase", "confidence": 0.88},
            {"record_id": raw_samples[2].record_id, "failure_types": ["document_screenshot"], "description": "OCR receipt search", "confidence": 0.91},
        ]

        mock_mem_llm = MagicMock()
        mock_mem_llm.extract.side_effect = [
            {
                "record_id": raw_samples[0].record_id,
                "remembered": {"people": ["Dave", "Sarah"], "event_context": ["wedding"]},
                "forgotten": {"exact_date": True},
                "search_attempts": {"keywords_tried": ["Dave Sarah wedding"]},
            },
            {
                "record_id": raw_samples[1].record_id,
                "remembered": {"visual_cues": ["yellow suitcase"], "location_cues": ["hotel room"]},
                "forgotten": {"exact_date": True, "file_name": True},
                "search_attempts": {"keywords_tried": ["yellow suitcase"]},
            },
            {
                "record_id": raw_samples[2].record_id,
                "remembered": {"object_cues": ["refrigerator receipt"]},
                "forgotten": {"exact_location": True},
                "search_attempts": {"keywords_tried": ["receipt", "refrigerator"]},
            },
        ]

        # 2. Stage 1: Relevance Filter
        rel_filter = RelevanceFilter(cfg, llm_client=mock_rel_llm)
        cat_engine = FailureCategorizer(cfg, llm_client=mock_cat_llm)
        mem_engine = MemoryModelExtractor(cfg, llm_client=mock_mem_llm)

        relevant_enriched = []

        for rec in raw_samples:
            rel_res = rel_filter.classify_record(rec)
            if rel_res.is_relevant:
                cat_res = cat_engine.categorize_record(rec)
                mem_res = mem_engine.extract_record(rec)

                enriched = EnrichedRecord(
                    record=rec,
                    relevance=rel_res,
                    categorization=cat_res,
                    memory_model=mem_res,
                )
                relevant_enriched.append(enriched)

        # 3 relevant, 1 discarded (backup issue)
        assert len(relevant_enriched) == 3

        # 3. Stage 4: Aggregation & Ranking
        aggregator = Aggregator(cfg)
        agg_res = aggregator.aggregate(
            relevant_enriched,
            total_collected=len(raw_samples),
            total_discarded=len(raw_samples) - len(relevant_enriched),
        )

        assert agg_res.total_records_collected == 4
        assert agg_res.total_records_relevant == 3
        assert len(agg_res.categories) >= 1

        # 4. Stage 5: Evidence Library Export
        lib = EvidenceLibrary()
        lib.build_from_records(relevant_enriched, aggregator=aggregator)
        csv_file = tmp_path / "evidence.csv"
        json_file = tmp_path / "evidence.json"
        lib.export_csv(csv_file)
        lib.export_json(json_file)
        assert csv_file.exists()
        assert json_file.exists()

        # 5. Stage 6: Report Generation
        agg_path = tmp_path / "aggregation.json"
        with open(agg_path, "w", encoding="utf-8") as f:
            f.write(agg_res.model_dump_json(indent=2))

        rep_cfg = ReportConfig(
            template_path="reports/templates/report_template.md",
            output_format="markdown",
        )
        rep_gen = ReportGenerator(rep_cfg)
        rep_out = tmp_path / "discovery_report.md"
        rep_gen.generate(aggregation_path=agg_path, output_path=rep_out)

        assert rep_out.exists()
        content = rep_out.read_text(encoding="utf-8")
        assert "Executive Summary" in content
        assert "Methodology & Data Provenance" in content
