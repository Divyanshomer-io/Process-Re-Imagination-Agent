"""LLM client using DAIA as the sole backend.

The DAIA (Data AI Accelerator) endpoint uses a custom token-based auth flow:
1. POST client_id/client_secret to generate a Bearer token.
2. Use the Bearer token to call the chat completions API.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from process_reimagination_agent.config import Settings

_logger = logging.getLogger(__name__)

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}
_token_lock = threading.Lock()

_DAIA_AUTH_PATH = "/authentication-service/api/v1/auth/generate-token"
_DAIA_CHAT_PATH = "/model-as-a-service/chat/completions"
_TOKEN_TTL_SECONDS = 1800  # refresh every 30 min to stay ahead of expiry


def _generate_daia_token(settings: Settings) -> str:
    """Obtain a Bearer token from the DAIA auth endpoint.

    Tokens are cached in-process and refreshed when the TTL expires or
    when a 401 is encountered on a chat call.
    """
    with _token_lock:
        now = time.time()
        if _token_cache["token"] and now < _token_cache["expires_at"]:
            return _token_cache["token"]

        url = f"{settings.daia_base_url.rstrip('/')}{_DAIA_AUTH_PATH}"
        payload = {
            "client_id": settings.daia_client_id,
            "client_secret": settings.daia_client_secret,
        }
        resp = requests.post(url, json=payload, timeout=30, verify=False)
        resp.raise_for_status()
        token = resp.json()["token"]
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + _TOKEN_TTL_SECONDS
        return token


def _invalidate_daia_token() -> None:
    with _token_lock:
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0.0


_DAIA_CONNECT_TIMEOUT = 30
_DAIA_READ_TIMEOUT = 300


_DAIA_DEFAULT_MAX_TOKENS = 100000


def _call_daia(
    prompt: str,
    settings: Settings,
    *,
    system_message: str | None = None,
    max_tokens: int | None = None,
) -> str | None:
    """Call the DAIA chat completions endpoint with automatic token retry."""
    messages: list[dict[str, str]] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    url = f"{settings.daia_base_url.rstrip('/')}{_DAIA_CHAT_PATH}"
    effective_max_tokens = max_tokens if max_tokens is not None else _DAIA_DEFAULT_MAX_TOKENS
    # Strict: GPT-5 only — no other model or fallback
    body: dict[str, Any] = {
        "model": "gpt-5",
        "messages": messages,
        "max_tokens": effective_max_tokens,
        "temperature": settings.model_temperature,
    }

    for attempt in range(2):
        token = _generate_daia_token(settings)
        headers = {"Authorization": f"Bearer {token}"}
        _logger.info("DAIA request: model=gpt-5 (strict), max_tokens=%s, temperature=%s, attempt=%d", body["max_tokens"], body["temperature"], attempt + 1)
        resp = requests.post(
            url,
            json=body,
            headers=headers,
            timeout=(_DAIA_CONNECT_TIMEOUT, _DAIA_READ_TIMEOUT),
            verify=False,
        )
        if resp.status_code == 401 and attempt == 0:
            _logger.warning("DAIA token expired, refreshing and retrying")
            _invalidate_daia_token()
            continue
        resp.raise_for_status()
        data = resp.json()

        choices = data.get("choices") or []
        if not choices:
            _logger.warning(
                "DAIA returned no choices. Response keys: %s, usage: %s",
                list(data.keys()),
                data.get("usage"),
            )
            _logger.debug("DAIA raw response (no choices): %s", data)
            return None
        first = choices[0]
        message = first.get("message") or first
        content = message.get("content") if isinstance(message.get("content"), str) else message.get("text")
        if content is None or (isinstance(content, str) and not content.strip()):
            _logger.warning(
                "DAIA returned null/empty content. finish_reason=%s, message keys=%s",
                first.get("finish_reason"),
                list(message.keys()) if isinstance(message, dict) else None,
            )
            _logger.debug("DAIA raw response (empty content): %s", data)
        return (content or "").strip() or None

    return None


class LLMNotConfiguredError(RuntimeError):
    """Raised when no LLM backend is configured and a call is attempted."""


_DAIA_CALL_RETRIES = 3
_DAIA_RETRY_BACKOFF = 5


def call_llm(
    prompt: str,
    settings: Settings,
    *,
    system_message: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Send *prompt* to the configured DAIA LLM backend and return the reply.

    Retries up to ``_DAIA_CALL_RETRIES`` times on transient failures.
    Raises ``LLMNotConfiguredError`` when no backend is configured.
    Raises ``RuntimeError`` when all attempts fail.
    """
    if not settings.daia_enabled:
        raise LLMNotConfiguredError(
            "No LLM backend is configured. Set DAIA_CLIENT_ID and "
            "DAIA_CLIENT_SECRET in your .env file or environment variables."
        )

    # Strict: only GPT-5 is used; override any other model setting
    if settings.daia_model != "gpt-5":
        _logger.warning("Enforcing model=gpt-5 (was %s); all outputs from GPT-5 only", settings.daia_model)

    prompt_preview = prompt[:80].replace("\n", " ")
    print(f"  [LLM] call_llm invoked (prompt: {len(prompt)} chars, max_tokens: {max_tokens}) -- \"{prompt_preview}...\"")

    errors_encountered: list[str] = []

    for attempt in range(1, _DAIA_CALL_RETRIES + 1):
        try:
            result = _call_daia(prompt, settings, system_message=system_message, max_tokens=max_tokens)
            if result:
                print(f"  [LLM] Response received via DAIA ({len(result)} chars)")
                _logger.info("LLM response received via DAIA endpoint")
                return result
            errors_encountered.append(f"DAIA returned empty response (attempt {attempt})")
            _logger.warning("DAIA returned empty response (attempt %d/%d)", attempt, _DAIA_CALL_RETRIES)
        except Exception as exc:
            errors_encountered.append(f"DAIA (attempt {attempt}): {exc}")
            action = "retrying" if attempt < _DAIA_CALL_RETRIES else "giving up"
            print(f"  [LLM] DAIA failed (attempt {attempt}/{_DAIA_CALL_RETRIES}), {action}: {exc}")
            _logger.warning("DAIA call failed (attempt %d/%d), %s: %s", attempt, _DAIA_CALL_RETRIES, action, exc)

        if attempt < _DAIA_CALL_RETRIES:
            wait = _DAIA_RETRY_BACKOFF * attempt
            _logger.info("Waiting %ds before retry...", wait)
            time.sleep(wait)

    error_detail = "; ".join(errors_encountered)
    print(f"  [LLM] ALL ATTEMPTS FAILED: {error_detail}")
    raise RuntimeError(f"All DAIA LLM attempts failed. Errors: {error_detail}")
