"""
Unified LLM client for OpenAI-compatible endpoints.

Single client implementation for any OpenAI-compatible API (DashScope /
Qwen included), with proxy handling and JSON-response parsing.

Public API:
    LLMClient          — lazy-initialised OpenAI client with proxy handling
    parse_llm_json(s)  — parse a JSON response that may be wrapped in fences

Environment variables read (all optional, pass explicit values to override):
    DASHSCOPE_API_KEY / LLM_API_KEY   — API key
    DASHSCOPE_BASE_URL / LLM_BASE_URL — base URL
    DASHSCOPE_MODEL / LLM_MODEL       — model name

Usage:
    from ppt_common.llm import LLMClient, parse_llm_json

    client = LLMClient()
    response = client.chat("Summarise this text.", system="You are a summary expert.")
    data = parse_llm_json(response)
"""

from __future__ import annotations

import json
from pathlib import Path
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_DEFAULT_TIMEOUT = 120  # seconds

# Environment-variable names (checked in order, first match wins)
_API_KEY_VARS = ("DASHSCOPE_API_KEY", "LLM_API_KEY")
_BASE_URL_VARS = ("DASHSCOPE_BASE_URL", "LLM_BASE_URL")
_MODEL_VARS = ("DASHSCOPE_MODEL", "LLM_MODEL")

# Proxy variables to temporarily clear when calling domestic China APIs
_PROXY_VARS = (
    "ALL_PROXY", "all_proxy",
    "HTTPS_PROXY", "https_proxy",
    "HTTP_PROXY", "http_proxy",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_env(var_names: tuple[str, ...], default: str = "") -> str:
    """Return the value of the first environment variable that is set."""
    for name in var_names:
        val = os.getenv(name, "")
        if val:
            return val
    return default


def parse_llm_json(raw: str) -> dict | None:
    """
    Parse a JSON response from an LLM, stripping markdown code fences.

    Returns the parsed dict, or ``None`` if parsing fails.

    >>> parse_llm_json('```json\\n{"a": 1}\\n```')
    {'a': 1}
    >>> parse_llm_json('not json') is None
    True
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()
    text = re.sub(r"^```(?:json|JSON)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    return data if isinstance(data, dict) else None


def _image_data_uri(path) -> str:
    """Encode a local image file as a base64 data URI."""
    import base64
    import mimetypes

    data = Path(path).read_bytes()
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------


# Celery task-timeout exceptions, matched by class name so ppt-common stays
# celery-dependency-free. When a worker's soft time limit fires mid-request,
# the signal handler raises SoftTimeLimitExceeded inside the blocking HTTP
# read; the openai SDK then wraps it (e.g. as APIConnectionError
# "Connection error."). Swallowing that let tasks sail past the soft limit
# until the hard limit SIGKILLed the worker. Timeout exceptions
# must propagate so the task stops gracefully.
_CELERY_TIMEOUT_NAMES = ("SoftTimeLimitExceeded", "TimeLimitExceeded")


def celery_timeout_in_chain(exc: BaseException) -> BaseException | None:
    """Return a celery timeout exception hidden anywhere in exc's cause chain."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ in _CELERY_TIMEOUT_NAMES:
            return current
        current = current.__cause__ or current.__context__
    return None


class LLMClient:
    """
    Lazy-initialised OpenAI-compatible client with DashScope proxy handling.

    The underlying ``openai.OpenAI`` instance is created on first use so that
    packages can construct the client even when ``openai`` is not yet
    installed (the import happens lazily).

    Parameters
    ----------
    api_key : str
        API key.  Falls back to ``DASHSCOPE_API_KEY`` / ``LLM_API_KEY``.
    base_url : str
        API base URL.  Falls back to ``DASHSCOPE_BASE_URL`` / ``LLM_BASE_URL``.
    model : str
        Default model name.  Falls back to ``DASHSCOPE_MODEL`` / ``LLM_MODEL``.
    timeout : int
        Request timeout in seconds (default 60).
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        timeout: int = _DEFAULT_TIMEOUT,
    ):
        self._api_key = api_key or _first_env(_API_KEY_VARS)
        self._base_url = base_url or _first_env(_BASE_URL_VARS, _DEFAULT_BASE_URL)
        self._model = model or _first_env(_MODEL_VARS, "qwen-plus")
        self._timeout = timeout
        self._client: Any | None = None

    # -- properties --------------------------------------------------------

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model(self) -> str:
        return self._model

    @property
    def is_available(self) -> bool:
        """True if an API key has been configured."""
        return bool(self._api_key)

    # -- lazy client -------------------------------------------------------

    @property
    def client(self) -> Any:
        """
        Return the underlying ``openai.OpenAI`` instance, creating it on
        first access.

        Raises ``RuntimeError`` if no API key is configured or if the
        ``openai`` package is not installed.
        """
        if self._client is not None:
            return self._client

        if not self._api_key:
            raise RuntimeError(
                "No API key configured. Set DASHSCOPE_API_KEY or LLM_API_KEY, "
                "or pass api_key to LLMClient()."
            )

        try:
            import httpx
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' and 'httpx' packages are required. "
                "Install them with: pip install 'ppt-common[llm]'"
            ) from exc

        # Temporarily clear proxy env vars — DashScope is a domestic China API
        saved_proxy: dict[str, str] = {}
        for key in _PROXY_VARS:
            if key in os.environ:
                saved_proxy[key] = os.environ.pop(key)

        try:
            http_client = httpx.Client(
                base_url=self._base_url,
                timeout=float(self._timeout),
                verify=False,
                proxy=None,
            )
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                default_headers={"Content-Type": "application/json"},
                http_client=http_client,
                # The SDK applies its own 600s default per request, overriding
                # the httpx.Client timeout -- pass it here so the documented
                # ``timeout`` actually bounds stalled reads.
                timeout=float(self._timeout),
                # Disable the SDK's internal retries (default 2): they silently
                # re-run stalled reads, tripling the wall time of a hung-gateway
                # call before _complete's own retry policy sees the error.
                # Retry policy belongs to _complete -- it logs, backs
                # off, and propagates celery timeouts; the SDK's does none of
                # that.
                max_retries=0,
            )
        finally:
            os.environ.update(saved_proxy)

        return self._client

    # -- convenience -------------------------------------------------------

    def chat(
        self,
        user_prompt: str,
        *,
        system: str = "",
        model: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        response_format: dict | None = None,
        max_retries: int = 1,
    ) -> str:
        """
        Send a chat completion request and return the raw text response.

        Automatically retries on rate limit (429) and server errors (5xx) with
        exponential backoff.

        Parameters
        ----------
        user_prompt : str
            The user message.
        system : str
            Optional system message.
        model : str
            Override the default model for this call.
        max_tokens : int
            Maximum tokens in the response.
        temperature : float
            Sampling temperature.
        response_format : dict | None
            Optional response format hint (e.g. ``{"type": "json_object"}``).
        max_retries : int
            Maximum retry attempts for transient errors (default 5).

        Returns
        -------
        str
            The model's text response, or an empty string on failure.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})

        kwargs: dict[str, Any] = {
            "model": model or self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format

        return self._complete(kwargs, max_retries)

    def chat_with_images(
        self,
        user_prompt: str,
        image_paths: list,
        *,
        system: str = "",
        model: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.2,
        max_retries: int = 1,
    ) -> str:
        """
        Send a multimodal chat (text + images) and return the raw text.

        Images are inlined as base64 data URIs (DashScope-compatible
        endpoints cannot fetch local file paths). Powers the render-level
        visual QC loop and similar multimodal review tasks.
        """
        content: list[dict] = [{"type": "text", "text": user_prompt}]
        for path in image_paths:
            content.append(
                {"type": "image_url", "image_url": {"url": _image_data_uri(path)}}
            )

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})

        kwargs: dict[str, Any] = {
            "model": model or self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        return self._complete(kwargs, max_retries)

    def _complete(self, kwargs: dict, max_retries: int) -> str:
        """Run one completion with 429/5xx backoff retries (shared by chat*)."""
        from openai import APIStatusError, APITimeoutError

        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(**kwargs)
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
                logger.warning("LLM returned empty response")
                return ""
            except APIStatusError as exc:
                timeout_exc = celery_timeout_in_chain(exc)
                if timeout_exc is not None:
                    raise timeout_exc
                last_exc = exc
                # Retry on 429 (rate limit) and 5xx (server errors)
                if exc.status_code == 429 or exc.status_code >= 500:
                    if attempt < max_retries:
                        # Exponential backoff: 2s, 4s, 8s, 16s, 32s (capped at 60s)
                        delay = min((attempt + 1) * 2, 10)
                        logger.warning(
                            "LLM request failed with %d (attempt %d/%d), retrying in %ds: %s",
                            exc.status_code, attempt + 1, max_retries + 1, delay, exc.message
                        )
                        time.sleep(delay)
                        continue
                    # Retryable status but retries exhausted
                    logger.error("LLM request failed after %d retries (status %d): %s", max_retries, exc.status_code, exc.message)
                    return ""
                # Non-retryable error (401, 400, 404, etc.)
                logger.error("LLM request failed with non-retryable error %d: %s", exc.status_code, exc.message)
                return ""
            except (APITimeoutError, ConnectionError, TimeoutError, OSError) as exc:
                timeout_exc = celery_timeout_in_chain(exc)
                if timeout_exc is not None:
                    raise timeout_exc
                last_exc = exc
                if attempt < max_retries:
                    delay = min((attempt + 1) * 2, 10)
                    logger.warning(
                        "LLM connection error (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1, max_retries + 1, delay, exc
                    )
                    time.sleep(delay)
                    continue
                logger.error("LLM connection error after %d retries: %s", max_retries, exc)
                return ""
            except Exception as exc:
                timeout_exc = celery_timeout_in_chain(exc)
                if timeout_exc is not None:
                    raise timeout_exc
                # Unexpected error — don't retry
                logger.error("LLM request failed with unexpected error: %s", exc)
                return ""

        logger.error("LLM request failed after %d retries: %s", max_retries, last_exc)
        return ""
    def chat_json(
        self,
        user_prompt: str,
        *,
        system: str = "",
        model: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        max_retries: int = 1,
    ) -> dict | None:
        """
        Send a chat request expecting a JSON response.

        Tries ``response_format={"type": "json_object"}`` first; falls back to
        stripping code fences from the raw text.
        """
        raw = self.chat(
            user_prompt,
            system=system,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
            max_retries=max_retries,
        )
        return parse_llm_json(raw)
