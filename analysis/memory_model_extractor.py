"""Memory model extractor — decomposes user feedback into remembered vs forgotten cognitive attributes and search attempts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

from core.config import AnalysisConfig
from core.llm_client import LLMClient
from core.schemas import MemoryModel, UnifiedRecord

logger = logging.getLogger("discovery_engine")


class MemoryModelExtractor:
    """Extracts cognitive memory cues (remembered vs forgotten) from user feedback."""

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
            else Path(__file__).parent / "prompts" / "memory_extraction_prompt.txt"
        )
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load memory extraction prompt instructions."""
        if self.prompt_path.exists():
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "Extract remembered cues, forgotten attributes, and search attempts from user feedback."

    def extract_record(self, record: UnifiedRecord) -> MemoryModel:
        """Extract the mental memory model from a single feedback record."""
        user_prompt = (
            f"Record ID: {record.record_id}\n"
            f"Source: {record.source_type.value}\n"
            f"Feedback:\n\"\"\"{record.raw_text}\"\"\"\n\n"
            f"Deconstruct the user's memory model per system instructions."
        )

        try:
            res_dict = self.llm.extract(
                user_prompt, MemoryModel, system_instruction=self._system_prompt
            )
            res_dict["record_id"] = record.record_id
            return MemoryModel.model_validate(res_dict)
        except Exception as e:
            logger.warning(
                f"Memory model extraction failed for {record.record_id[:8]}: {e}. Returning baseline model."
            )
            return MemoryModel(record_id=record.record_id)

    def extract_stream(
        self, records: Iterator[UnifiedRecord]
    ) -> Iterator[tuple[UnifiedRecord, MemoryModel]]:
        """Process a stream of records and yield (record, memory_model)."""
        count = 0
        for record in records:
            count += 1
            mm = self.extract_record(record)
            if count % 20 == 0:
                logger.info(
                    f"Memory extraction progress: {count} models extracted",
                    extra={"stage": "memory_extractor"},
                )
            yield record, mm
