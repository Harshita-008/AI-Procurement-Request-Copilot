"""Central configuration. Reference date comes from the policy file; provider from the API key present."""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
POLICY_PATH = DATA_DIR / "procurement_policy.md"


def _reference_date_from_policy() -> date:
    text = POLICY_PATH.read_text(encoding="utf-8")
    match = re.search(r"reference date:\*\*\s*(\d{4}-\d{2}-\d{2})", text)
    if not match:
        raise ValueError(f"No reference date found in {POLICY_PATH}")
    return date.fromisoformat(match.group(1))


REFERENCE_DATE = _reference_date_from_policy()
REVIEW_VALID_DAYS = 365

# Provider presets. "sdk" picks the adapter; "model" is a default that MODEL_NAME overrides.
PROVIDERS = {
    "anthropic": {"sdk": "anthropic", "model": "claude-opus-5-5", "key_env": "ANTHROPIC_API_KEY", "base_url": None},
    "openai": {"sdk": "openai", "model": "gpt-5-mini", "key_env": "OPENAI_API_KEY", "base_url": "https://api.openai.com/v1"},
    # Gemini cannot combine JSON response format with tools; the answer is formatted in a second call.
    "gemini": {"sdk": "openai", "model": "gemini-3.1-flash-lite", "key_env": "GEMINI_API_KEY",
               "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "format_with_tools": False},
    "openrouter": {"sdk": "openai", "model": "nvidia/nemotron-3-super-120b-a12b:free", "key_env": "OPENROUTER_API_KEY",
                   "base_url": "https://openrouter.ai/api/v1"},
    "openai_compatible": {"sdk": "openai", "model": "", "key_env": "OPENAI_COMPAT_API_KEY",
                          "base_url": os.getenv("OPENAI_COMPAT_BASE_URL", "")},
}


def detect_provider(env: Mapping[str, str]) -> str:
    """LLM_PROVIDER if set; otherwise the first preset whose API key is present; otherwise anthropic."""
    explicit = (env.get("LLM_PROVIDER") or "").strip().lower()
    if explicit:
        return explicit
    for name, preset in PROVIDERS.items():
        if env.get(preset["key_env"]):
            return name
    return "anthropic"


LLM_PROVIDER = detect_provider(os.environ)
_preset = PROVIDERS.get(LLM_PROVIDER, PROVIDERS["openai_compatible"])
LLM_SDK = _preset["sdk"]
MODEL_NAME = os.getenv("MODEL_NAME") or _preset["model"]
MODEL_EFFORT = os.getenv("MODEL_EFFORT", "")  # Anthropic only; empty = the model's own default
API_KEY = os.getenv(_preset["key_env"], "")
API_BASE_URL = os.getenv("API_BASE_URL") or _preset["base_url"]
FORMAT_WITH_TOOLS = _preset.get("format_with_tools", True)
MAX_AGENT_TURNS = 8
MAX_OUTPUT_TOKENS = 8000

VENDOR_RISK_BASE_URL = os.getenv("VENDOR_RISK_BASE_URL", "http://127.0.0.1:8001")
UI_PORT = os.getenv("UI_PORT", "8501")
VENDOR_API_TIMEOUT_SECONDS = 3.0
# Auto-start the local mock API when it is down. Set false to demo an outage.
AUTO_START_MOCK_API = os.getenv("AUTO_START_MOCK_API", "true").strip().lower() == "true"
