"""Tests for the DAIA LLM client with mocked HTTP calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from process_reimagination_agent.config import Settings
from process_reimagination_agent.llm_client import (
    _invalidate_daia_token,
    call_llm,
)


@pytest.fixture(autouse=True)
def _clear_token_cache() -> None:
    _invalidate_daia_token()


def _daia_settings() -> Settings:
    return Settings(
        daia_client_id="test-client-id",
        daia_client_secret="test-client-secret",
        daia_base_url="https://daia.test.example.com",
        daia_model="gpt-5",
    )


def test_call_llm_returns_none_when_no_backend_configured() -> None:
    result = call_llm("Hello", Settings())
    assert result is None


@patch("process_reimagination_agent.llm_client.requests.post")
def test_call_llm_daia_success(mock_post: MagicMock) -> None:
    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.json.return_value = {"token": "test-bearer-token"}
    token_resp.raise_for_status = MagicMock()

    chat_resp = MagicMock()
    chat_resp.status_code = 200
    chat_resp.json.return_value = {
        "choices": [{"message": {"content": "LLM says hello"}}]
    }
    chat_resp.raise_for_status = MagicMock()

    mock_post.side_effect = [token_resp, chat_resp]

    result = call_llm("Hello", _daia_settings())
    assert result == "LLM says hello"
    assert mock_post.call_count == 2

    auth_call = mock_post.call_args_list[0]
    assert "/generate-token" in str(auth_call)
    chat_call = mock_post.call_args_list[1]
    assert "/chat/completions" in str(chat_call)
    assert "Bearer test-bearer-token" in str(chat_call)


@patch("process_reimagination_agent.llm_client.requests.post")
def test_call_llm_daia_token_retry_on_401(mock_post: MagicMock) -> None:
    token_resp_1 = MagicMock()
    token_resp_1.status_code = 200
    token_resp_1.json.return_value = {"token": "expired-token"}
    token_resp_1.raise_for_status = MagicMock()

    expired_chat = MagicMock()
    expired_chat.status_code = 401

    token_resp_2 = MagicMock()
    token_resp_2.status_code = 200
    token_resp_2.json.return_value = {"token": "fresh-token"}
    token_resp_2.raise_for_status = MagicMock()

    good_chat = MagicMock()
    good_chat.status_code = 200
    good_chat.json.return_value = {
        "choices": [{"message": {"content": "Retried OK"}}]
    }
    good_chat.raise_for_status = MagicMock()

    mock_post.side_effect = [token_resp_1, expired_chat, token_resp_2, good_chat]

    result = call_llm("Hello", _daia_settings())
    assert result == "Retried OK"


@patch("process_reimagination_agent.llm_client.requests.post")
def test_call_llm_daia_failure_returns_none(mock_post: MagicMock) -> None:
    mock_post.side_effect = Exception("Network error")
    result = call_llm("Hello", _daia_settings())
    assert result is None


def test_call_llm_with_system_message_no_backend() -> None:
    result = call_llm("Hello", Settings(), system_message="You are helpful.")
    assert result is None
