"""
Model configuration for Pydantic AI agents.

Provides factory functions for creating LLM models from different providers.
Supports DashScope (Qwen), OpenAI, Anthropic, and Ollama.

Environment variables:
    DASHSCOPE_API_KEY / LLM_API_KEY   — API key for DashScope
    DASHSCOPE_BASE_URL / LLM_BASE_URL — Base URL for DashScope
    DASHSCOPE_MODEL / LLM_MODEL       — Default model name

Usage:
    from ppt_common.agents.models import get_default_model, get_model
    
    model = get_default_model()  # DashScope/Qwen
    model = get_model("openai")  # OpenAI GPT
"""

from __future__ import annotations

import os
import re
from typing import Any

# Proxy variables to temporarily clear when calling domestic China APIs
_PROXY_VARS = (
    "ALL_PROXY", "all_proxy",
    "HTTPS_PROXY", "https_proxy",
    "HTTP_PROXY", "http_proxy",
)


def _first_env(var_names: tuple[str, ...], default: str = "") -> str:
    """Return the value of the first environment variable that is set."""
    for name in var_names:
        val = os.getenv(name, "")
        if val:
            return val
    return default


def _clear_proxy_env() -> dict[str, str]:
    """Temporarily clear proxy environment variables for DashScope calls.
    
    Returns a dict of cleared variables so they can be restored later.
    """
    cleared = {}
    for var in _PROXY_VARS:
        val = os.environ.pop(var, None)
        if val is not None:
            cleared[var] = val
    return cleared


def _restore_proxy_env(cleared: dict[str, str]) -> None:
    """Restore previously cleared proxy environment variables."""
    for var, val in cleared.items():
        os.environ[var] = val



# Pattern matching Qwen thinking/reasoning models that don't support tool_choice=required.
# This includes qwen3.x-max (thinking mode), qwq-* reasoning models, etc.
_QWEN_THINKING_RE = re.compile(
    r'^(qwen-?3|qwq-)',
    re.IGNORECASE,
)


def _is_qwen_thinking_model(model_name: str) -> bool:
    """Check if a Qwen model is a thinking/reasoning model that doesn't support tool_choice=required."""
    return bool(_QWEN_THINKING_RE.match(model_name))


def _build_qwen_profile(model_name: str) -> Any:
    """Build a pydantic-ai model profile for Qwen models.
    
    Qwen thinking models (qwen3.x-max, qwq-*) don't support tool_choice=required.
    This profile tells pydantic-ai to fall back to tool_choice=auto.
    
    Uses qwen_model_profile as the base (provides InlineDefsJsonSchemaTransformer
    needed for Qwen's JSON schema handling), then overrides tool_choice support
    for thinking models.
    """
    try:
        from pydantic_ai.profiles.qwen import qwen_model_profile
    except ImportError:
        return None

    base = qwen_model_profile(model_name)
    if base is None:
        return None

    merged = dict(base)
    
    # Qwen thinking models don't support tool_choice=required
    if _is_qwen_thinking_model(model_name):
        merged['openai_supports_tool_choice_required'] = False
    
    return merged


def get_default_model() -> Any:
    """Get the default LLM model (DashScope/Qwen).
    
    Returns a Pydantic AI model configured for DashScope using the proper
    AlibabaProvider, which handles Qwen-specific JSON schema transformations
    and API quirks.
    
    Automatically handles proxy clearing for China-based API.
    
    Returns:
        Pydantic AI Model instance
    
    Raises:
        RuntimeError: If no API key is configured
    """
    try:
        # Try OpenAIChatModel first (newer name), fallback to OpenAIModel
        try:
            from pydantic_ai.models.openai import OpenAIChatModel as ModelClass
        except ImportError:
            from pydantic_ai.models.openai import OpenAIModel as ModelClass
        
        # Use AlibabaProvider for proper Qwen/DashScope support
        try:
            from pydantic_ai.providers.alibaba import AlibabaProvider
            use_alibaba = True
        except ImportError:
            # Fall back to OpenAIProvider if AlibabaProvider not available
            from pydantic_ai.providers.openai import OpenAIProvider
            use_alibaba = False
    except ImportError as e:
        raise ImportError(
            "pydantic-ai is not installed. Install with: pip install 'ppt-common[agents]'"
        ) from e
    
    api_key = _first_env(("DASHSCOPE_API_KEY", "LLM_API_KEY"))
    if not api_key:
        raise RuntimeError(
            "No API key configured. Set DASHSCOPE_API_KEY or LLM_API_KEY."
        )
    
    base_url = _first_env(
        ("DASHSCOPE_BASE_URL", "LLM_BASE_URL"),
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model_name = _first_env(("DASHSCOPE_MODEL", "LLM_MODEL"), "qwen-plus")
    
    # Build a profile for Qwen models.
    # Thinking models (qwen3.x-max, qwq-*) don't support tool_choice=required.
    profile = _build_qwen_profile(model_name)

    # Clear proxy for DashScope (China-based API)
    cleared_proxy = _clear_proxy_env()
    try:
        if use_alibaba:
            provider = AlibabaProvider(base_url=base_url, api_key=api_key)
        else:
            provider = OpenAIProvider(base_url=base_url, api_key=api_key)
        model = ModelClass(model_name=model_name, provider=provider, profile=profile)
    finally:
        _restore_proxy_env(cleared_proxy)
    
    return model


def get_model(provider_name: str = "default", **kwargs) -> Any:
    """Get a model by provider name.
    
    Supported providers:
    - "default" / "dashscope" — DashScope/Qwen (OpenAI-compatible)
    - "openai" — OpenAI GPT models
    - "anthropic" — Anthropic Claude
    - "ollama" — Local Ollama models
    
    Args:
        provider_name: Provider name (default: "default")
        **kwargs: Additional arguments passed to the model/provider constructor
    
    Returns:
        Pydantic AI Model instance
    
    Raises:
        ValueError: If provider is not recognized
        ImportError: If required dependencies are not installed
    
    Examples:
        >>> model = get_model("default")  # DashScope
        >>> model = get_model("openai", model_name="gpt-4o")
        >>> model = get_model("anthropic", model_name="claude-3-5-sonnet-20241022")
        >>> model = get_model("ollama", model_name="llama3")
    """
    try:
        if provider_name in ("default", "dashscope"):
            return get_default_model()
        
        elif provider_name == "openai":
            # Try OpenAIChatModel first (newer name), fallback to OpenAIModel
            try:
                from pydantic_ai.models.openai import OpenAIChatModel as ModelClass
            except ImportError:
                from pydantic_ai.models.openai import OpenAIModel as ModelClass
            from pydantic_ai.providers.openai import OpenAIProvider
            model_name = kwargs.pop("model_name", "gpt-4o")
            api_key = kwargs.pop("api_key", None)
            base_url = kwargs.pop("base_url", None)
            provider = OpenAIProvider(base_url=base_url, api_key=api_key)
            return ModelClass(model_name=model_name, provider=provider)
        
        elif provider_name == "anthropic":
            from pydantic_ai.models.anthropic import AnthropicModel
            model_name = kwargs.pop("model_name", "claude-3-5-sonnet-20241022")
            return AnthropicModel(model_name=model_name, **kwargs)
        
        elif provider_name == "ollama":
            from pydantic_ai.models.ollama import OllamaModel
            model_name = kwargs.pop("model_name", "llama3")
            return OllamaModel(model_name=model_name, **kwargs)
        
        else:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Supported: default, dashscope, openai, anthropic, ollama"
            )
    except ImportError as e:
        raise ImportError(
            f"Required dependencies for provider '{provider_name}' are not installed. "
            f"Install with: pip install 'ppt-common[agents]'"
        ) from e
