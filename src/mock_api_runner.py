"""Start the mock vendor-risk API when it is not already running (used by evals and the UI)."""
from __future__ import annotations

import subprocess
import sys
import time

import requests

from src.config import ROOT, VENDOR_RISK_BASE_URL


def is_mock_api_up(base_url: str = VENDOR_RISK_BASE_URL) -> bool:
    try:
        return requests.get(f"{base_url.rstrip('/')}/health", timeout=0.5).ok
    except requests.RequestException:
        return False


def ensure_mock_api(base_url: str = VENDOR_RISK_BASE_URL, timeout_seconds: float = 10.0) -> subprocess.Popen | None:
    """Return a Popen if this call started the API (caller should terminate it), else None."""
    if is_mock_api_up(base_url):
        return None
    host, _, port = base_url.replace("http://", "").replace("https://", "").rpartition(":")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mock_api.app:app", "--host", host or "127.0.0.1", "--port", port or "8001", "--log-level", "warning"],
        cwd=ROOT,
    )
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_mock_api_up(base_url):
            return proc
        if proc.poll() is not None:
            raise RuntimeError(f"mock API exited with code {proc.returncode}")
        time.sleep(0.25)
    proc.terminate()
    raise RuntimeError("mock API did not become ready")
