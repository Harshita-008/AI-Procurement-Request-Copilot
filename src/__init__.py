"""Shared package initialization for the assessment starter pack.

A local .env file is loaded automatically and takes precedence over shell variables,
so a stale key in the OS environment cannot shadow the project's .env. This keeps `python run_local.py`, the public eval
runner, and direct module usage consistent.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)
