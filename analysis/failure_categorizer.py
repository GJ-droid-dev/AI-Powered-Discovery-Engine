"""Failure categorizer — maps relevant records to retrieval failure taxonomy and discovers emergent categories via BGE embeddings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from sklearn.cluster import DBSCAN

from core.config import AnalysisConfig
from core.llm_client import LLMClient
from core.schemas import CategorizationResult, UnifiedRecord

logger = logging.getLogger("discovery_engine")


class FailureCategorizer:
    """Categorizes retrieval failures into seed taxonomy and detects emergent patterns."""

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
            else Path(__file__).parent / "prompts" / "categorization_prompt.txt"
        )
        self._system_prompt = self._load_system_prompt()
        self._embedding_model = None

    def _load_system_prompt(self) -> str:
        """Load categorization prompt instructions."""
        if self.prompt_path.exists():
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "Categorize photo retrieval feedback into failure taxonomy."

    def _get_embedding_model(self):
        """Lazily initialize BGE embedding model."""
        if self._embedding_model is None:
            from fastembed import TextEmbedding
            # BAAI/bge-small-en-v1.5 provides high quality, compact 384-d semantic vectors
            self._embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        return self._embedding_model

    def categorize_record(self, record: UnifiedRecord) -> CategorizationResult:
        """Classify a single relevant feedback record into failure categories."""
        user_prompt = (
            f"Record ID: {record.record_id}\n"
            f"Source: {record.source_type.value}\n"
            f"Rating: {record.rating or 'N/A'}\n"
            f"User Feedback:\n\"\"\"{record.raw_text}\"\"\"\n\n"
            f"Categorize this retrieval failure into the seed taxonomy."
        )

        try:
            res_dict = self.llm.classify(
                user_prompt, CategorizationResult, system_instruction=self._system_prompt
            )
            res_dict["record_id"] = record.record_id

            # Ensure failure_types is not empty
            if not res_dict.get("failure_types"):
                res_dict["failure_types"] = ["contextual_episodic"]

            return CategorizationResult.model_validate(res_dict)
        except Exception as e:
            logger.warning(
                f"LLM categorization failed for {record.record_id[:8]}: {e}. Assigning default category."
            )
            return CategorizationResult(
                record_id=record.record_id,
                failure_types=["contextual_episodic"],
                description="General photo retrieval difficulty",
                confidence=0.5,
            )

    def categorize_stream(
        self, records: Iterator[UnifiedRecord]
    ) -> Iterator[tuple[UnifiedRecord, CategorizationResult]]:
        """Process a stream of relevant records and yield (record, categorization_result)."""
        count = 0
        for record in records:
            count += 1
            cat_res = self.categorize_record(record)
            if count % 20 == 0:
                logger.info(
                    f"Categorization progress: {count} records categorized",
                    extra={"stage": "categorizer"},
                )
            yield record, cat_res

    def cluster_emergent_failures(
        self,
        records: list[UnifiedRecord],
        cat_results: list[CategorizationResult],
        min_cluster_size: int = 3,
    ) -> dict[str, Any]:
        """Use BGE embeddings and DBSCAN to cluster failure descriptions.

        Identifies emergent retrieval problems and semantic clusters beyond the seed taxonomy.

        Args:
            records: List of analyzed UnifiedRecord objects.
            cat_results: Corresponding CategorizationResult objects.
            min_cluster_size: Minimum records to form an emergent cluster.

        Returns:
            Dict containing cluster summaries, labels, and member counts.
        """
        if not records or len(records) < min_cluster_size:
            return {"clusters": [], "total_clustered": 0}

        # Collect descriptions for embedding
        descriptions = [cr.description for cr in cat_results]

        logger.info(f"Generating BGE embeddings for {len(descriptions)} failure descriptions...")
        embed_model = self._get_embedding_model()
        embeddings = list(embed_model.embed(descriptions))
        X = np.array(embeddings)

        # Normalize for cosine distance clustering
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        X_norm = X / norms

        # Cluster with DBSCAN using cosine distance
        clustering = DBSCAN(eps=0.35, min_samples=min_cluster_size, metric="cosine")
        labels = clustering.fit_predict(X)

        clusters = []
        unique_labels = set(labels)

        for label in unique_labels:
            if label == -1:
                # Noise points
                continue

            cluster_indices = [i for i, l in enumerate(labels) if l == label]
            cluster_recs = [records[i] for i in cluster_indices]
            cluster_cats = [cat_results[i] for i in cluster_indices]

            # Representative description (closest to mean centroid)
            cluster_vectors = X_norm[cluster_indices]
            centroid = np.mean(cluster_vectors, axis=0)
            dists = np.linalg.norm(cluster_vectors - centroid, axis=1)
            medoid_idx = cluster_indices[int(np.argmin(dists))]
            theme = cat_results[medoid_idx].description

            clusters.append({
                "cluster_id": int(label),
                "size": len(cluster_indices),
                "representative_theme": theme,
                "record_ids": [r.record_id for r in cluster_recs],
                "sample_quotes": [r.raw_text[:120] for r in cluster_recs[:3]],
            })

        clusters.sort(key=lambda c: c["size"], reverse=True)
        logger.info(f"Discovered {len(clusters)} semantic clusters via BGE embeddings")

        return {
            "num_clusters": len(clusters),
            "clusters": clusters,
            "noise_count": int(np.sum(labels == -1)),
        }
