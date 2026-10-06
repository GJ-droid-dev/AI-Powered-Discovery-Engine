"""Google Photos Support Forum collector.

Scrapes public community threads from https://support.google.com/photos/threads.
Captures user complaints, questions, and retrieval issues directly from Google's official support forum.
"""

from __future__ import annotations

import hashlib
import logging
import urllib.parse
from datetime import datetime
from typing import Any, Iterator

import requests
from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector, rate_limit, retry_with_backoff

logger = logging.getLogger("discovery_engine")


class SupportForumCollector(BaseCollector):
    """Collects user support threads from Google Photos Help Community."""

    def __init__(self, params: dict[str, Any] | None = None):
        super().__init__(source_type="support_forum", params=params)

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def collect(self) -> Iterator[dict[str, Any]]:
        """Search and collect threads from Google Photos Help Community.

        Yields:
            Raw dicts with: raw_text, source_url, date, thread_title, author_hash
        """
        base_url = self.params.get("base_url", "https://support.google.com/photos/threads")
        search_queries = self.params.get(
            "search_queries",
            [
                "can't find photo",
                "search not working",
                "missing photos",
                "lost photos",
                "cannot locate picture",
                "search by date",
                "face search",
                "find old photo",
                "find video",
                "photo disappeared",
            ],
        )
        max_threads = self.params.get("max_threads", 200)
        seen_urls = set()
        count = 0

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        for query in search_queries:
            if count >= max_threads:
                break

            encoded_q = urllib.parse.quote_plus(query)
            url = f"{base_url}?hl=en&max_results=50&q={encoded_q}"

            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code != 200:
                    logger.warning(
                        f"Support forum search failed for '{query}': HTTP {resp.status_code}",
                        extra={"stage": "collector", "source_type": "support_forum"},
                    )
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                links = soup.find_all("a", href=lambda h: h and "/photos/thread/" in h)

                for link in links:
                    if count >= max_threads:
                        break

                    href = link.get("href", "")
                    clean_href = href.split("?")[0]
                    if clean_href in seen_urls:
                        continue
                    seen_urls.add(clean_href)

                    # Extract title and snippet from link children
                    spans = [
                        s.get_text().strip()
                        for s in link.find_all("span")
                        if len(s.get_text().strip()) > 10
                    ]

                    full_url = f"https://support.google.com{clean_href}?hl=en"

                    if len(spans) >= 2:
                        title = spans[0]
                        body = spans[1]
                        raw_text = f"{title}\n\n{body}"
                    elif spans:
                        title = spans[0]
                        raw_text = spans[0]
                    else:
                        text = link.get_text().strip()
                        if len(text) < 20:
                            continue
                        title = text[:80]
                        raw_text = text

                    author_hash = hashlib.sha256(clean_href.encode()).hexdigest()[:16]

                    count += 1
                    self._log_progress(count, "support_forum")

                    yield {
                        "raw_text": raw_text,
                        "source_url": full_url,
                        "date": datetime.now(),
                        "thread_title": title,
                        "author_hash": author_hash,
                    }

            except Exception as e:
                logger.warning(
                    f"Error searching forum for query '{query}': {e}",
                    extra={"stage": "collector", "source_type": "support_forum"},
                )
                continue

        logger.info(
            f"Support forum collection complete: {count} threads",
            extra={"stage": "collector", "source_type": "support_forum"},
        )
