"""Tests for ppt_common.llm module."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from ppt_common.llm import LLMClient, parse_llm_json


class TestParseLlmJson:
    """Tests for parse_llm_json() function."""

    def test_valid_json(self):
        """Valid JSON should be parsed correctly."""
        result = parse_llm_json('{"a": 1, "b": "test"}')
        assert result == {"a": 1, "b": "test"}

    def test_json_with_code_fences(self):
        """JSON wrapped in markdown code fences should be parsed."""
        raw = '```json\n{"key": "value"}\n```'
        result = parse_llm_json(raw)
        assert result == {"key": "value"}

    def test_json_with_plain_fences(self):
        """JSON wrapped in plain code fences should be parsed."""
        raw = '```\n{"key": "value"}\n```'
        result = parse_llm_json(raw)
        assert result == {"key": "value"}

    def test_json_with_uppercase_fence(self):
        """JSON with uppercase JSON fence should be parsed."""
        raw = '```JSON\n{"key": "value"}\n```'
        result = parse_llm_json(raw)
        assert result == {"key": "value"}

    def test_invalid_json(self):
        """Invalid JSON should return None."""
        assert parse_llm_json("not json") is None

    def test_empty_string(self):
        """Empty string should return None."""
        assert parse_llm_json("") is None

    def test_none_input(self):
        """None input should return None."""
        assert parse_llm_json(None) is None

    def test_json_array(self):
        """JSON array should return None (we only accept dicts)."""
        assert parse_llm_json('[1, 2, 3]') is None

    def test_nested_json(self):
        """Nested JSON should be parsed correctly."""
        raw = '{"outer": {"inner": [1, 2, 3]}}'
        result = parse_llm_json(raw)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_whitespace_handling(self):
        """Leading/trailing whitespace should be handled."""
        result = parse_llm_json('  \n  {"key": "value"}  \n  ')
        assert result == {"key": "value"}


class TestLLMClient:
    """Tests for LLMClient class."""

    def test_init_defaults(self):
        """Client should initialize with defaults."""
        # clear=True: ambient env (e.g. backend/.env loaded by Django settings)
        # must not leak real keys into a defaults test
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient()
            assert client.api_key == ""
            assert "dashscope" in client.base_url
            assert client.model == "qwen-plus"
            assert client.is_available is False

    def test_init_with_api_key(self):
        """Client should accept explicit API key."""
        client = LLMClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.is_available is True

    def test_init_with_custom_params(self):
        """Client should accept custom parameters."""
        client = LLMClient(
            api_key="key",
            base_url="http://custom.api",
            model="gpt-4",
            timeout=120,
        )
        assert client.api_key == "key"
        assert client.base_url == "http://custom.api"
        assert client.model == "gpt-4"

    @patch.dict(os.environ, {"DASHSCOPE_API_KEY": "env-key"})
    def test_init_from_env(self):
        """Client should read API key from environment."""
        client = LLMClient()
        assert client.api_key == "env-key"
        assert client.is_available is True

    @patch.dict(os.environ, {"LLM_API_KEY": "llm-key"}, clear=True)
    def test_init_from_llm_env(self):
        """Client should read from LLM_API_KEY as fallback."""
        client = LLMClient()
        assert client.api_key == "llm-key"

    def test_is_available_false_without_key(self):
        """Client should not be available without API key."""
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient()
            assert client.is_available is False

    def test_client_property_raises_without_key(self):
        """Accessing client without API key should raise RuntimeError."""
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient()
            with pytest.raises(RuntimeError, match="No API key configured"):
                _ = client.client

    def test_client_property_creates_openai_client(self):
        """Client property should create OpenAI client on first access."""
        client = LLMClient(api_key="test-key")
        
        # Directly set the _client to a mock (bypass lazy init)
        mock_openai_client = MagicMock()
        client._client = mock_openai_client
        
        # Access client property should return the mock
        result = client.client
        assert result == mock_openai_client

    @patch.dict(os.environ, {"ALL_PROXY": "http://proxy:8080"})
    def test_proxy_env_handling(self):
        """Client should handle proxy env vars."""
        # Just verify the env var is set and client can be created
        assert "ALL_PROXY" in os.environ
        client = LLMClient(api_key="test-key")
        assert client.is_available is True

    def test_chat_method(self):
        """Chat method should call OpenAI API."""
        client = LLMClient(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Directly set _client
        client._client = mock_openai_client
        
        result = client.chat("Hello", system="You are helpful")
        
        assert result == "Test response"
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_chat_method_error_handling(self):
        """Chat method should handle errors gracefully."""
        client = LLMClient(api_key="test-key")
        
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Directly set _client
        client._client = mock_openai_client
        
        result = client.chat("Hello")
        assert result == ""

    def test_chat_json_method(self):
        """Chat JSON method should parse response."""
        client = LLMClient(api_key="test-key")
        
        # Mock the chat method directly
        with patch.object(LLMClient, 'chat', return_value='{"key": "value"}'):
            result = client.chat_json("Give me JSON")
            assert result == {"key": "value"}

    def test_chat_json_method_invalid(self):
        """Chat JSON method should return None for invalid JSON."""
        client = LLMClient(api_key="test-key")
        
        with patch.object(LLMClient, 'chat', return_value='not json'):
            result = client.chat_json("Give me JSON")
            assert result is None

    def test_chat_retries_on_429(self):
        """Chat should retry on 429 rate limit errors."""
        from openai import APIStatusError
        from httpx import Response, Request

        client = LLMClient(api_key="test-key")
        mock_openai_client = MagicMock()

        # First two calls fail with 429, third succeeds
        error_429 = APIStatusError(
            message="Rate limit exceeded",
            response=Response(429, request=Request("POST", "https://test")),
            body={"error": "rate_limit"},
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retry"

        mock_openai_client.chat.completions.create.side_effect = [
            error_429,
            error_429,
            mock_response,
        ]
        client._client = mock_openai_client

        with patch('ppt_common.llm.time.sleep'):
            result = client.chat("Hello", max_retries=3)

        assert result == "Success after retry"
        assert mock_openai_client.chat.completions.create.call_count == 3

    def test_chat_retries_on_500(self):
        """Chat should retry on 500 server errors."""
        from openai import APIStatusError
        from httpx import Response, Request

        client = LLMClient(api_key="test-key")
        mock_openai_client = MagicMock()

        error_500 = APIStatusError(
            message="Internal server error",
            response=Response(500, request=Request("POST", "https://test")),
            body={"error": "server_error"},
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Recovered"

        mock_openai_client.chat.completions.create.side_effect = [error_500, mock_response]
        client._client = mock_openai_client

        with patch('ppt_common.llm.time.sleep'):
            result = client.chat("Hello", max_retries=2)

        assert result == "Recovered"
        assert mock_openai_client.chat.completions.create.call_count == 2

    def test_chat_no_retry_on_401(self):
        """Chat should NOT retry on 401 authentication errors."""
        from openai import APIStatusError
        from httpx import Response, Request

        client = LLMClient(api_key="bad-key")
        mock_openai_client = MagicMock()

        error_401 = APIStatusError(
            message="Invalid API key",
            response=Response(401, request=Request("POST", "https://test")),
            body={"error": "invalid_api_key"},
        )
        mock_openai_client.chat.completions.create.side_effect = error_401
        client._client = mock_openai_client

        result = client.chat("Hello", max_retries=3)

        assert result == ""
        assert mock_openai_client.chat.completions.create.call_count == 1

    def test_chat_max_retries_exhausted(self):
        """Chat should return empty after max retries exhausted."""
        from openai import APIStatusError
        from httpx import Response, Request

        client = LLMClient(api_key="test-key")
        mock_openai_client = MagicMock()

        error_429 = APIStatusError(
            message="Rate limit exceeded",
            response=Response(429, request=Request("POST", "https://test")),
            body={"error": "rate_limit"},
        )
        mock_openai_client.chat.completions.create.side_effect = error_429
        client._client = mock_openai_client

        with patch('ppt_common.llm.time.sleep'):
            result = client.chat("Hello", max_retries=2)

        assert result == ""
        assert mock_openai_client.chat.completions.create.call_count == 3  # initial + 2 retries

    def test_sdk_client_disables_internal_retries(self):
        """The lazily-built OpenAI client must disable SDK-internal retries.

        SDK retries silently re-run stalled reads, tripling the wall time of
        a hung-gateway call before _complete's retry policy sees the error.
        """
        client = LLMClient(api_key="test-key")
        assert client.client.max_retries == 0

    def test_hung_gateway_respects_retry_budget(self):
        """A gateway that accepts but never responds must consume exactly the
        ppt-level retry budget — one HTTP attempt per _complete attempt.

        With SDK-internal retries enabled this opens 6 connections
        (2 ppt attempts x 3 SDK attempts) and burns ~6x the timeout.
        """
        import socket
        import threading
        import time as time_mod

        connections = []

        def accept_loop(server):
            while True:
                try:
                    conn, _ = server.accept()
                    conn.recv(65536)  # read request, never respond -> read timeout
                    connections.append(conn)
                except OSError:
                    return

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(8)
        port = server.getsockname()[1]
        threading.Thread(target=accept_loop, args=(server,), daemon=True).start()

        try:
            client = LLMClient(
                api_key="test-key",
                base_url=f"http://127.0.0.1:{port}/v1",
                timeout=1,
            )
            start = time_mod.monotonic()
            with patch('ppt_common.llm.time.sleep'):
                result = client.chat("Hello")  # default max_retries=1 -> 2 ppt attempts
            elapsed = time_mod.monotonic() - start

            assert result == ""
            assert len(connections) == 2  # one HTTP attempt per ppt attempt
            assert elapsed < 15  # bounded, not 6x the timeout
        finally:
            server.close()
            for conn in connections:
                conn.close()


TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
    "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class TestChatWithImages:
    """Multimodal channel for visual QC and template analysis."""

    def _client_with_mock(self):
        client = LLMClient(api_key="test-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "review result"
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = mock_response
        client._client = mock_openai_client
        return client, mock_openai_client

    def test_sends_multimodal_content_parts(self, tmp_path):
        import base64

        img = tmp_path / "slide.png"
        img.write_bytes(base64.b64decode(TINY_PNG_B64))
        client, mock_client = self._client_with_mock()

        result = client.chat_with_images("review this slide", [img],
                                         system="qc reviewer")
        assert result == "review result"

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = kwargs["messages"]
        assert messages[0]["role"] == "system"
        user_content = messages[-1]["content"]
        assert user_content[0] == {"type": "text", "text": "review this slide"}
        assert user_content[1]["type"] == "image_url"
        assert user_content[1]["image_url"]["url"].startswith(
            "data:image/png;base64,")

    def test_multiple_images_in_order(self, tmp_path):
        import base64

        imgs = []
        for i in range(3):
            p = tmp_path / f"{i}.png"
            p.write_bytes(base64.b64decode(TINY_PNG_B64))
            imgs.append(p)
        client, mock_client = self._client_with_mock()
        client.chat_with_images("review", imgs)
        content = mock_client.chat.completions.create.call_args.kwargs[
            "messages"][-1]["content"]
        assert len(content) == 4  # 1 text + 3 images

    def test_missing_image_raises(self, tmp_path):
        client, _ = self._client_with_mock()
        with pytest.raises(FileNotFoundError):
            client.chat_with_images("review", [tmp_path / "nope.png"])

    def test_error_returns_empty(self, tmp_path):
        import base64

        img = tmp_path / "s.png"
        img.write_bytes(base64.b64decode(TINY_PNG_B64))
        client = LLMClient(api_key="test-key")
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = Exception("boom")
        client._client = mock_openai_client
        assert client.chat_with_images("review", [img]) == ""


# ---------------------------------------------------------------------------
# Celery task-timeout exceptions must propagate, never be swallowed
# ---------------------------------------------------------------------------


class SoftTimeLimitExceeded(Exception):
    """Name-match stand-in for celery.exceptions.SoftTimeLimitExceeded.

    ppt_common matches these by class name (and cause chain) so it carries
    no celery dependency; the tests therefore don't need one either.
    """


class TimeLimitExceeded(Exception):
    """Name-match stand-in for celery.exceptions.TimeLimitExceeded."""


class TestCeleryTimeoutPropagation:
    """A worker soft-limit signal lands inside the blocking LLM
    read; the openai SDK wraps it (APIConnectionError "Connection error.").
    _complete must re-raise it instead of returning "", otherwise the task
    sails past the soft limit until the hard limit SIGKILLs the worker.
    """

    def test_chain_walker_finds_direct_timeout(self):
        from ppt_common.llm import celery_timeout_in_chain
        exc = SoftTimeLimitExceeded()
        assert celery_timeout_in_chain(exc) is exc

    def test_chain_walker_finds_wrapped_timeout(self):
        from ppt_common.llm import celery_timeout_in_chain
        inner = TimeLimitExceeded()
        try:
            try:
                raise inner
            except TimeLimitExceeded:
                raise RuntimeError("wrapped")  # sets __context__
        except RuntimeError as outer:
            found = celery_timeout_in_chain(outer)
        assert found is inner

    def test_chain_walker_no_false_positive(self):
        from ppt_common.llm import celery_timeout_in_chain
        assert celery_timeout_in_chain(ValueError("boom")) is None

    def test_direct_soft_timeout_propagates(self):
        client = LLMClient(api_key="test-key")
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = (
            SoftTimeLimitExceeded()
        )
        client._client = mock_openai_client
        with pytest.raises(SoftTimeLimitExceeded):
            client.chat("Hello")

    def test_openai_wrapped_soft_timeout_propagates(self):
        """The exact prod shape: openai wraps the signal-raised exception
        as APIConnectionError('Connection error.') with the timeout in the
        context chain."""
        from openai import APIConnectionError
        from httpx import Request

        client = LLMClient(api_key="test-key")
        mock_openai_client = MagicMock()

        def raise_wrapped(*args, **kwargs):
            try:
                raise SoftTimeLimitExceeded()
            except SoftTimeLimitExceeded:
                raise APIConnectionError(
                    request=Request("POST", "https://test"),
                )  # default message is "Connection error."

        mock_openai_client.chat.completions.create.side_effect = raise_wrapped
        client._client = mock_openai_client
        with pytest.raises(SoftTimeLimitExceeded):
            client.chat("Hello")

    def test_plain_errors_still_return_empty(self):
        """Regression guard: non-timeout errors keep the swallow-to-''
        contract the callers rely on."""
        client = LLMClient(api_key="test-key")
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = RuntimeError(
            "some other failure"
        )
        client._client = mock_openai_client
        assert client.chat("Hello") == ""
