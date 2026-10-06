"""Reddit collector using PRAW.

Searches configured subreddits for retrieval-related posts and comments.
Handles pagination, comment depth, and PRAW's built-in rate limits.
"""

from __future__ import annotations

import hashlib
import os
import logging
from typing import Any, Iterator

from collectors.base_collector import BaseCollector, retry_with_backoff

logger = logging.getLogger("discovery_engine")


class RedditCollector(BaseCollector):
    """Collects posts and comments from Reddit subreddits using PRAW."""

    def __init__(self, params: dict[str, Any] | None = None):
        super().__init__(source_type="reddit", params=params)
        self._client = None

    def _get_client(self):
        """Lazily initialize the PRAW client."""
        if self._client is None:
            import praw
            self._client = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID", ""),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
                user_agent=os.getenv("REDDIT_USER_AGENT", "discovery-engine/1.0"),
            )
        return self._client

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def collect(self) -> Iterator[dict[str, Any]]:
        """Search Reddit for retrieval-related posts and comments.

        Yields:
            Raw dicts with: raw_text, source_url, date, subreddit,
            thread_title, reply_depth, author_hash
        """
        client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
        client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret:
            logger.info(
                "Reddit API credentials not configured in .env. Falling back to curated r/googlephotos seed data.",
                extra={"stage": "collector", "source_type": "reddit"},
            )
            yield from self._collect_from_seed()
            return

        try:
            reddit = self._get_client()
        except Exception as e:
            logger.warning(
                f"Failed to initialize Reddit client: {e}. Falling back to seed data.",
                extra={"stage": "collector", "source_type": "reddit"},
            )
            yield from self._collect_from_seed()
            return

        subreddits = self.params.get("subreddits", ["googlephotos"])
        search_queries = self.params.get("search_queries", ["can't find photo"])
        max_results = self.params.get("max_results_per_query", 200)
        include_comments = self.params.get("include_comments", True)
        comment_depth = self.params.get("comment_depth", 3)

        seen_ids = set()
        count = 0

        try:
            for sub_name in subreddits:
                try:
                    subreddit = reddit.subreddit(sub_name)
                except Exception as e:
                    logger.warning(f"Could not access r/{sub_name}: {e}", extra={"stage": "collector", "source_type": "reddit"})
                    continue

            for query in search_queries:
                try:
                    results = subreddit.search(query, limit=max_results, sort="relevance")
                except Exception as e:
                    logger.warning(f"Search failed for '{query}' in r/{sub_name}: {e}", extra={"stage": "collector"})
                    continue

                for submission in results:
                    # Yield the post itself
                    if submission.id not in seen_ids and submission.selftext:
                        seen_ids.add(submission.id)
                        count += 1
                        self._log_progress(count, f"r/{sub_name}")

                        yield {
                            "raw_text": f"{submission.title}\n\n{submission.selftext}",
                            "source_url": f"https://reddit.com{submission.permalink}",
                            "date": submission.created_utc,
                            "subreddit": sub_name,
                            "thread_title": submission.title,
                            "reply_depth": 0,
                            "author_hash": _hash_author(str(submission.author)),
                            "score": submission.score,
                        }

                    # Yield top-level and nested comments
                    if include_comments:
                        try:
                            submission.comments.replace_more(limit=0)
                            for comment in submission.comments.list():
                                if comment.id in seen_ids:
                                    continue
                                if not comment.body or comment.body == "[deleted]" or comment.body == "[removed]":
                                    continue
                                # Respect comment depth
                                depth = _get_comment_depth(comment)
                                if depth > comment_depth:
                                    continue

                                seen_ids.add(comment.id)
                                count += 1
                                self._log_progress(count, f"r/{sub_name}")

                                yield {
                                    "raw_text": comment.body,
                                    "source_url": f"https://reddit.com{comment.permalink}",
                                    "date": comment.created_utc,
                                    "subreddit": sub_name,
                                    "thread_title": submission.title,
                                    "reply_depth": depth,
                                    "author_hash": _hash_author(str(comment.author)),
                                    "score": comment.score,
                                }
                        except Exception as e:
                            logger.warning(f"Comment extraction failed: {e}", extra={"stage": "collector"})
        except Exception as e:
            logger.warning(
                f"PRAW collection failed: {e}. Falling back to curated seed data.",
                extra={"stage": "collector", "source_type": "reddit"},
            )
            yield from self._collect_from_seed()
            return

        logger.info(f"Reddit collection complete: {count} records", extra={"stage": "collector", "source_type": "reddit"})

    def _collect_from_seed(self) -> Iterator[dict[str, Any]]:
        """Yield curated Reddit feedback records when API credentials are not provided."""
        import json
        from pathlib import Path

        seed_paths = [
            Path("data/seed/reddit_seed.json"),
            Path(__file__).parent.parent / "data" / "seed" / "reddit_seed.json",
        ]

        seed_file = next((p for p in seed_paths if p.exists()), None)
        if not seed_file:
            logger.warning("No Reddit seed file found at data/seed/reddit_seed.json", extra={"stage": "collector"})
            return

        with open(seed_file, "r", encoding="utf-8") as f:
            records = json.load(f)

        count = 0
        for rec in records:
            count += 1
            self._log_progress(count, "reddit_seed")
            yield rec

        logger.info(
            f"Loaded {count} Reddit records from seed cache",
            extra={"stage": "collector", "source_type": "reddit"},
        )


def _hash_author(author: str) -> str:
    """SHA-256 hash of author name for dedup without storing PII."""
    return hashlib.sha256(author.encode()).hexdigest()[:16]


def _get_comment_depth(comment) -> int:
    """Calculate the depth of a comment in the thread."""
    depth = 0
    current = comment
    while hasattr(current, "parent_id") and current.parent_id and current.parent_id.startswith("t1_"):
        depth += 1
        try:
            current = current.parent()
        except Exception:
            break
    return depth
