from __future__ import annotations

import atexit

from src.config import AUTO_START_MOCK_API
from src.contracts import Architecture, ProcurementDecision
from src.mock_api_runner import ensure_mock_api
from src.pipeline import run


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter used by the evaluation harness and the UI."""
    if AUTO_START_MOCK_API:
        proc = ensure_mock_api()
        if proc:
            atexit.register(proc.terminate)
    return run(request_id, architecture)
