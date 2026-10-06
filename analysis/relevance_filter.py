"""Two-pass relevance filter combining regex keyword pre-filtering with Gemini 3.8 Flash."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterator

from core.config import AnalysisConfig
from core.llm_client import LLMClient
from core.schemas import RelevanceResult, UnifiedRecord

logger = logging.getLogger("discovery_engine")

# ---------------------------------------------------------------------------
# Pre-filter keywords: regex patterns targeting memory retrieval issues
# ---------------------------------------------------------------------------
RETRIEVAL_KEYWORD_PATTERNS = [
    r"\b(find|finding|found|locate|locating|located)\b",
    r"\b(search|searching|searched)\b",
    r"\b(retrieve|retrieving|retrieval)\b",
    r"\b(lost|missing|disappeared|disappear|vanished)\b",
    r"\b(can'?t\s+see|cannot\s+see|can'?t\s+find|cannot\s+find)\b",
    r"\b(looking\s+for|look\s+for|looked\s+for)\b",
    r"\b(scroll|scrolling|scrolled)\b",
    r"\b(browse|browsing)\b",
    r"\b(remember|remembered|remembering|recall|recollect)\b",
    r"\b(memory|memories)\b",
    r"\b(where\s+is|where\s+are|where\s+did)\b",
    r"\b(old\s+photo|old\s+picture|old\s+pic|childhood)\b",
    r"\b(face|faces|tag|tagged|tagging|naming)\b",
    r"\b(album|albums|timeline)\b",
    r"\b(date|month|year|timestamp)\b",
    r"\b(receipt|receipts|warranty|serial\s+number)\b",
    r"\b(screenshot|screenshots|document|documents)\b",
    r"\b(whiteboard|notes|license\s+plate|odometer)\b",
    r"\b(outfit|wearing|dress|jacket|shirt)\b",
    r"\b(background|scene|setting)\b",
    r"\b(co-?occurrence|both\s+of\s+them)\b",
]

COMPILED_KEYWORD_REGEX = re.compile("|".join(RETRIEVAL_KEYWORD_PATTERNS), re.IGNORECASE)


class RelevanceFilter:
    """Two-pass relevance filter: keyword pre-filter + Gemini Flash classification."""

    def __init__(
        self,
        config: AnalysisConfig,
        llm_client: LLMClient | None = None,
        prompt_path: Path | str | None = None,
    ):
        self.config = config
        self.llm = llm_client or LLMClient()
        self.prompt_path = (
            Path(prompt_path)
            if prompt_path
            else Path(__file__).parent / "prompts" / "relevance_prompt.txt"
        )
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load relevance prompt instructions."""
        if self.prompt_path.exists():
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "You are an expert evaluating whether user feedback is about photo retrieval failure."

    def fast_keyword_check(self, text: str) -> bool:
        """Pass 1: Fast regex keyword check."""
        if len(text.strip()) < self.config.min_text_length:
            return False
        return bool(COMPILED_KEYWORD_REGEX.search(text))

    def classify_record(self, record: UnifiedRecord) -> RelevanceResult:
        """Classify a single UnifiedRecord using the two-pass pipeline.

        Pass 1: Keyword pre-filter. If no keywords match, discard early.
        Pass 2: LLM classification for nuanced contextual analysis.
        """
        text = record.raw_text

        # Pass 1: Keyword check
        if not self.fast_keyword_check(text):
            return RelevanceResult(
                record_id=record.record_id,
                is_relevant=False,
                confidence=0.1,
                reason="Pass 1: No retrieval keywords or text below minimum length",
            )

        # Pass 2: LLM classification
        user_prompt = (
            f"Record ID: {record.record_id}\n"
            f"Source: {record.source_type.value}\n"
            f"Rating: {record.rating or 'N/A'}\n"
            f"User Feedback:\n\"\"\"{text}\"\"\"\n\n"
            f"Evaluate relevance per system instructions."
        )

        try:
            res_dict = self.llm.classify(
                user_prompt, RelevanceResult, system_instruction=self._system_prompt
            )
            # Ensure correct record_id is preserved
            res_dict["record_id"] = record.record_id
            return RelevanceResult.model_validate(res_dict)
        except Exception as e:
            logger.warning(
                f"LLM relevance classification failed for record {record.record_id[:8]}: {e}. Discarding as safe default."
            )
            return RelevanceResult(
                record_id=record.record_id,
                is_relevant=False,
                confidence=0.0,
                reason=f"LLM classification error: {e}",
            )

    def evaluate_decision(self, result: RelevanceResult) -> str:
        """Determine decision bucket based on configured thresholds.

        Returns:
            'relevant', 'review', or 'discarded'
        """
        if result.is_relevant:
            if result.confidence >= self.config.relevance_threshold:
                return "relevant"
            elif result.confidence >= self.config.review_threshold:
                return "review"
            else:
                return "discarded"
        else:
            # If model says not relevant, only review if confidence is low (< 0.6)
            if result.confidence < 0.6:
                return "review"
            return "discarded"

    def filter_records(
        self, records: Iterator[UnifiedRecord]
    ) -> Iterator[tuple[UnifiedRecord, RelevanceResult, str]]:
        """Filter a stream of records and yield (record, result, decision)."""
        count = 0
        relevant_count = 0

        for record in records:
            count += 1
            result = self.classify_record(record)
            decision = self.evaluate_decision(result)
            if decision == "relevant":
                relevant_count += 1

            if count % 25 == 0:
                logger.info(
                    f"Relevance filter progress: {count} evaluated, {relevant_count} relevant",
                    extra={"stage": "relevance_filter"},
                )

            yield record, result, decision
