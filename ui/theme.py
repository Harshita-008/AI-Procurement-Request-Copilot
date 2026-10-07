"""Visual theme: dark surface, one cyan accent, subtle glow. All user data is escaped before rendering."""
from __future__ import annotations

import html

import streamlit as st

CSS = """
<style>
:root {
  --bg:#171a2b; --sidebar:#12141f; --surface:#1e2235; --surface2:#262b42; --line:#2c3250;
  --text:#f1f5f9; --muted:#a0a7bd; --accent:#ff4d6d; --accent2:#22d3ee;
  --green:#2dd4a0; --amber:#fbbf24; --red:#ff4d6d; --blue:#5aa9ff;
  --shadow:0 8px 24px rgba(0,0,0,.28);
}
html, body, [data-testid="stAppViewContainer"] {background:var(--bg); color:var(--text);}
.block-container {padding-top:1.4rem; padding-bottom:2.5rem; max-width:1560px;}
h1 {font-size:1.7rem; font-weight:700; letter-spacing:-.01em; margin:0 0 .25rem 0; color:#fff;}
.stMarkdown h3, .card h3 {font-size:.76rem !important; font-weight:700 !important; letter-spacing:.1em; text-transform:uppercase;
                           color:var(--muted) !important; margin:0 0 .8rem 0 !important; padding:0 !important;}
.grid2 {display:grid; grid-template-columns:1fr 1fr; gap:.9rem; align-items:stretch; margin-bottom:.9rem;}
.grid2 .card {margin-bottom:0; height:100%;}
.tiles {display:grid; grid-template-columns:1fr 1fr; gap:.8rem; margin:.2rem 0 .9rem 0;}
.tile {background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:.85rem 1rem; box-shadow:var(--shadow);}
.tile .l {font-size:.7rem; color:var(--muted); letter-spacing:.08em; text-transform:uppercase;}
.tile .n {font-size:1.45rem; font-weight:700; color:#fff; margin-top:.15rem; line-height:1.2;}
.tile .n small {font-size:.8rem; color:var(--muted); font-weight:500; margin-left:.25rem;}
p, li, label, .stMarkdown {color:var(--text);}
.subtitle {color:var(--muted); font-size:.95rem; margin-bottom:1rem;}
.principles {display:flex; gap:.55rem; margin:0 0 1.5rem 0; flex-wrap:wrap;}
.pill {padding:.38rem .9rem; border-radius:999px; font-size:.8rem; font-weight:600; background:var(--surface);
       border:1px solid var(--line); color:var(--text); box-shadow:var(--shadow);}
.pill b {color:var(--accent); font-weight:700; margin-right:.35rem;}
.card {background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:1.1rem 1.25rem;
       margin-bottom:.9rem; box-shadow:var(--shadow);}
.kv {display:grid; grid-template-columns: 40% 60%; row-gap:.55rem; column-gap:.6rem; font-size:.92rem; align-items:baseline;}
.kv .k {color:var(--muted);} .kv .v {color:#fff; font-weight:600; word-break:break-word;}
.quote {border-left:3px solid var(--accent); background:var(--surface2); padding:.7rem .95rem; border-radius:10px;
        font-size:.92rem; color:var(--text); line-height:1.5;}
.tag {display:inline-block; font-size:.66rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
      padding:.16rem .55rem; border-radius:6px; background:rgba(255,77,109,.14); color:var(--accent); margin-left:.5rem; vertical-align:middle;}
.legend {color:var(--muted); font-size:.8rem; margin:-.2rem 0 .8rem 0;}
.legend i {display:inline-block; width:.6rem; height:.6rem; border-radius:3px; margin:0 .35rem 0 .7rem; vertical-align:middle;}
.evidence {background:var(--surface); border:1px solid var(--line); border-left:4px solid var(--blue); border-radius:14px;
           padding:.8rem 1rem; margin-bottom:.65rem; box-shadow:var(--shadow);}
.evidence.deterministic {border-left-color:var(--green);}
.evidence .src {font-family:ui-monospace, Menlo, Consolas, monospace; font-size:.76rem; font-weight:700; color:var(--blue);}
.evidence.deterministic .src {color:var(--green);}
.evidence .ref {font-size:.76rem; color:var(--muted); margin-left:.6rem;}
.evidence .finding {margin-top:.4rem; font-size:.92rem; color:var(--text); line-height:1.5;}
.banner {border-radius:16px; padding:1.1rem 1.3rem; margin-bottom:.9rem; border:1px solid var(--line); background:var(--surface);
         box-shadow:var(--shadow); position:relative; overflow:hidden;}
.banner::before {content:""; position:absolute; left:0; top:0; bottom:0; width:5px;}
.banner .label {font-size:.7rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;}
.banner .title {font-size:1.3rem; font-weight:700; margin:.25rem 0 .4rem 0; color:#fff;}
.banner .summary {font-size:.93rem; color:var(--text); line-height:1.5;}
.banner.green::before {background:var(--green);} .banner.green .label {color:var(--green);}
.banner.amber::before {background:var(--amber);} .banner.amber .label {color:var(--amber);}
.banner.blue::before  {background:var(--blue);}  .banner.blue .label  {color:var(--blue);}
.banner.red::before   {background:var(--red);}   .banner.red .label   {color:var(--red);}
.chip {display:inline-block; font-size:.76rem; font-weight:600; padding:.3rem .7rem; border-radius:999px;
       margin:0 .4rem .45rem 0; background:var(--surface2); border:1px solid var(--line);}
.chip.red {color:var(--red); border-color:rgba(255,77,109,.45);}
.chip.amber {color:var(--amber); border-color:rgba(251,191,36,.45);}
.chip.grey {color:var(--text); border-color:var(--line);}
.check {font-size:.92rem; margin:.25rem 0; color:var(--text); display:flex; align-items:center;}
.check i {display:inline-block; width:.5rem; height:.5rem; border-radius:50%; background:var(--green); margin-right:.65rem; flex:none;
          box-shadow:0 0 8px var(--green);}
.check.warn i {background:var(--amber); box-shadow:0 0 8px var(--amber);}
.next {background:var(--surface2); border:1px solid var(--line); color:#fff; border-radius:12px; padding:.8rem 1rem;
       font-size:.93rem; line-height:1.5;}
.human {font-size:.82rem; color:var(--amber); background:rgba(251,191,36,.08); border:1px solid rgba(251,191,36,.3);
        border-radius:12px; padding:.55rem .85rem; margin-bottom:.9rem;}
.muted {color:var(--muted); font-size:.85rem;}
.badge {display:inline-block; font-size:.66rem; font-weight:700; letter-spacing:.08em; padding:.14rem .5rem; border-radius:6px;
        margin-right:.5rem; vertical-align:middle;}
.badge.tool {background:rgba(90,169,255,.16); color:var(--blue);} .badge.model {background:rgba(255,77,109,.16); color:var(--accent);}
div[data-testid="stMetric"] {background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:.75rem 1rem; box-shadow:var(--shadow);}
div[data-testid="stMetric"] label {font-size:.72rem; color:var(--muted); letter-spacing:.06em; text-transform:uppercase;}
div[data-testid="stMetricValue"] {color:#fff; font-weight:700;}
section[data-testid="stSidebar"] {background:var(--sidebar); border-right:1px solid var(--line);}
section[data-testid="stSidebar"] * {color:var(--text);}
section[data-testid="stSidebar"] h4 {font-size:.74rem; letter-spacing:.1em; text-transform:uppercase; color:var(--muted) !important;}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *, section[data-testid="stSidebar"] small {color:var(--muted) !important;}
.stTabs [data-baseweb="tab-list"] {gap:.3rem; border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"] {color:var(--muted);} .stTabs [aria-selected="true"] {color:#fff;}
.status {display:flex; align-items:center; font-size:.88rem; color:#fff; padding:.55rem .8rem; border-radius:12px;
         border:1px solid var(--line); background:var(--surface);}
.status i {width:.55rem; height:.55rem; border-radius:50%; margin-right:.65rem; display:inline-block;}
.status.ok i {background:var(--green); box-shadow:0 0 10px var(--green);}
.status.down i {background:var(--red); box-shadow:0 0 10px var(--red);}
div[data-testid="stExpander"] {background:var(--surface); border:1px solid var(--line); border-radius:12px;}
</style>
"""

RECOMMENDATION_TONE = {
    "approve_with_standard_approvals": "green",
    "evaluate_existing_tool_first": "blue",
    "route_for_reviews": "amber",
    "request_clarification": "amber",
    "escalate_budget_exception": "red",
    "escalate_manual_review": "red",
}

FLAG_TONE = {
    "budget_insufficient": "red", "vendor_risk_unavailable": "red", "conflicting_vendor_evidence": "red",
    "prompt_injection_detected": "red", "llm_unavailable": "red",
    "security_review_required": "amber", "privacy_review_required": "amber", "legal_review_required": "amber",
    "vendor_review_expired": "amber", "missing_information": "amber",
    "existing_tool_overlap": "grey",
}

DETERMINISTIC_SOURCES = {"budget_check", "approval_thresholds", "catalog_overlap", "vendor_status",
                         "data_classification", "required_fields", "injection_scan"}


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def principles() -> str:
    return ('<div class="principles"><span class="pill"><b>AI</b>interprets and recommends</span>'
            '<span class="pill"><b>Code</b>thresholds and deterministic checks</span>'
            '<span class="pill"><b>Human</b>approvals and exceptions</span></div>')


def card(inner_html: str) -> str:
    return f'<div class="card">{inner_html}</div>'


def grid2(left_html: str, right_html: str) -> str:
    """Two cards side by side with equal height."""
    return f'<div class="grid2">{left_html}{right_html}</div>'


def key_values(rows: dict) -> str:
    cells = "".join(f'<div class="k">{esc(k)}</div><div class="v">{esc(v)}</div>' for k, v in rows.items())
    return f'<div class="kv">{cells}</div>'


def legend() -> str:
    return ('<div class="legend">Source<i style="background:var(--blue)"></i>model finding from a tool it called'
            '<i style="background:var(--green)"></i>deterministic policy engine</div>')


def evidence_card(item: dict) -> str:
    kind = "deterministic" if item.get("source") in DETERMINISTIC_SOURCES else ""
    ref = f'<span class="ref">{esc(item["reference"])}</span>' if item.get("reference") else ""
    return (f'<div class="evidence {kind}"><span class="src">{esc(item.get("source"))}</span>{ref}'
            f'<div class="finding">{esc(item.get("finding"))}</div></div>')


TONE_LABEL = {"green": "Clear to proceed", "blue": "Check existing tool", "amber": "Needs attention", "red": "Escalation"}


def banner(code: str, label: str, summary: str | None) -> str:
    tone = RECOMMENDATION_TONE.get(code, "grey")
    text = f'<div class="summary">{esc(summary)}</div>' if summary else ""
    return (f'<div class="banner {tone}"><div class="label">{TONE_LABEL.get(tone, "Outcome")}</div>'
            f'<div class="title">{esc(label)}</div>{text}</div>')


def tiles(items: list[tuple[str, str, str]]) -> str:
    """(label, value, unit) tuples rendered as a 2x2 metric grid."""
    cells = "".join(f'<div class="tile"><div class="l">{esc(l)}</div><div class="n">{esc(v)}<small>{esc(u)}</small></div></div>'
                    for l, v, u in items)
    return f'<div class="tiles">{cells}</div>'


def chips(flags: list[str], help_text: dict[str, str]) -> str:
    if not flags:
        return '<span class="muted">none</span>'
    return "".join(f'<span class="chip {FLAG_TONE.get(f, "grey")}" title="{esc(help_text.get(f, ""))}">{esc(f)}</span>'
                   for f in flags)


def checklist(items: list[str], warn: bool = False) -> str:
    if not items:
        return '<span class="muted">none</span>'
    cls = "check warn" if warn else "check"
    return "".join(f'<div class="{cls}"><i></i>{esc(i)}</div>' for i in items)


def badge(kind: str) -> str:
    return f'<span class="badge {kind}">{kind.upper()}</span>'


def status(ok: bool, text: str) -> str:
    return f'<div class="status {"ok" if ok else "down"}"><i></i>{esc(text)}</div>'
