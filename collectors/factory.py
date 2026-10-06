"""Collector factory — reads sources.yaml and instantiates collectors.

Maps collector class names from config to actual collector classes.
Returns an iterator of (source_name, collector_instance) tuples.
"""

from __future__ import annotations

import logging
from typing import Iterator

from core.config import AppConfig, SourcesConfig
from collectors.base_collector import BaseCollector
from collectors.reddit import RedditCollector
from collectors.google_play import PlayStoreCollector
from collectors.app_store import AppStoreCollector
from collectors.support_forum import SupportForumCollector

logger = logging.getLogger("discovery_engine")

# Registry mapping config collector names to classes
COLLECTOR_REGISTRY: dict[str, type[BaseCollector]] = {
    "RedditCollector": RedditCollector,
    "PlayStoreCollector": PlayStoreCollector,
    "AppStoreCollector": AppStoreCollector,
    "SupportForumCollector": SupportForumCollector,
    "ForumCollector": SupportForumCollector,
}


class CollectorFactory:
    """Creates collector instances based on sources.yaml configuration."""

    def __init__(self, sources_config: SourcesConfig, app_config: AppConfig):
        self.sources_config = sources_config
        self.app_config = app_config

    def create_collectors(
        self, source_filter: list[str] | None = None
    ) -> Iterator[tuple[str, BaseCollector]]:
        """Create and yield collector instances for enabled sources.

        Args:
            source_filter: Optional list of source names to include.
                           If None, all enabled sources are used.

        Yields:
            Tuples of (source_name, collector_instance).
        """
        for name, source_params in self.sources_config.sources.items():
            # Skip disabled sources
            if not source_params.enabled:
                logger.info(f"Skipping disabled source: {name}", extra={"stage": "factory"})
                continue

            # Apply source filter if provided
            if source_filter and name not in source_filter:
                logger.info(f"Skipping filtered source: {name}", extra={"stage": "factory"})
                continue

            # Look up collector class
            collector_class_name = source_params.collector
            collector_class = COLLECTOR_REGISTRY.get(collector_class_name)

            if collector_class is None:
                logger.warning(
                    f"Unknown collector '{collector_class_name}' for source '{name}', skipping",
                    extra={"stage": "factory"},
                )
                continue

            # Instantiate
            try:
                collector = collector_class(params=source_params.params)
                logger.info(
                    f"Created {collector_class_name} for source '{name}'",
                    extra={"stage": "factory", "source_type": name},
                )
                yield name, collector
            except Exception as e:
                logger.error(
                    f"Failed to create collector for '{name}': {e}",
                    extra={"stage": "factory"},
                )
