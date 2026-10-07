from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> list of dicts with NaN converted to None."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _csv(name: str) -> list[dict]:
    return _records(pd.read_csv(DATA_DIR / name))


def load_employees() -> list[dict]:
    return _csv("employees.csv")


def load_budgets() -> list[dict]:
    return _csv("department_budgets.csv")


def load_software_catalog() -> list[dict]:
    return _csv("software_catalog.csv")


def load_vendors() -> list[dict]:
    return _csv("vendors.csv")


def load_purchase_history() -> list[dict]:
    return _csv("purchase_history.csv")


def load_requests() -> list[dict]:
    return json.loads((DATA_DIR / "requests.json").read_text(encoding="utf-8"))


def get_request(request_id: str) -> dict:
    for request in load_requests():
        if request["request_id"] == request_id:
            return request
    raise KeyError(f"Unknown request_id: {request_id}")


def load_policy_text() -> str:
    return (DATA_DIR / "procurement_policy.md").read_text(encoding="utf-8")
