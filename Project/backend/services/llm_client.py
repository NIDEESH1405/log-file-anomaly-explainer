"""
services/llm_client.py
----------------------
Thin wrapper around the Groq API using the OpenAI-compatible client.

Public API
~~~~~~~~~~
    call_llm(system_prompt, user_prompt, model, temperature, max_retries)
        -> (text, error_code, error_message)
    check_api_key() -> (is_set: bool, error_message: str | None)

Retry behaviour
~~~~~~~~~~~~~~~
Transient errors (connection failure, timeout, rate-limit) are retried
with exponential backoff.  Permanent errors (401, 403, missing key) are
returned immediately — retrying them would never succeed.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Optional

# _ENV_FILE is always defined so check_api_key() can reference it safely.
_HERE         = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parent.parent.parent
_ENV_FILE     = _PROJECT_ROOT / ".env"

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_ENV_FILE, override=False)
except ImportError:
    # python-dotenv not installed — on Render, env vars are injected natively.
    pass

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL      = "https://api.groq.com/openai/v1"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Error codes — UI and explainer branch on these, never on raw strings
ERR_NO_KEY     = "NO_KEY"
ERR_AUTH       = "AUTH_FAILED"
ERR_PERMISSION = "PERMISSION_DENIED"    # 403
ERR_CONNECTION = "CONNECTION_FAILED"
ERR_TIMEOUT    = "TIMEOUT"
ERR_RATE_LIMIT = "RATE_LIMIT"           # 429 — common on Groq free tier
ERR_API        = "API_ERROR"
ERR_UNKNOWN    = "UNKNOWN"

# Only transient errors are worth retrying
_RETRYABLE = {ERR_CONNECTION, ERR_TIMEOUT, ERR_RATE_LIMIT}

# Retry tuning
_MAX_RETRIES     = 3      # extra attempts after first failure (4 total)
_BACKOFF_BASE    = 2.0    # seconds; doubles each retry: 2 → 4 → 8
_RATE_LIMIT_WAIT = 30.0   # Groq 429s clear faster than xAI — 30s is enough


# ---------------------------------------------------------------------------
# Startup helper
# ---------------------------------------------------------------------------

def check_api_key() -> tuple[bool, Optional[str]]:
    """Return (True, None) if GROQ_API_KEY is set, else (False, message)."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if key:
        return True, None
    return False, f"GROQ_API_KEY is not set. Looked for .env at: {_ENV_FILE}"


# ---------------------------------------------------------------------------
# Internal: single attempt
# ---------------------------------------------------------------------------

def _attempt(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> tuple[str, Optional[str], Optional[str]]:
    """Make one API call. Returns (text, error_code, error_msg)."""
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=temperature,
        )
        text = (completion.choices[0].message.content or "").strip()
        return (text, None, None)

    except AuthenticationError:
        return ("", ERR_AUTH,
                "Groq API key is invalid or revoked (401).")

    except PermissionDeniedError:
        return ("", ERR_PERMISSION,
                "Groq API returned 403 — check your API key permissions.")

    except APIConnectionError as exc:
        return ("", ERR_CONNECTION,
                f"Could not reach api.groq.com — {exc}")

    except APITimeoutError:
        return ("", ERR_TIMEOUT,
                "Groq API request timed out.")

    except APIStatusError as exc:
        if exc.status_code == 401:
            return ("", ERR_AUTH,
                    "Groq API key is invalid or revoked (401).")
        if exc.status_code == 403:
            return ("", ERR_PERMISSION,
                    "Groq API returned 403 — check your API key permissions.")
        if exc.status_code == 429:
            return ("", ERR_RATE_LIMIT,
                    "Groq API rate limit exceeded (429) — free tier has per-minute limits.")
        return ("", ERR_API,
                f"Groq API HTTP {exc.status_code}: {exc.message}")

    except Exception as exc:  # noqa: BLE001
        return ("", ERR_UNKNOWN, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.3,
    max_retries: int = _MAX_RETRIES,
) -> tuple[str, Optional[str], Optional[str]]:
    """Send a chat request to the Groq API with automatic retry.

    Transient errors (connection failure, timeout, rate-limit 429) are
    retried with exponential backoff.  Permanent errors (401, 403, missing
    key) are returned immediately.

    Parameters
    ----------
    system_prompt, user_prompt:
        Chat messages sent to the model.
    model:
        Groq model tag. Defaults to ``llama-3.3-70b-versatile``.
    temperature:
        Sampling temperature (0 = deterministic).
    max_retries:
        Extra attempts after first failure (default 3, 4 total).
        Pass 0 to disable retry.

    Returns
    -------
    (response_text, error_code, error_message)
        Success : (text,  None,    None)
        Failure : ("",    ERR_*,   human-readable message)
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return ("", ERR_NO_KEY, "GROQ_API_KEY is not configured.")

    client = OpenAI(api_key=api_key, base_url=_BASE_URL)

    last_code: Optional[str] = None
    last_msg:  Optional[str] = None
    total_attempts = max_retries + 1

    for attempt in range(1, total_attempts + 1):
        text, code, msg = _attempt(client, model, system_prompt, user_prompt, temperature)

        # ── Success ───────────────────────────────────────────
        if code is None:
            if attempt > 1:
                logger.info("Groq API succeeded on attempt %d/%d.", attempt, total_attempts)
            return (text, None, None)

        last_code, last_msg = code, msg

        # ── Permanent error — never retry ─────────────────────
        if code not in _RETRYABLE:
            logger.warning("Groq API permanent error [%s]: %s", code, msg)
            return ("", code, msg)

        # ── Transient — retry if attempts remain ──────────────
        if attempt >= total_attempts:
            break

        wait = _RATE_LIMIT_WAIT if code == ERR_RATE_LIMIT else _BACKOFF_BASE ** attempt
        logger.warning(
            "Groq API transient error [%s] on attempt %d/%d — retrying in %.0fs.",
            code, attempt, total_attempts, wait,
        )
        time.sleep(wait)

    logger.error(
        "Groq API failed after %d attempt(s) [%s]: %s",
        total_attempts, last_code, last_msg,
    )
    return ("", last_code, last_msg)


# ---------------------------------------------------------------------------
# Backward-compat alias (call_grok → call_llm)
# Any code that still calls call_grok() keeps working unchanged.
# ---------------------------------------------------------------------------
call_grok = call_llm
