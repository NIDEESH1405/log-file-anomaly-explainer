"""
app.py
------
Streamlit frontend for Log File Anomaly Explainer.

Run with:
    streamlit run app.py
from the Project/ directory.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Resolve project root and add to sys.path BEFORE any backend import.
# app.py lives at Project/app.py — its parent IS the project root.
# Also load .env here as a safety net (llm_client.py loads it too, but
# doing it early means any backend module that reads env vars at import
# time will also see them).
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed — env vars must be set externally

from backend.log_parser import find_error_block
from backend.llm_explainer import explain_anomaly
from backend.report_generator import format_report, generate_report
from backend.services.llm_client import (
    check_api_key,
    ERR_PERMISSION,
    ERR_NO_KEY,
    ERR_AUTH,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
UPLOADS_DIR = ROOT / "uploads"
REPORTS_DIR = ROOT / "reports"
DB_PATH     = ROOT / "database.db"
UPLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

SEVERITY_EMOJI = {"CRITICAL": "🔴", "ERROR": "🟠", "UNKNOWN": "🟡"}
SEVERITY_COLOR = {"CRITICAL": "#ff4b4b", "ERROR": "#ffa500", "UNKNOWN": "#ffd700"}
DEFAULT_MODEL  = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Page config — must be the FIRST Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Log File Anomaly Explainer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: #0d0d1a !important; color: #e0e0f0 !important;
}
[data-testid="stAppViewContainer"] > .main { background: #0d0d1a; }
[data-testid="stSidebar"] { background: #12122b !important; }

h1 { color: #00e5ff !important; letter-spacing: 1px; }
h2 { color: #a78bfa !important; }
h3 { color: #34d399 !important; }

[data-baseweb="tab-list"] {
    background: #1a1a35 !important; border-radius: 12px; padding: 4px; gap: 4px;
}
[data-baseweb="tab"] {
    border-radius: 8px !important; color: #a0a0c0 !important; font-weight: 600;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: linear-gradient(135deg, #7c3aed, #2563eb) !important; color: #fff !important;
}

.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #2563eb);
    color: #fff; border: none; border-radius: 10px;
    font-weight: 700; padding: 0.5rem 1.5rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stButton > button:hover {
    transform: translateY(-2px); box-shadow: 0 8px 25px rgba(124,58,237,0.45);
}

[data-testid="stFileUploader"] {
    background: #1a1a35; border: 2px dashed #7c3aed; border-radius: 12px; padding: 12px;
}
[data-testid="metric-container"] {
    background: #1a1a35; border: 1px solid #2d2d5e; border-radius: 12px; padding: 16px;
}
pre, code { background: #12122b !important; color: #a5f3fc !important; border-radius: 8px; }
label { color: #a0a0c0 !important; }
[data-testid="stDataFrame"] { border: 1px solid #2d2d5e; border-radius: 8px; }
hr { border-color: #2d2d5e; }
[data-testid="stAlert"]    { border-radius: 10px; }
[data-testid="stExpander"] { background: #1a1a35; border: 1px solid #2d2d5e; border-radius: 10px; }

/* API error banner */
.api-error-box {
    background: #1f0f0f;
    border: 1px solid #7f2020;
    border-left: 4px solid #ff4b4b;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 12px 0;
}
.api-error-box .err-title {
    color: #ff6b6b; font-size: 1rem; font-weight: 700; margin-bottom: 8px;
}
.api-error-box .err-action {
    margin-top: 10px; padding: 8px 12px;
    background: #2d1010; border-radius: 6px;
    color: #ffaaaa; font-size: 0.88rem;
}

/* Mock notice banner */
.mock-notice {
    background: #0f1a2f;
    border: 1px solid #1e3a5f;
    border-left: 4px solid #3b82f6;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 8px 0 16px 0;
    color: #93c5fd;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _card(title: str, content: str) -> None:
    with st.expander(title, expanded=bool(content)):
        if content:
            st.markdown(content)
        else:
            st.caption("_No content returned._")


def _render_api_error(info: dict) -> None:
    """Render a styled, actionable error card for API failures."""
    title  = info.get("title",  "API Error")
    detail = info.get("detail", "")
    action = info.get("action")
    code   = info.get("code",   "")

    # Choose icon by error type
    icon_map = {
        ERR_PERMISSION: "🚫",
        ERR_NO_KEY:     "🔑",
        ERR_AUTH:       "❌",
    }
    icon = icon_map.get(code, "⚠️")

    action_html = ""
    if action:
        action_html = f'<div class="err-action">👉 {action}</div>'

    # Render detail as markdown inside st.warning for link support
    st.markdown(
        f"""<div class="api-error-box">
            <div class="err-title">{icon} {title}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.warning(detail)
    if action:
        st.info(f"👉 {action}")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                filename      TEXT    NOT NULL,
                severity      TEXT,
                timestamp     TEXT,
                summary       TEXT,
                root_cause    TEXT,
                suggested_fix TEXT,
                prevention    TEXT,
                report_path   TEXT,
                created_at    TEXT    NOT NULL
            )
        """)
        conn.commit()


def save_analysis(
    filename: str, severity: str, timestamp: str | None,
    summary: str, root_cause: str, suggested_fix: str,
    prevention: str, report_path: str,
) -> None:
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO analyses
                (filename, severity, timestamp, summary,
                 root_cause, suggested_fix, prevention,
                 report_path, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            filename, severity, timestamp or "",
            summary, root_cause, suggested_fix, prevention,
            report_path, datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()


def get_history(search: str = "") -> pd.DataFrame:
    with _get_conn() as conn:
        if search:
            df = pd.read_sql_query("""
                SELECT id, filename, severity, timestamp,
                       substr(summary,1,120) AS summary_preview,
                       created_at, report_path
                FROM analyses
                WHERE filename LIKE ? OR summary LIKE ?
                ORDER BY created_at DESC
            """, conn, params=(f"%{search}%", f"%{search}%"))
        else:
            df = pd.read_sql_query("""
                SELECT id, filename, severity, timestamp,
                       substr(summary,1,120) AS summary_preview,
                       created_at, report_path
                FROM analyses ORDER BY created_at DESC
            """, conn)
    return df


def get_full_record(row_id: int) -> sqlite3.Row | None:
    with _get_conn() as conn:
        return conn.execute("SELECT * FROM analyses WHERE id=?", (row_id,)).fetchone()


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
init_db()

# ---------------------------------------------------------------------------
# Startup: check API key and show a sidebar status
# ---------------------------------------------------------------------------
key_ok, key_msg = check_api_key()

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    if key_ok:
        st.success("✅ GROQ_API_KEY is set", icon="🔑")
    else:
        st.error("❌ GROQ_API_KEY missing", icon="🔑")
        st.markdown("""
**To enable AI analysis:**

1. Get a **free** key at [console.groq.com](https://console.groq.com)
2. Add it to your `.env` file:
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```
3. Restart the app

**On Render:** set `GROQ_API_KEY` in your service *Environment* settings.

You can still use the app — tick **Skip LLM** to analyse logs without AI.
        """)
    st.divider()
    st.caption("Log File Anomaly Explainer · Powered by Groq")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align:center; padding: 1.5rem 0 0.5rem;">
    <h1 style="font-size:2.4rem; margin-bottom:0;">🔍 Log File Anomaly Explainer</h1>
    <p style="color:#6b6b9f; font-size:1rem; margin-top:4px;">
        AI-powered log analysis for on-call engineers · Powered by Groq
    </p>
</div>
""", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_analyze, tab_dashboard, tab_history = st.tabs(
    ["🚀  Analyze Log", "📊  Dashboard", "📜  History"]
)

# ============================================================
# TAB 1 — Analyze Log
# ============================================================
with tab_analyze:
    st.subheader("Upload & Analyze a Log File")

    uploaded = st.file_uploader(
        "Drop a `.log` or `.txt` file here",
        type=["log", "txt"],
        help="Plain-text log files up to a few hundred MB are handled efficiently.",
    )

    if not uploaded:
        st.info("Upload a log file above to get started.")
        if not key_ok:
            st.markdown("""
<div class="api-error-box">
<div class="err-title">🔑 Groq API key not configured</div>
</div>
            """, unsafe_allow_html=True)
            st.warning(
                "No `GROQ_API_KEY` found. The log parser will still work, "
                "but AI explanation requires a key.\n\n"
                "See the **sidebar** for setup instructions, "
                "or tick **Skip LLM** after uploading a file."
            )
        st.stop()

    # ── Options ───────────────────────────────────────────────
    col_model, col_ctx, col_skip = st.columns([2, 2, 1])
    with col_model:
        model = st.text_input(
            "Groq model", value=DEFAULT_MODEL,
            help="Groq model tag — e.g. llama-3.3-70b-versatile, mixtral-8x7b-32768",
        )
    with col_ctx:
        context_lines = st.slider(
            "Context lines", min_value=5, max_value=60, value=20, step=5,
        )
    with col_skip:
        st.markdown("<br>", unsafe_allow_html=True)
        no_llm = st.checkbox(
            "Skip LLM", value=(not key_ok),
            help="Parse only — no AI explanation. Auto-enabled when API key is missing.",
        )

    if not st.button("🚀  Analyze", type="primary", width="stretch"):
        st.stop()

    # ── Save upload ───────────────────────────────────────────
    upload_path = UPLOADS_DIR / uploaded.name
    upload_path.write_bytes(uploaded.getbuffer())

    # ── Step 1: parse ─────────────────────────────────────────
    with st.status("🔎 Scanning log file…", expanded=False) as status:
        try:
            log_context = find_error_block(str(upload_path), context_lines=context_lines)
        except Exception as exc:
            status.update(label="❌ Failed to parse log file.", state="error")
            st.error(f"Parse error: {exc}")
            st.stop()
        status.update(label="✅ Log file scanned.", state="complete")

    # ── No error found ────────────────────────────────────────
    if not log_context["found"]:
        st.success("✅ No errors or anomalies detected in this log file.")
        report_md   = format_report(log_context, explanation=None)
        report_path = REPORTS_DIR / f"{upload_path.stem}_{_ts()}.md"
        report_path.write_text(report_md, encoding="utf-8")
        st.download_button("📥 Download Clean Report", report_md, file_name=report_path.name)
        st.stop()

    # ── Anomaly banner ────────────────────────────────────────
    sev   = log_context["severity"]
    color = SEVERITY_COLOR.get(sev, "#ffffff")
    emoji = SEVERITY_EMOJI.get(sev, "🔵")
    first = log_context["error_block"][0] if log_context["error_block"] else ""
    st.markdown(f"""
<div style="background:#1a1a35; border-left:4px solid {color};
            border-radius:10px; padding:16px 20px; margin:12px 0;">
    <span style="color:{color}; font-size:1.1rem; font-weight:700;">
        {emoji} Anomaly Detected — {sev}
    </span><br>
    <span style="color:#8080a0; font-size:0.85rem;">
        Line {log_context['error_line_index']} of {log_context['total_lines']}
        &nbsp;·&nbsp; {log_context['timestamp'] or 'no timestamp'}
    </span><br>
    <code style="color:#a5f3fc; font-size:0.82rem;">{first}</code>
</div>
    """, unsafe_allow_html=True)

    # ── Step 2: LLM ───────────────────────────────────────────
    explanation: dict | None = None

    if no_llm:
        st.info("⏭️ LLM step skipped — showing raw log analysis only.")
    else:
        with st.status(
            f"🤖 Asking **{model}** (Groq) to explain the anomaly…", expanded=False
        ) as llm_status:
            explanation = explain_anomaly(log_context, model=model, use_mock_on_failure=True)

            if explanation.get("error"):
                # Hard failure (shouldn't normally reach here with mock enabled)
                llm_status.update(label="❌ AI analysis failed.", state="error")

            elif explanation.get("is_mock"):
                llm_status.update(
                    label="⚠️ Groq API unavailable — showing basic analysis.",
                    state="error",
                )

            else:
                llm_status.update(label="✅ AI analysis complete.", state="complete")

    # ── API error banner (shown OUTSIDE the spinner, always visible) ──
    if explanation and explanation.get("is_mock"):
        err_info = explanation.get("api_error_info", {})
        _render_api_error(err_info)

        # Contextual tip based on error type
        err_code = err_info.get("code", "")
        if err_code == ERR_PERMISSION:
            st.markdown("""
<div class="mock-notice">
💡 <strong>The log was parsed successfully.</strong>
Scroll down to see the raw error block and context.
Once you fix the API key at
<a href="https://console.groq.com" target="_blank">console.groq.com</a>,
re-run for full AI analysis.
</div>
            """, unsafe_allow_html=True)
        elif err_code in (ERR_NO_KEY, ERR_AUTH):
            st.markdown("""
<div class="mock-notice">
💡 <strong>The log was parsed successfully.</strong>
Set a valid <code>GROQ_API_KEY</code> in your <code>.env</code> file
(see the sidebar) then re-run for AI analysis.
</div>
            """, unsafe_allow_html=True)
        elif err_code == "RATE_LIMIT":
            st.markdown("""
<div class="mock-notice">
⏳ <strong>Groq rate limit hit.</strong>
Wait 30 seconds, reduce Context lines, then click Analyze again.
The parsed log is shown below.
</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
<div class="mock-notice">
💡 <strong>The log was parsed successfully.</strong>
The AI step failed — raw error block and context are shown below.
</div>
            """, unsafe_allow_html=True)

    elif explanation and explanation.get("error"):
        st.error(explanation["error"])

    # ── Step 3: generate & save report ────────────────────────
    report_md   = format_report(log_context, explanation=explanation)
    report_path = REPORTS_DIR / f"{upload_path.stem}_{_ts()}.md"
    report_path.write_text(report_md, encoding="utf-8")

    # ── Persist to DB ─────────────────────────────────────────
    save_analysis(
        filename      = uploaded.name,
        severity      = sev,
        timestamp     = log_context.get("timestamp"),
        summary       = explanation.get("summary",       "") if explanation else "",
        root_cause    = explanation.get("root_cause",    "") if explanation else "",
        suggested_fix = explanation.get("suggested_fix", "") if explanation else "",
        prevention    = explanation.get("prevention",    "") if explanation else "",
        report_path   = str(report_path),
    )

    # ── Results ───────────────────────────────────────────────
    st.divider()

    has_content = (
        explanation is not None
        and not explanation.get("error")
        and any(explanation.get(k) for k in ("summary", "root_cause", "suggested_fix"))
    )

    if has_content:
        is_mock = explanation.get("is_mock", False)

        if is_mock:
            st.markdown("### 📋 Basic Analysis")
            st.caption(
                "Rule-based analysis — AI explanation unavailable. "
                "Resolve the API issue above for full Grok analysis."
            )
        else:
            st.markdown("### 🤖 AI Analysis")
            st.caption(f"Generated by Groq (`{explanation.get('model', model)}`) · review before acting in production.")

        c1, c2 = st.columns(2)
        with c1:
            _card("📋 Summary",          explanation.get("summary",          ""))
            _card("🔎 Why It Happened",   explanation.get("why_it_happened",  ""))
            _card("🛡️ Prevention",        explanation.get("prevention",       ""))
        with c2:
            _card("🎯 Root Cause",        explanation.get("root_cause",       ""))
            _card("🛠️ Suggested Fix",     explanation.get("suggested_fix",    ""))

        st.divider()

    # ── Raw log sections — always visible ────────────────────
    with st.expander("🚨 Raw Error Block", expanded=True):
        st.code("\n".join(log_context.get("error_block", [])), language="log")

    col_b, col_a = st.columns(2)
    with col_b:
        n = len(log_context.get("context_before", []))
        with st.expander(f"📜 Context Before ({n} lines)"):
            st.code("\n".join(log_context.get("context_before", [])), language="log")
    with col_a:
        n = len(log_context.get("context_after", []))
        with st.expander(f"📜 Context After ({n} lines)"):
            st.code("\n".join(log_context.get("context_after", [])), language="log")

    if explanation and explanation.get("raw_llm_response"):
        with st.expander("🗒️ Raw LLM Response"):
            st.text(explanation["raw_llm_response"])

    # ── Report download ───────────────────────────────────────
    st.divider()
    st.markdown("### 📄 Full Report")
    with st.expander("Preview Markdown", expanded=False):
        st.markdown(report_md, unsafe_allow_html=True)

    st.download_button(
        label="📥 Download Markdown Report",
        data=report_md,
        file_name=report_path.name,
        mime="text/markdown",
        width="stretch",
    )

# ============================================================
# TAB 2 — Dashboard
# ============================================================
with tab_dashboard:
    st.subheader("Overview")

    df_all  = get_history()
    total   = len(df_all)
    n_crit  = int((df_all["severity"] == "CRITICAL").sum()) if total else 0
    n_err   = int((df_all["severity"] == "ERROR").sum())    if total else 0
    n_other = total - n_crit - n_err

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Analyses", total)
    m2.metric("🔴 Critical",    n_crit)
    m3.metric("🟠 Errors",      n_err)
    m4.metric("🟡 Other",       n_other)

    if total == 0:
        st.info("No analyses yet. Upload a log file in the **Analyze Log** tab.")
    else:
        st.divider()
        col_sev, col_time = st.columns(2)
        with col_sev:
            st.markdown("#### Severity Breakdown")
            sc = df_all["severity"].value_counts().reset_index()
            sc.columns = ["Severity", "Count"]
            st.bar_chart(sc.set_index("Severity"), color="#7c3aed")
        with col_time:
            st.markdown("#### Analyses Over Time")
            dt = df_all.copy()
            dt["date"] = pd.to_datetime(dt["created_at"], errors="coerce").dt.date
            tc = dt.groupby("date").size().reset_index(name="Count")
            if not tc.empty:
                st.line_chart(tc.set_index("date"), color="#00e5ff")
        st.divider()
        st.markdown("#### Recent Analyses")
        st.dataframe(
            df_all.head(10)[["filename", "severity", "timestamp", "created_at", "summary_preview"]],
            width="stretch", hide_index=True,
        )

# ============================================================
# TAB 3 — History
# ============================================================
with tab_history:
    st.subheader("Analysis History")

    search  = st.text_input(
        "🔍 Search by filename or summary", placeholder="payment, OOM, database…"
    )
    df_hist = get_history(search)

    if df_hist.empty:
        st.info("No analyses found." + (" Try a different search term." if search else ""))
    else:
        st.caption(f"{len(df_hist)} record(s) found.")
        st.dataframe(
            df_hist[["id", "filename", "severity", "timestamp", "created_at", "summary_preview"]],
            width="stretch", hide_index=True,
        )
        st.divider()
        st.markdown("#### View a Saved Report")
        selected_id = st.number_input(
            "Enter report ID", min_value=1, step=1, value=int(df_hist["id"].iloc[0]),
        )
        if st.button("Load Report", width="stretch"):
            row = get_full_record(int(selected_id))
            if row is None:
                st.error(f"No record with ID {selected_id}.")
            else:
                st.markdown(f"**File:** `{row['filename']}`  **Severity:** `{row['severity']}`")
                rpath = Path(row["report_path"])
                if rpath.exists():
                    md_content = rpath.read_text(encoding="utf-8")
                    with st.expander("Report Preview", expanded=True):
                        st.markdown(md_content, unsafe_allow_html=True)
                    st.download_button(
                        "📥 Download Report", data=md_content,
                        file_name=rpath.name, mime="text/markdown",
                    )
                else:
                    st.warning("Report file not found on disk. Showing stored fields.")
                    for label, key in (
                        ("Summary",       "summary"),
                        ("Root Cause",    "root_cause"),
                        ("Suggested Fix", "suggested_fix"),
                        ("Prevention",    "prevention"),
                    ):
                        val = row[key]
                        if val:
                            st.markdown(f"**{label}:** {val}")
