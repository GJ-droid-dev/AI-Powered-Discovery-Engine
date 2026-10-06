"""Apple App Store review collector.

Uses web scraping as a fallback since dedicated App Store scraper libraries
can be unreliable. Fetches reviews from the Apple RSS feed for Google Photos.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Iterator

import requests

from collectors.base_collector import BaseCollector, rate_limit, retry_with_backoff

logger = logging.getLogger("discovery_engine")


class AppStoreCollector(BaseCollector):
    """Collects Apple App Store reviews for Google Photos via RSS feed."""

    def __init__(self, params: dict[str, Any] | None = None):
        super().__init__(source_type="app_store", params=params)

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def collect(self) -> Iterator[dict[str, Any]]:
        """Fetch App Store reviews via Apple's RSS JSON feed.

        The RSS feed provides the most recent 500 reviews per country.

        Yields:
            Raw dicts with: raw_text, source_url, date, rating, author_hash
        """
        app_id = self.params.get("app_id", "962194608")
        countries = self.params.get("countries") or [self.params.get("country", "us")]
        max_reviews = self.params.get("max_reviews", 500)
        filter_keywords = self.params.get("filter_keywords", [])

        count = 0

        for country in countries:
            if count >= max_reviews:
                break

            # Apple provides up to 10 pages of 50 reviews each via RSS
            for page in range(1, 11):
                if count >= max_reviews:
                    break

                url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/json"

                try:
                    resp = requests.get(url, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"App Store RSS ({country}) page {page} failed: {e}", extra={"stage": "collector"})
                    break

                entries = data.get("feed", {}).get("entry", [])
                if not entries:
                    break

            for entry in entries:
                if count >= max_reviews:
                    break

                # The first entry is often the app metadata, skip it
                content = entry.get("content", {})
                if isinstance(content, dict):
                    text = content.get("label", "")
                else:
                    continue

                if not text:
                    continue

                # Keyword pre-filter
                if filter_keywords:
                    text_lower = text.lower()
                    if not any(kw.lower() in text_lower for kw in filter_keywords):
                        continue

                # Extract rating
                rating_data = entry.get("im:rating", {})
                rating = None
                if isinstance(rating_data, dict):
                    try:
                        rating = int(rating_data.get("label", 0))
                    except (ValueError, TypeError):
                        pass

                # Extract date
                date_str = entry.get("updated", {}).get("label", "")
                date = None
                if date_str:
                    try:
                        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                # Extract author
                author_name = entry.get("author", {}).get("name", {}).get("label", "unknown")

                count += 1
                self._log_progress(count, "app_store")

                yield {
                    "raw_text": text,
                    "source_url": f"https://apps.apple.com/{country}/app/google-photos/id{app_id}",
                    "date": date,
                    "rating": rating,
                    "author_hash": hashlib.sha256(
                        author_name.encode()
                    ).hexdigest()[:16],
                    "title": entry.get("title", {}).get("label", ""),
                }

        logger.info(
            f"App Store collection complete: {count} records",
            extra={"stage": "collector", "source_type": "app_store"},
        )
