"""
llm_explainer.py
----------------
Sends a parsed log-error context to the Groq API (via llm_client) and
returns a structured explanation of the anomaly.

Public API
~~~~~~~~~~
    explain_anomaly(log_context, model, use_mock_on_failure) -> dict
"""

from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Robust import: works when loaded as backend.llm_explainer (via app.py)
# or run directly from inside the backend/ directory.
# ---------------------------------------------------------------------------
try:
    from backend.services.llm_client import (
        ERR_NO_KEY, ERR_AUTH, ERR_PERMISSION, ERR_RATE_LIMIT,
        ERR_CONNECTION, ERR_TIMEOUT, ERR_API, ERR_UNKNOWN,
        _DEFAULT_MODEL, call_llm,
    )
except ModuleNotFoundError:
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from backend.services.llm_client import (   # type: ignore[no-redef]
        ERR_NO_KEY, ERR_AUTH, ERR_PERMISSION, ERR_RATE_LIMIT,
        ERR_CONNECTION, ERR_TIMEOUT, ERR_API, ERR_UNKNOWN,
        _DEFAULT_MODEL, call_llm,
    )

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert Site Reliability Engineer (SRE) and software debugger.
    Your job is to analyse application log errors and provide clear, actionable
    explanations for engineering teams.

    When given a log snippet containing an error, you MUST respond with EXACTLY
    the following five labelled sections and nothing else.  Each label must
    appear on its own line followed by the content on the next line(s).

    SUMMARY:
    <1-2 sentence plain-English description of what went wrong>

    ROOT_CAUSE:
    <The most probable technical root cause, referencing specific details from
     the log where possible>

    WHY_IT_HAPPENED:
    <Contextual explanation of the conditions or sequence of events that led to
     this error>

    SUGGESTED_FIX:
    <Concrete, actionable step(s) the on-call engineer should take right now to
     resolve or mitigate the issue>

    PREVENTION:
    <2-3 specific practices, code changes, or monitoring improvements that would
     prevent this class of error in future>

    Keep each section concise but technically precise.  Do not add extra
    headings, preamble, or closing remarks outside the five sections above.
""")

_USER_PROMPT_TEMPLATE = textwrap.dedent("""\
    Please analyse the following log error and provide your structured explanation.

    --- ERROR METADATA ---
    Severity : {severity}
    Timestamp: {timestamp}
    Log file : {log_path}
    Error at line {error_line_index} of {total_lines}

    --- ERROR BLOCK ---
    {error_block}

    --- CONTEXT BEFORE ERROR ---
    {context_before}

    --- CONTEXT AFTER ERROR ---
    {context_after}
""")

# ---------------------------------------------------------------------------
# Section parser
# ---------------------------------------------------------------------------

_SECTION_ALIASES: list[tuple[str, list[str]]] = [
    ("summary",         ["summary", "what went wrong"]),
    ("root_cause",      ["root_cause", "root cause"]),
    ("why_it_happened", ["why_it_happened", "why it happened", "why this happened"]),
    ("suggested_fix",   ["suggested_fix", "suggested fix", "immediate fix", "fix"]),
    ("prevention",      ["prevention", "prevention tips", "how to prevent"]),
]

_HEADER_RE = re.compile(
    r"(?:^|\n)"
    r"(?:\*{1,3}|#{1,3}\s*)?"
    r"([A-Za-z][A-Za-z _]+?)"
    r"(?:\*{1,3})?"
    r"\s*:?\s*"
    r"(?:\n|$)",
    re.MULTILINE,
)


def _normalise_label(raw: str) -> str:
    return re.sub(r"[\s_]+", " ", raw.strip().lower())


def _label_to_key(raw_label: str) -> Optional[str]:
    normalised = _normalise_label(raw_label)
    for key, aliases in _SECTION_ALIASES:
        if normalised in aliases:
            return key
    return None


def _parse_sections(text: str) -> dict[str, str]:
    result: dict[str, str] = {key: "" for key, _ in _SECTION_ALIASES}
    tagged: list[tuple[int, int, str]] = []

    for m in _HEADER_RE.finditer(text):
        key = _label_to_key(m.group(1))
        if key is None:
            continue
        tagged.append((m.start(), m.end(), key))

    if not tagged:
        result["summary"] = text.strip()
        return result

    for i, (_, content_start, key) in enumerate(tagged):
        next_start = tagged[i + 1][0] if i + 1 < len(tagged) else len(text)
        content = text[content_start:next_start].strip()
        if not result[key]:
            result[key] = content

    return result


# ---------------------------------------------------------------------------
# User-facing error messages keyed by error code
# ---------------------------------------------------------------------------

def _user_message(error_code: str, raw_message: str) -> dict:
    """Map an error code to a structured UI-friendly message dict."""

    if error_code == ERR_NO_KEY:
        return {
            "title":  "Groq API Key Not Configured",
            "detail": (
                "The `GROQ_API_KEY` environment variable is not set.\n\n"
                "**To fix this locally:**\n"
                "1. Copy `.env.example` to `.env`\n"
                "2. Set `GROQ_API_KEY=gsk_your_key_here` in `.env`\n"
                "3. Get a free key at [console.groq.com](https://console.groq.com)\n\n"
                "**On Render:** Dashboard → your service → *Environment* → "
                "Add `GROQ_API_KEY`."
            ),
            "action": "Get your free API key at [console.groq.com](https://console.groq.com)",
            "code":   error_code,
        }

    if error_code == ERR_AUTH:
        return {
            "title":  "Groq API — Authentication Failed (401)",
            "detail": (
                "The `GROQ_API_KEY` is invalid or has been revoked.\n\n"
                "**To fix this:**\n"
                "1. Go to [console.groq.com](https://console.groq.com)\n"
                "2. Generate a new API key\n"
                "3. Update your `.env` file or Render environment variable."
            ),
            "action": "Regenerate your key at [console.groq.com](https://console.groq.com)",
            "code":   error_code,
        }

    if error_code == ERR_PERMISSION:
        return {
            "title":  "Groq API — Permission Denied (403)",
            "detail": (
                "Your API key does not have permission for this request.\n\n"
                "**To fix this:**\n"
                "1. Go to [console.groq.com](https://console.groq.com)\n"
                "2. Check your API key scopes and account status\n"
                "3. Generate a new key if needed."
            ),
            "action": "Check your account at [console.groq.com](https://console.groq.com)",
            "code":   error_code,
        }

    if error_code == ERR_RATE_LIMIT:
        return {
            "title":  "Groq API — Rate Limit Hit (429)",
            "detail": (
                "The Groq free tier has per-minute token limits.\n\n"
                "**Options:**\n"
                "- Wait 30 seconds and click **Analyze** again\n"
                "- Reduce **Context lines** to send a smaller prompt\n"
                "- Tick **Skip LLM** to view the parsed log without AI"
            ),
            "action": None,
            "code":   error_code,
        }

    if error_code == ERR_CONNECTION:
        return {
            "title":  "Groq API — Connection Failed",
            "detail": (
                "Could not reach `api.groq.com`. "
                "Check your internet connection and try again."
            ),
            "action": None,
            "code":   error_code,
        }

    if error_code == ERR_TIMEOUT:
        return {
            "title":  "Groq API — Request Timed Out",
            "detail": "The model took too long to respond. Please try again.",
            "action": None,
            "code":   error_code,
        }

    return {
        "title":  "Groq API — Unexpected Error",
        "detail": raw_message,
        "action": None,
        "code":   error_code,
    }


# ---------------------------------------------------------------------------
# Mock fallback (used when API is unavailable)
# ---------------------------------------------------------------------------

def _mock_explanation(log_context: dict, model: str) -> dict:
    """Rule-based explanation when the API cannot be reached."""
    severity    = log_context.get("severity", "UNKNOWN")
    error_lines = log_context.get("error_block", [])
    first_line  = error_lines[0] if error_lines else "unknown error"
    n_lines     = log_context.get("total_lines", "?")
    err_idx     = log_context.get("error_line_index", "?")
    timestamp   = log_context.get("timestamp") or "not detected"

    return {
        "summary": (
            f"A **{severity}** level event was detected at line {err_idx} of {n_lines} "
            f"(timestamp: {timestamp}).\n\n"
            f"First error line: `{first_line[:200]}`"
        ),
        "root_cause": (
            "Full root cause analysis requires the Groq AI.\n\n"
            "Based on the error keywords:\n\n"
            + _heuristic_cause(first_line)
        ),
        "why_it_happened": (
            "Contextual analysis requires the Groq API. "
            "Review the **Context Before** section to understand what led to this error."
        ),
        "suggested_fix": (
            "**Immediate steps (without AI):**\n\n"
            "1. Review the **Raw Error Block** below for the full error message\n"
            "2. Check **Context Before** — the triggering event is usually there\n"
            "3. Search your codebase or issue tracker for this error message\n"
            "4. Check system resources (disk, memory, network) if relevant\n\n"
            "**To get AI-powered suggestions:** resolve the API issue above and re-run."
        ),
        "prevention": (
            "Enable full AI analysis by resolving the Groq API issue above.\n\n"
            "General best practices:\n\n"
            "- Add structured logging with severity levels\n"
            "- Set up alerts for ERROR/CRITICAL events\n"
            "- Review this log section with your team"
        ),
        "raw_llm_response": "",
        "model":    f"{model} (not called — API unavailable)",
        "error":    None,
        "is_mock":  True,
    }


def _heuristic_cause(first_line: str) -> str:
    """Keyword-based root cause hint for the mock fallback."""
    line = first_line.lower()
    if any(k in line for k in ("connection", "timeout", "refused", "unreachable")):
        return "Likely a **network or service connectivity issue** — a downstream service may be unreachable."
    if any(k in line for k in ("memory", "oom", "heap", "out of memory")):
        return "Likely an **out-of-memory condition** — the process exhausted available RAM."
    if any(k in line for k in ("permission", "access denied", "unauthorized", "forbidden")):
        return "Likely an **authentication or permissions issue** — check credentials and access controls."
    if any(k in line for k in ("disk", "no space", "i/o error", "filesystem")):
        return "Likely a **disk I/O or storage issue** — check available disk space."
    if any(k in line for k in ("null", "nonetype", "attribute", "has no attribute")):
        return "Likely a **null reference or missing attribute** — an object was None when a value was expected."
    if any(k in line for k in ("syntax", "parse", "invalid", "decode")):
        return "Likely a **configuration or input parsing error** — check config files and input data."
    return "Review the raw error block below to identify the specific failure."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_anomaly(
    log_context: dict,
    model: str = _DEFAULT_MODEL,
    use_mock_on_failure: bool = True,
) -> dict:
    """Send a parsed log-error context to the Groq API for analysis.

    Parameters
    ----------
    log_context:
        Dict returned by ``find_error_block()``. Must have ``found=True``.
    model:
        Groq model tag. Defaults to ``llama-3.3-70b-versatile``.
    use_mock_on_failure:
        When True (default) and the API fails, return a rule-based mock
        instead of a bare error so the rest of the pipeline still works.

    Returns
    -------
    dict with keys:
        summary, root_cause, why_it_happened, suggested_fix, prevention,
        raw_llm_response, model, error, is_mock, [api_error_info].

        ``error``          — None on success or mock; message string on hard failure.
        ``is_mock``        — True when mock content was substituted.
        ``api_error_info`` — structured dict (title/detail/action/code) when is_mock=True.
    """
    if not log_context.get("found", False):
        return _error_result(
            "No error block found in log context. "
            "Ensure find_error_block() returned found=True.",
            model=model,
        )

    error_block    = "\n".join(log_context.get("error_block",    []))
    context_before = "\n".join(log_context.get("context_before", []))
    context_after  = "\n".join(log_context.get("context_after",  []))

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        severity         = log_context.get("severity",         "UNKNOWN"),
        timestamp        = log_context.get("timestamp")        or "not available",
        log_path         = log_context.get("log_path",         "unknown"),
        error_line_index = log_context.get("error_line_index", "?"),
        total_lines      = log_context.get("total_lines",      "?"),
        error_block      = error_block      or "(no error block captured)",
        context_before   = context_before   or "(no preceding context)",
        context_after    = context_after    or "(no following context)",
    )

    raw, error_code, raw_error_msg = call_llm(
        system_prompt = _SYSTEM_PROMPT,
        user_prompt   = user_prompt,
        model         = model,
        temperature   = 0.3,
    )

    if error_code:
        if use_mock_on_failure:
            mock = _mock_explanation(log_context, model)
            mock["api_error_info"] = _user_message(error_code, raw_error_msg or "")
            return mock
        msg_dict = _user_message(error_code, raw_error_msg or "")
        return _error_result(f"{msg_dict['title']}: {msg_dict['detail']}", model=model)

    sections = _parse_sections(raw)
    return {
        **sections,
        "raw_llm_response": raw,
        "model":            model,
        "error":            None,
        "is_mock":          False,
    }


def _error_result(message: str, model: str = "") -> dict:
    return {
        "summary":          "",
        "root_cause":       "",
        "why_it_happened":  "",
        "suggested_fix":    "",
        "prevention":       "",
        "raw_llm_response": "",
        "model":            model,
        "error":            message,
        "is_mock":          False,
    }
