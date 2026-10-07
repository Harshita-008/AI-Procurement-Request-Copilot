from __future__ import annotations

from urllib.parse import quote

import requests

from src.config import VENDOR_API_TIMEOUT_SECONDS, VENDOR_RISK_BASE_URL


def get_vendor_risk(vendor_name: str, timeout_seconds: float = VENDOR_API_TIMEOUT_SECONDS) -> dict:
    """Low-level client. Raises on any HTTP or network error."""
    url = f"{VENDOR_RISK_BASE_URL.rstrip('/')}/vendor-risk/{quote(vendor_name, safe='')}"
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()


def fetch_vendor_risk(vendor_name: str) -> tuple[dict | None, str, str | None]:
    """Safe wrapper: returns (record, availability, error).

    availability is "ok", "no_record" or "unavailable". Never infers a status on failure.
    """
    try:
        return get_vendor_risk(vendor_name), "ok", None
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        detail = _detail(exc.response)
        if status == 404:
            return None, "no_record", detail
        return None, "unavailable", f"HTTP {status}: {detail}"
    except requests.RequestException as exc:
        return None, "unavailable", f"vendor-risk service unreachable ({type(exc).__name__})"


def _detail(response) -> str:
    try:
        return response.json().get("detail", response.text)
    except Exception:
        return getattr(response, "text", "") or "no detail"
