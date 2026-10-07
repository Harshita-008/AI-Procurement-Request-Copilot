"""Tool 1: requester, reporting line and department budget."""
from __future__ import annotations

from src.data_access import load_budgets, load_employees


def get_requester_and_budget(ctx, requester_id: str) -> dict:
    employees = {e["employee_id"]: e for e in load_employees()}
    employee = employees.get(requester_id)
    if employee is None:
        return {"found": False, "requester_id": requester_id, "employee": None, "manager": None, "budget": None,
                "error": f"no employee with id {requester_id}"}
    manager = employees.get(employee.get("manager_id") or "")
    budget = next((b for b in load_budgets() if b["department"] == employee["department"]), None)
    return {
        "found": True,
        "employee": employee,
        "manager": manager,
        "budget": budget,
        "note": None if budget else f"no budget row for department {employee['department']}",
    }
