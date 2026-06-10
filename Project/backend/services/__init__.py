# backend/services package
# Re-export everything from llm_client so both import styles work:
#   from backend.services.llm_client import ...
#   from backend.services import ...

from backend.services.llm_client import (
    call_llm,
    call_grok,          # backward-compat alias
    check_api_key,
    ERR_NO_KEY,
    ERR_AUTH,
    ERR_PERMISSION,
    ERR_CONNECTION,
    ERR_TIMEOUT,
    ERR_RATE_LIMIT,
    ERR_API,
    ERR_UNKNOWN,
    _DEFAULT_MODEL,
)

__all__ = [
    "call_llm",
    "call_grok",
    "check_api_key",
    "ERR_NO_KEY",
    "ERR_AUTH",
    "ERR_PERMISSION",
    "ERR_CONNECTION",
    "ERR_TIMEOUT",
    "ERR_RATE_LIMIT",
    "ERR_API",
    "ERR_UNKNOWN",
    "_DEFAULT_MODEL",
]
