"""Unified LLM client with DAIA as primary backend and Azure/OpenAI as fallbacks.

The DAIA (Data AI Accelerator) endpoint uses a custom token-based auth flow:
1. POST client_id/client_secret to generate a Bearer token.
2. Use the Bearer token to call the chat completions API.

When DAIA is unavailable, the client falls back to Azure OpenAI SDK and then
plain OpenAI SDK, matching the previous behaviour.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import requests

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
        resp = requests.post(url, json=payload, timeout=30, verify=settings.daia_verify_ssl)
        resp.raise_for_status()
        token = resp.json()["token"]
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + _TOKEN_TTL_SECONDS
        return token


def _invalidate_daia_token() -> None:
    with _token_lock:
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0.0


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
    body: dict[str, Any] = {
        "model": settings.daia_model,
        "messages": messages,
        "temperature": settings.model_temperature,
    }
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    for attempt in range(2):
        token = _generate_daia_token(settings)
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(
            url, json=body, headers=headers, timeout=120, verify=settings.daia_verify_ssl,
        )
        if resp.status_code == 401 and attempt == 0:
            _logger.warning("DAIA token expired, refreshing and retrying")
            _invalidate_daia_token()
            continue
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    return None


def _call_azure_openai(
    prompt: str,
    settings: Settings,
    *,
    system_message: str | None = None,
    max_tokens: int | None = None,
) -> str | None:
    try:
        from openai import AzureOpenAI  # type: ignore[import-untyped]
    except ImportError:
        return None

    messages: list[dict[str, str]] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
    kwargs: dict[str, Any] = {
        "model": settings.azure_openai_deployment,
        "temperature": settings.model_temperature,
        "messages": messages,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    response = client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
    return response.choices[0].message.content


def _call_openai(
    prompt: str,
    settings: Settings,
    *,
    system_message: str | None = None,
    max_tokens: int | None = None,
) -> str | None:
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError:
        return None

    messages: list[dict[str, str]] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    client = OpenAI(api_key=settings.openai_api_key)
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "temperature": settings.model_temperature,
        "messages": messages,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    response = client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
    return response.choices[0].message.content


class LLMNotConfiguredError(RuntimeError):
    """Raised when no LLM backend is configured and a call is attempted."""


def call_llm(
    prompt: str,
    settings: Settings,
    *,
    system_message: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Send *prompt* to the best available LLM backend and return the reply.

    Priority: DAIA (primary) -> Azure OpenAI (fallback) -> OpenAI (fallback).
    Raises ``LLMNotConfiguredError`` when no backend is configured.
    Raises ``RuntimeError`` when all configured backends fail.
    """
    if not settings.any_llm_configured:
        raise LLMNotConfiguredError(
            "No LLM backend is configured. Set DAIA_CLIENT_ID/DAIA_CLIENT_SECRET, "
            "AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY, or OPENAI_API_KEY in your "
            ".env file or environment variables."
        )

    errors_encountered: list[str] = []

    if settings.daia_enabled:
        try:
            result = _call_daia(prompt, settings, system_message=system_message, max_tokens=max_tokens)
            if result:
                _logger.info("LLM response received via DAIA endpoint")
                return result
            errors_encountered.append("DAIA returned empty response")
        except Exception as exc:
            errors_encountered.append(f"DAIA: {exc}")
            _logger.warning("DAIA call failed, trying fallback: %s", exc)

    if settings.azure_enabled:
        try:
            result = _call_azure_openai(prompt, settings, system_message=system_message, max_tokens=max_tokens)
            if result:
                _logger.info("LLM response received via Azure OpenAI")
                return result
            errors_encountered.append("Azure OpenAI returned empty response")
        except Exception as exc:
            errors_encountered.append(f"Azure OpenAI: {exc}")
            _logger.warning("Azure OpenAI call failed: %s", exc)

    if settings.openai_enabled:
        try:
            result = _call_openai(prompt, settings, system_message=system_message, max_tokens=max_tokens)
            if result:
                _logger.info("LLM response received via OpenAI")
                return result
            errors_encountered.append("OpenAI returned empty response")
        except Exception as exc:
            errors_encountered.append(f"OpenAI: {exc}")
            _logger.warning("OpenAI call failed: %s", exc)

    error_detail = "; ".join(errors_encountered)
    raise RuntimeError(
        f"All configured LLM backends failed. Errors: {error_detail}"
    )
