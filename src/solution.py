"""Entry points: the harness adapter (by request id) and the general analyser (by request record)."""
from __future__ import annotations

import atexit

from src.config import AUTO_START_MOCK_API
from src.contracts import Architecture, ProcurementDecision
from src.data_access import get_request
from src.mock_api_runner import ensure_mock_api
from src.pipeline import run


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter used by the evaluation harness: looks the request up by id."""
    return analyse_request(get_request(request_id), architecture)


def analyse_request(request: dict, architecture: Architecture = "single") -> ProcurementDecision:
    """Analyse any request record, including ones that are not in data/requests.json."""
    if AUTO_START_MOCK_API:
        proc = ensure_mock_api()
        if proc:
            atexit.register(proc.terminate)
    return run(request, architecture)
