"""Gemini 3.8 Flash LLM Client with retries, caching, token tracking, and structured output."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from core.llm_config import LLMConfig
from core.errors import RetryableError, PipelineHaltError

logger = logging.getLogger("discovery_engine")

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Production client for Gemini 3.8 Flash API."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = None
        self._cache: dict[str, Any] = {}
        self.stats = {
            "total_calls": 0,
            "cache_hits": 0,
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "errors": 0,
        }
        self._load_cache()

    def _get_client(self):
        """Lazily initialize Google GenAI client."""
        if self._client is None:
            from google import genai

            api_key = self.config.api_key
            if not api_key:
                raise PipelineHaltError("GEMINI_API_KEY environment variable is not set")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def _load_cache(self) -> None:
        """Load response cache from disk."""
        if not self.config.enable_cache:
            return
        cache_path = self.config.cache_path
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} cached LLM responses from {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to load LLM cache: {e}")
                self._cache = {}

    def _save_cache(self) -> None:
        """Persist response cache to disk."""
        if not self.config.enable_cache:
            return
        cache_path = self.config.cache_path
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save LLM cache: {e}")

    def _cache_key(self, prompt: str, schema_name: str = "") -> str:
        """Generate a deterministic SHA-256 hash for caching."""
        content = f"{self.config.model}:{self.config.temperature}:{schema_name}:{prompt}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        response_schema: Type[T] | None = None,
    ) -> dict[str, Any] | str:
        """Generate content from Gemini with caching, retries, and structured schemas.

        Args:
            prompt: User prompt content.
            system_instruction: Optional system instruction.
            response_schema: Optional Pydantic model for structured output.

        Returns:
            Dict matching response_schema if schema is provided, otherwise raw text string.
        """
        schema_name = response_schema.__name__ if response_schema else ""
        cache_key = self._cache_key(f"{system_instruction or ''}\n{prompt}", schema_name)

        if self.config.enable_cache and cache_key in self._cache:
            self.stats["cache_hits"] += 1
            cached_val = self._cache[cache_key]
            logger.debug(f"LLM cache hit: {cache_key[:8]}")
            return cached_val

        # Execute with retries
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                client = self._get_client()
                gen_config: dict[str, Any] = {
                    "temperature": self.config.temperature,
                }
                if system_instruction:
                    gen_config["system_instruction"] = system_instruction
                if response_schema:
                    gen_config["response_mime_type"] = "application/json"
                    gen_config["response_schema"] = response_schema

                response = client.models.generate_content(
                    model=self.config.model,
                    contents=prompt,
                    config=gen_config,
                )

                self.stats["total_calls"] += 1

                # Track token usage if available
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    self.stats["prompt_tokens"] += getattr(response.usage_metadata, "prompt_token_count", 0)
                    self.stats["candidates_tokens"] += getattr(response.usage_metadata, "candidates_token_count", 0)

                raw_text = response.text or ""

                if response_schema:
                    # Parse JSON and validate against schema
                    clean_text = raw_text.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:]
                    if clean_text.startswith("```"):
                        clean_text = clean_text[3:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]
                    clean_text = clean_text.strip()

                    parsed = json.loads(clean_text)
                    # Validate
                    validated = response_schema.model_validate(parsed)
                    result = validated.model_dump()
                else:
                    result = raw_text

                # Store in cache
                if self.config.enable_cache:
                    self._cache[cache_key] = result
                    if self.stats["total_calls"] % 10 == 0:
                        self._save_cache()

                return result

            except Exception as e:
                self.stats["errors"] += 1
                last_error = e
                wait_time = self.config.retry_base_delay * (2 ** attempt)
                logger.warning(
                    f"LLM call failed (attempt {attempt + 1}/{self.config.max_retries}): {e}. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)

        self._save_cache()
        raise RetryableError(f"LLM request failed after {self.config.max_retries} attempts: {last_error}")

    def classify(self, prompt: str, schema: Type[T], system_instruction: str | None = None) -> dict[str, Any]:
        """Classify input using structured schema and optional system instruction."""
        res = self.generate(prompt, system_instruction=system_instruction, response_schema=schema)
        return res if isinstance(res, dict) else json.loads(res)

    def extract(self, prompt: str, schema: Type[T], system_instruction: str | None = None) -> dict[str, Any]:
        """Extract structured entities using schema and optional system instruction."""
        res = self.generate(prompt, system_instruction=system_instruction, response_schema=schema)
        return res if isinstance(res, dict) else json.loads(res)

    def synthesize(self, prompt: str) -> str:
        """Generate narrative synthesis/report text."""
        res = self.generate(prompt)
        return str(res)

    def close(self) -> None:
        """Save cache on shutdown."""
        self._save_cache()
