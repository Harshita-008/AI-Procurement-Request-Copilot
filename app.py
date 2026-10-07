from __future__ import annotations

import streamlit as st

from src.config import MODEL_NAME, REFERENCE_DATE
from src.data_access import load_requests
from src.mock_api_runner import ensure_mock_api, is_mock_api_up
from src.solution import handle_request
from ui import theme
from ui.panels import render_evidence, render_recommendation, render_request
from ui.saved import find_saved

st.set_page_config(page_title="Procurement Request Copilot", layout="wide")
theme.inject_css()

st.title("AI Procurement Request Copilot")
st.markdown('<div class="subtitle">Evidence-backed next actions for software purchase requests. Every approval stays with a person.</div>'
            + theme.principles(), unsafe_allow_html=True)

requests = {r["request_id"]: r for r in load_requests()}
with st.sidebar:
    st.markdown("#### Analyse a request")
    request_id = st.selectbox("Request", list(requests), format_func=lambda rid: f"{rid} · {requests[rid]['product_name']}")
    architecture = st.radio("Architecture", ["single", "staged", "rules"],
                            captions=["one tool-using agent", "analyst → reviewer", "deterministic only, no model"])
    run = st.button("Run analysis", type="primary", width="stretch")
    load_saved = st.button("Load saved evaluation result", width="stretch",
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

key = f"{request_id}:{architecture}"
if run:
    with st.spinner(f"Running the {architecture} architecture..."):
        try:
            st.session_state[key] = handle_request(request_id, architecture=architecture).model_dump()
        except Exception as exc:
            st.exception(exc)
if load_saved:
    saved = find_saved(request_id, architecture)
    if saved:
        st.session_state[key] = saved
    else:
        st.warning(f"No saved {architecture} result for {request_id}. Run evals/run_comparison.py first.")

left, middle, right = st.columns([0.85, 1.15, 1.0], gap="large")
with left:
    render_request(requests[request_id])
decision = st.session_state.get(key)
with middle:
    if decision:
        render_evidence(decision)
    else:
        st.markdown("### Evidence")
        st.info("Run the analysis to gather evidence from the tools.")
with right:
    if decision:
        render_recommendation(decision, request_id, architecture)
    else:
        st.markdown("### Recommendation")
        st.info("No recommendation yet.")
