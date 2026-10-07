from __future__ import annotations

import hashlib
import json

import streamlit as st

from src.config import MODEL_NAME, REFERENCE_DATE
from src.data_access import load_requests
from src.mock_api_runner import ensure_mock_api, is_mock_api_up
from src.request_normalize import normalize_request
from src.solution import analyse_request
from ui import custom_request, theme
from ui.panels import render_evidence, render_recommendation, render_request
from ui.saved import find_saved

st.set_page_config(page_title="Procurement Request Copilot", layout="wide")
theme.inject_css()

st.title("AI Procurement Request Copilot")
st.markdown('<div class="subtitle">Evidence-backed next actions for software purchase requests. Every approval stays with a person.</div>'
            + theme.principles(), unsafe_allow_html=True)


def result_key(request: dict, architecture: str) -> str:
    """Session key for a decision: changes whenever the request content or architecture changes."""
    digest = hashlib.sha1(json.dumps(request, sort_keys=True, default=str).encode()).hexdigest()[:8]
    return f"{request['request_id']}:{architecture}:{digest}"


samples = {r["request_id"]: r for r in load_requests()}
with st.sidebar:
    st.markdown("#### Analyse a request")
    source = st.radio("Request source", ["Sample request", "Custom request"], horizontal=True, label_visibility="collapsed")
    if source == "Sample request":
        request_id = st.selectbox("Request", list(samples), format_func=lambda rid: f"{rid} · {samples[rid]['product_name']}")
        request = samples[request_id]
    else:
        st.caption("Type any request, including incomplete or adversarial ones. Fields are treated as untrusted data.")
        request = custom_request.request_form()
    architecture = st.radio("Architecture", ["single", "staged", "rules"],
                            captions=["one tool-using agent", "analyst → reviewer", "deterministic only, no model"])
    run = st.button("Run analysis", type="primary", width="stretch")
    load_saved = st.button("Load saved evaluation result", width="stretch", disabled=source != "Sample request",
                           help="Shows the decision recorded by evals/run_comparison.py; needs no model key")
    st.divider()
    st.markdown("#### Services")
    api_up = is_mock_api_up()
    st.markdown(theme.status(api_up, "Vendor-risk API online" if api_up else "Vendor-risk API offline"), unsafe_allow_html=True)
    if not api_up and st.button("Start vendor-risk API", width="stretch"):
        ensure_mock_api()
        st.rerun()
    st.caption(f"Model: {MODEL_NAME}")
    st.caption(f"Policy reference date: {REFERENCE_DATE}")

key = result_key(request, architecture)
if run:
    with st.spinner(f"Running the {architecture} architecture..."):
        try:
            st.session_state[key] = analyse_request(request, architecture=architecture).model_dump()
        except Exception as exc:
            st.exception(exc)
if load_saved:
    saved = find_saved(request["request_id"], architecture)
    if saved:
        st.session_state[key] = saved
    else:
        st.warning(f"No saved {architecture} result for {request['request_id']}. Run evals/run_comparison.py first.")

left, middle, right = st.columns([0.85, 1.15, 1.0], gap="large")
with left:
    render_request(normalize_request(request))
decision = st.session_state.get(key)
with middle:
    if decision:
        render_evidence(decision)
    else:
        st.markdown("### Evidence")
        st.info("Run the analysis to gather evidence from the tools.")
with right:
    if decision:
        render_recommendation(decision, request["request_id"], architecture)
    else:
        st.markdown("### Recommendation")
        st.info("No recommendation yet.")
