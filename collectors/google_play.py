"""Google Play Store review collector.

Uses the google-play-scraper library to fetch reviews for the Google Photos app.
Applies keyword pre-filtering at collection time to reduce noise.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Iterator

from collectors.base_collector import BaseCollector, rate_limit, retry_with_backoff

logger = logging.getLogger("discovery_engine")


class PlayStoreCollector(BaseCollector):
    """Collects Google Play Store reviews for Google Photos."""

    def __init__(self, params: dict[str, Any] | None = None):
        super().__init__(source_type="google_play", params=params)

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def collect(self) -> Iterator[dict[str, Any]]:
        """Fetch and filter Google Play reviews.

        Yields:
            Raw dicts with: raw_text, source_url, date, rating, author_hash
        """
        from google_play_scraper import Sort, reviews

        app_id = self.params.get("app_id", "com.google.android.apps.photos")
        max_reviews = self.params.get("max_reviews", 1000)
        filter_keywords = self.params.get("filter_keywords", [])

        # google-play-scraper returns reviews in batches
        # We'll collect up to max_reviews
        result, continuation_token = reviews(
            app_id,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=min(max_reviews, 200),  # API batch size
        )

        all_reviews = list(result)

        # Continue fetching if we need more
        while continuation_token and len(all_reviews) < max_reviews:
            result, continuation_token = reviews(
                app_id,
                lang="en",
                country="us",
                sort=Sort.NEWEST,
                count=min(max_reviews - len(all_reviews), 200),
                continuation_token=continuation_token,
            )
            all_reviews.extend(result)

        count = 0
        for review in all_reviews:
            text = review.get("content", "")
            if not text:
                continue

            # Keyword pre-filter: only yield reviews mentioning retrieval-related terms
            if filter_keywords:
                text_lower = text.lower()
                if not any(kw.lower() in text_lower for kw in filter_keywords):
                    continue

            count += 1
            self._log_progress(count, "google_play")

            yield {
                "raw_text": text,
                "source_url": f"https://play.google.com/store/apps/details?id={app_id}&reviewId={review.get('reviewId', '')}",
                "date": review.get("at"),
                "rating": review.get("score"),
                "author_hash": hashlib.sha256(
                    str(review.get("userName", "")).encode()
                ).hexdigest()[:16],
                "thumbs_up": review.get("thumbsUpCount", 0),
            }

        logger.info(
            f"Play Store collection complete: {count} records (from {len(all_reviews)} total)",
            extra={"stage": "collector", "source_type": "google_play"},
        )
