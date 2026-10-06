"""LLM Configuration dataclass for Gemini 3.8 Flash."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")


def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                key = str(st.secrets["GEMINI_API_KEY"])
        except Exception:
            pass
    return key


@dataclass
class LLMConfig:
    """Configuration for LLM API client."""
    model: str = "gemini-3.8-flash"
    temperature: float = 0.0
    max_output_tokens: int = 4096
    api_key: str = field(default_factory=_get_api_key)
    cache_path: Path = field(default_factory=lambda: Path("data/.cache/llm_cache.json"))
    enable_cache: bool = True
    timeout_seconds: float = 45.0
    max_retries: int = 3
    retry_base_delay: float = 2.0
