"""Package init: load .env, letting it override shell variables so a stale OS key cannot shadow it."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)
