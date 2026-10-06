"""Content-hash deduplicator.

Uses SHA-256 of normalized lowercase text to detect duplicate records.
Maintains a hash set per run and persists seen hashes to disk for
cross-run deduplication.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from core.schemas import UnifiedRecord

logger = logging.getLogger("discovery_engine")


class Deduplicator:
    """Content-hash based deduplication for collected records."""

    def __init__(self, cache_dir: Path | str | None = None):
        """Initialize the deduplicator.

        Args:
            cache_dir: Directory to persist seen hashes across runs.
                       If None, only in-memory dedup is used.
        """
        self._seen_hashes: set[str] = set()
        self._cache_file: Path | None = None
        self._new_hashes: set[str] = set()

        if cache_dir:
            self._cache_file = Path(cache_dir) / "seen_hashes.json"
            self._load_cache()

    def _load_cache(self) -> None:
        """Load previously seen hashes from disk."""
        if self._cache_file and self._cache_file.exists():
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._seen_hashes = set(data.get("hashes", []))
                logger.info(
                    f"Loaded {len(self._seen_hashes)} cached hashes",
                    extra={"stage": "deduplicator"},
                )
            except Exception as e:
                logger.warning(f"Could not load hash cache: {e}", extra={"stage": "deduplicator"})

    def save_cache(self) -> None:
        """Persist all seen hashes (old + new) to disk."""
        if self._cache_file:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                all_hashes = self._seen_hashes | self._new_hashes
                with open(self._cache_file, "w", encoding="utf-8") as f:
                    json.dump({"hashes": list(all_hashes)}, f)
                logger.info(
                    f"Saved {len(all_hashes)} hashes to cache",
                    extra={"stage": "deduplicator"},
                )
            except Exception as e:
                logger.warning(f"Could not save hash cache: {e}", extra={"stage": "deduplicator"})

    def is_duplicate(self, record: UnifiedRecord) -> bool:
        """Check if a record's content has been seen before.

        Args:
            record: The unified record to check.

        Returns:
            True if the record is a duplicate, False otherwise.
        """
        content_hash = self._compute_hash(record.raw_text)

        if content_hash in self._seen_hashes or content_hash in self._new_hashes:
            return True

        self._new_hashes.add(content_hash)
        return False

    @staticmethod
    def _compute_hash(text: str) -> str:
        """Compute SHA-256 hash of normalized text.

        Normalization: lowercase, strip whitespace, collapse multiple spaces.
        """
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @property
    def total_seen(self) -> int:
        """Total unique records seen (cached + current run)."""
        return len(self._seen_hashes | self._new_hashes)

    @property
    def new_this_run(self) -> int:
        """Records seen for the first time in this run."""
        return len(self._new_hashes)
