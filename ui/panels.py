"""The three product panels: request details, evidence, recommendation + action."""
from __future__ import annotations

import json

import streamlit as st

from src.data_access import load_budgets, load_employees
from ui import theme
from ui.actions import ACTIONS, load_actions, log_action

FLAG_HELP = {
    "existing_tool_overlap": "An approved catalog tool overlaps this request (policy §3)",
    "budget_insufficient": "Cost exceeds the department's available budget (policy §2)",
    "security_review_required": "Security trigger (policy §5)",
    "privacy_review_required": "Privacy trigger (policy §6)",
    "legal_review_required": "Legal trigger (policy §7)",
    "vendor_review_expired": "Vendor assessment older than 365 days",
    "conflicting_vendor_evidence": "Registry and risk service disagree",
    "vendor_risk_unavailable": "Vendor-risk service could not be reached",
    "prompt_injection_detected": "Business data tried to act as instructions (policy §9)",
    "missing_information": "Required request fields are missing (policy §1)",
    "llm_unavailable": "Model call failed; deterministic fallback used",
}


def _money(value) -> str:
    return f"${value:,.0f}" if isinstance(value, (int, float)) else "not provided"


def render_request(req: dict) -> None:
    st.markdown("### Request details")
    employee = next((e for e in load_employees() if e["employee_id"] == req["requester_id"]), None)
    budget = next((b for b in load_budgets() if employee and b["department"] == employee["department"]), None)
    rows = {
        "Request id": req["request_id"],
        "Product": req.get("product_name"),
        "Vendor": req.get("vendor_name"),
        "Category": req.get("category"),
        "Annual cost": _money(req.get("annual_cost_usd")),
        "Users / seats": req.get("user_count") if req.get("user_count") is not None else "not provided",
        "Data access": req.get("data_access_level") or "not provided",
        "Integrations": ", ".join(req.get("requested_integrations") or []) or "none",
        "Urgency": req.get("urgency"),
    }
    st.markdown(theme.card(theme.key_values(rows)), unsafe_allow_html=True)

    who = {
        "Requester": f"{employee['name']} · {employee['level']}" if employee else req["requester_id"],
        "Department": employee["department"] if employee else "unknown",
        "Budget available": _money(budget["available_usd"]) if budget else "unknown",
        "Budget committed": _money(budget["committed_usd"]) if budget else "unknown",
    }
    st.markdown(theme.card("<h3>Requester & budget</h3>" + theme.key_values(who)), unsafe_allow_html=True)

    justification = req.get("business_justification") or "none provided"
    st.markdown(theme.card('<h3>Business justification<span class="tag">untrusted text</span></h3>'
                           f'<div class="quote">{theme.esc(justification)}</div>'), unsafe_allow_html=True)


def render_evidence(decision: dict) -> None:
    tel = decision.get("telemetry") or {}
    st.markdown(f"### Evidence <span class='tag'>{len(decision['evidence'])} findings</span>", unsafe_allow_html=True)
    st.markdown(theme.legend(), unsafe_allow_html=True)
    st.markdown("".join(theme.evidence_card(e) for e in decision["evidence"]), unsafe_allow_html=True)

    trace = tel.get("trace", [])
    tool_calls = [t for t in trace if t.get("type") == "tool_call" and not t.get("internal")]
    llm_calls = [t for t in trace if t.get("type") == "llm_call"]
    tab_trace, tab_draft, tab_fix = st.tabs([f"Tool trace ({len(tool_calls)} tool calls, {len(llm_calls)} model calls)",
                                             "Model draft", f"Guardrail corrections ({len(tel.get('guardrail_corrections', []))})"])
    with tab_trace:
        internal = [t for t in trace if t.get("type") == "tool_call" and t.get("internal")]
        if internal:
            st.caption(f"{len(internal)} internal tool-to-tool calls (made by run_policy_checks, served from cache) are hidden.")
        for t in trace:
            if t.get("type") == "tool_call":
                if t.get("internal"):
                    continue
                tag = "cached" if t.get("cached") else "called"
                st.markdown(f"{theme.badge('tool')}**{t['tool']}** · {tag} · {t['duration_ms']} ms  \n`{json.dumps(t['inputs'])}`",
                            unsafe_allow_html=True)
                st.json(t["output"], expanded=False)
            else:
                st.markdown(f"{theme.badge('model')}**{t.get('label')}** · {t.get('stop_reason')} · "
                            f"tools requested: {', '.join(t.get('tools_requested') or []) or 'none'} · "
                            f"{t.get('input_tokens')} in / {t.get('output_tokens')} out · {t.get('duration_ms')} ms",
                            unsafe_allow_html=True)
    with tab_draft:
        if tel.get("raw_model_output"):
            st.caption("What the model returned before the code guardrail touched it.")
            st.json(tel["raw_model_output"], expanded=False)
        else:
            st.caption("No model draft: this decision came from the deterministic rules only.")
    with tab_fix:
        corrections = tel.get("guardrail_corrections", [])
        st.markdown("\n".join(f"- {c}" for c in corrections) or "_The model draft already matched deterministic policy._")


def render_recommendation(decision: dict, request_id: str, architecture: str) -> None:
    tel = decision.get("telemetry") or {}
    st.markdown("### Recommendation")
    st.markdown(theme.banner(decision.get("recommendation_code", ""), decision["recommendation"], decision.get("summary")),
                unsafe_allow_html=True)
    st.markdown('<div class="human">Human review required. The copilot recommends; it never approves, purchases or changes budgets.</div>',
                unsafe_allow_html=True)

    # One grid row so both cards stretch to the same height.
    st.markdown(theme.grid2(
        theme.card("<h3>Approvals required</h3>" + theme.checklist(decision["required_approvals"])),
        theme.card("<h3>Risk flags</h3>" + theme.chips(decision["risk_flags"], FLAG_HELP)),
    ), unsafe_allow_html=True)
    if decision["missing_information"]:
        st.markdown(theme.card("<h3>Missing information</h3>" + theme.checklist(decision["missing_information"], warn=True)),
                    unsafe_allow_html=True)
    st.markdown(theme.card("<h3>Next step</h3>" + f'<div class="next">{theme.esc(decision["next_step"])}</div>'), unsafe_allow_html=True)

    tokens = (tel.get("input_tokens") or 0) + (tel.get("output_tokens") or 0)
    st.markdown(theme.tiles([
        ("Latency", f"{(tel.get('latency_ms') or 0) / 1000:.1f}", "s"),
        ("Model calls", str(tel.get("llm_calls", 0)), ""),
        ("Tool calls", str(tel.get("tool_calls", 0)), ""),
        ("Tokens", f"{tokens:,}", ""),
    ]), unsafe_allow_html=True)
    st.caption(f"Architecture: {tel.get('architecture', architecture)} · model: {tel.get('model') or 'none (rules only)'}")

    st.markdown("### Reviewer action")
    reviewer = st.text_input("Your name", key=f"reviewer_{request_id}", placeholder="e.g. Procurement reviewer")
    note = st.text_input("Note (optional)", key=f"note_{request_id}", placeholder="Context for the approvers")
    cols = st.columns(len(ACTIONS))
    for col, (code, text) in zip(cols, ACTIONS.items()):
        if col.button(text, key=f"{code}_{request_id}", width="stretch"):
            entry = log_action(request_id, architecture, code, reviewer, note, decision)
            st.toast(f"Logged: {text} by {entry['reviewer']}")
    history = load_actions(request_id)
    if history:
        with st.expander(f"Review history ({len(history)})"):
            for e in reversed(history):
                st.markdown(f"`{e['timestamp']}` · **{ACTIONS.get(e['action'], e['action'])}** · {theme.esc(e['reviewer'])} · {theme.esc(e['note'] or '')}")
