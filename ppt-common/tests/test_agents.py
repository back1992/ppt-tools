"""
Tests for ppt_common.agents module.

Tests cover:
- Model configuration (get_default_model, get_model)
- AgentFactory creation and usage
- Dependency types (BaseDeps, UserDeps, etc.)
- Utility functions (parse_json_response, format_citations, etc.)
"""

import pytest
from unittest.mock import patch, MagicMock

# ppt_common.agents needs the optional extra ppt-common[agents] (pydantic-ai).
# Skip only when the extra is not installed (import unavailable). A broken
# dependency stack must fail loudly, never skip: silent skips are how the
# openai/pydantic-ai CI conflict went unnoticed.
def _probe_agents() -> bool:
    try:
        import pydantic_ai.models.openai  # noqa: F401
        return True
    except ImportError:
        return False

_HAS_AGENTS = _probe_agents()

_needs_agents = pytest.mark.skipif(
    not _HAS_AGENTS, reason="requires the ppt-common[agents] extra")


class TestParseJsonResponse:
    """Tests for parse_json_response utility."""
    
    def test_parse_valid_json(self):
        from ppt_common.agents.tools import parse_json_response
        
        result = parse_json_response('{"a": 1, "b": "test"}')
        assert result == {"a": 1, "b": "test"}
    
    def test_parse_json_with_code_fences(self):
        from ppt_common.agents.tools import parse_json_response
        
        result = parse_json_response('```json\n{"a": 1}\n```')
        assert result == {"a": 1}
    
    def test_parse_json_with_uppercase_fences(self):
        from ppt_common.agents.tools import parse_json_response
        
        result = parse_json_response('```JSON\n{"a": 1}\n```')
        assert result == {"a": 1}
    
    def test_parse_invalid_json_returns_none(self):
        from ppt_common.agents.tools import parse_json_response
        
        result = parse_json_response("not json")
        assert result is None
    
    def test_parse_empty_string_returns_none(self):
        from ppt_common.agents.tools import parse_json_response
        
        result = parse_json_response("")
        assert result is None
    
    def test_parse_non_dict_returns_none(self):
        from ppt_common.agents.tools import parse_json_response
        
        result = parse_json_response("[1, 2, 3]")
        assert result is None


class TestFormatCitations:
    """Tests for format_citations utility."""
    
    def test_format_empty_results(self):
        from ppt_common.agents.tools import format_citations
        
        result = format_citations([])
        assert result == "No results found."
    
    def test_format_single_result(self):
        from ppt_common.agents.tools import format_citations
        
        results = [
            {"text": "Sample text", "chunk_index": 0, "page": 1, "score": 0.95}
        ]
        result = format_citations(results)
        assert "[1]" in result
        assert "Chunk 0" in result
        assert "page 1" in result
        assert "0.95" in result
        assert "Sample text" in result
    
    def test_format_multiple_results(self):
        from ppt_common.agents.tools import format_citations
        
        results = [
            {"text": "First", "chunk_index": 0, "page": 1, "score": 0.95},
            {"text": "Second", "chunk_index": 1, "page": 2, "score": 0.85},
        ]
        result = format_citations(results)
        assert "[1]" in result
        assert "[2]" in result
        assert "First" in result
        assert "Second" in result
    
    def test_format_result_without_page(self):
        from ppt_common.agents.tools import format_citations
        
        results = [
            {"text": "Sample", "chunk_index": 0, "score": 0.95}
        ]
        result = format_citations(results)
        assert "page" not in result


class TestTruncateText:
    """Tests for truncate_text utility."""
    
    def test_truncate_short_text(self):
        from ppt_common.agents.tools import truncate_text
        
        result = truncate_text("Hello", max_chars=100)
        assert result == "Hello"
    
    def test_truncate_long_text(self):
        from ppt_common.agents.tools import truncate_text
        
        # "Hello, world!" (13 chars) with max_chars=8 and suffix "..." (3 chars)
        # Result should be 5 chars + "..." = 8 chars total
        result = truncate_text("Hello, world!", max_chars=8)
        assert result == "Hello..."
        assert len(result) == 8
    
    def test_truncate_custom_suffix(self):
        from ppt_common.agents.tools import truncate_text
        
        # "Hello, world!" with max_chars=10 and suffix " [more]" (7 chars)
        # Result should be 3 chars + " [more]" = 10 chars total
        result = truncate_text("Hello, world!", max_chars=10, suffix=" [more]")
        assert result == "Hel [more]"
        assert len(result) == 10
    
    def test_truncate_exact_length(self):
        from ppt_common.agents.tools import truncate_text
        
        result = truncate_text("Hello", max_chars=5)
        assert result == "Hello"


class TestValidateRequiredFields:
    """Tests for validate_required_fields utility."""
    
    def test_all_fields_present(self):
        from ppt_common.agents.tools import validate_required_fields
        
        data = {"a": 1, "b": 2, "c": 3}
        missing = validate_required_fields(data, ["a", "b"])
        assert missing == []
    
    def test_missing_fields(self):
        from ppt_common.agents.tools import validate_required_fields
        
        data = {"a": 1}
        missing = validate_required_fields(data, ["a", "b", "c"])
        assert missing == ["b", "c"]
    
    def test_empty_required_list(self):
        from ppt_common.agents.tools import validate_required_fields
        
        data = {"a": 1}
        missing = validate_required_fields(data, [])
        assert missing == []


class TestDependencyTypes:
    """Tests for dependency dataclasses."""
    
    def test_base_deps_defaults(self):
        from ppt_common.agents.deps import BaseDeps
        
        deps = BaseDeps()
        assert deps.request_id == ""
        assert deps.metadata == {}
    
    def test_base_deps_with_values(self):
        from ppt_common.agents.deps import BaseDeps
        
        deps = BaseDeps(request_id="req-123", metadata={"key": "value"})
        assert deps.request_id == "req-123"
        assert deps.metadata == {"key": "value"}
    
    def test_user_deps_inherits_base(self):
        from ppt_common.agents.deps import UserDeps
        
        deps = UserDeps(user_id="user-456", request_id="req-123")
        assert deps.user_id == "user-456"
        assert deps.request_id == "req-123"
    
    def test_document_deps_inherits_user(self):
        from ppt_common.agents.deps import DocumentDeps
        
        deps = DocumentDeps(
            user_id="user-456",
            book_id="book-789",
            chapter_id="chapter-012"
        )
        assert deps.user_id == "user-456"
        assert deps.book_id == "book-789"
        assert deps.chapter_id == "chapter-012"
    
    def test_conversation_deps_inherits_document(self):
        from ppt_common.agents.deps import ConversationDeps
        
        deps = ConversationDeps(
            user_id="user-456",
            book_id="book-789",
            conversation_id="conv-abc",
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]
        )
        assert deps.user_id == "user-456"
        assert deps.book_id == "book-789"
        assert deps.conversation_id == "conv-abc"
        assert len(deps.conversation_history) == 2


@_needs_agents
class TestAgentFactory:
    """Tests for AgentFactory."""
    
    def test_factory_creation(self):
        """Test that factory can be created with basic parameters."""
        from ppt_common.agents.base import AgentFactory
        from pydantic import BaseModel
        
        class TestResult(BaseModel):
            answer: str
        
        factory = AgentFactory[TestResult](
            output_type=TestResult,
            system_prompt="Test prompt",
        )
        
        assert factory.output_type == TestResult
        assert factory.system_prompt == "Test prompt"
        assert factory.retries == 2
    
    @pytest.mark.asyncio
    async def test_factory_create_agent(self):
        """Test that factory can create an agent."""
        import os
        from ppt_common.agents.base import AgentFactory
        from ppt_common.agents.models import get_default_model
        from pydantic import BaseModel
        
        class TestResult(BaseModel):
            answer: str
        
        # Set dummy API key for test; patch.dict restores the real value
        # afterwards (a leaked fake key breaks LLM-dependent tests that run
        # later in the same pytest process).
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key-for-unit-test"}):
            factory = AgentFactory[TestResult](
                output_type=TestResult,
                system_prompt="Test prompt",
            )

            # Use a real model instance (won't call API in this test)
            model = get_default_model()
            factory.model = model

            agent = factory.create()
            assert agent is not None


@_needs_agents
class TestModelConfiguration:
    """Tests for model configuration functions."""
    
    def test_get_default_model_without_api_key(self):
        """Test that get_default_model raises error without API key."""
        from ppt_common.agents.models import get_default_model
        
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="No API key configured"):
                get_default_model()
    
    def test_get_model_unknown_provider(self):
        """Test that get_model raises error for unknown provider."""
        from ppt_common.agents.models import get_model
        
        with pytest.raises(ValueError, match="Unknown provider"):
            get_model("unknown_provider")
    
    @patch.dict("os.environ", {
        "DASHSCOPE_API_KEY": "test-key",
        "DASHSCOPE_BASE_URL": "https://test.example.com/v1",
        "DASHSCOPE_MODEL": "test-model",
    })
    def test_get_default_model_with_env_vars(self):
        """Test that get_default_model uses environment variables."""
        from ppt_common.agents.models import get_default_model

        model = get_default_model()
        assert model is not None


@_needs_agents
class TestQwenThinkingModelProfile:
    """Qwen thinking models must not be sent tool_choice=required.

    DashScope rejects tool_choice=required/object in thinking mode with
    invalid_parameter_error, which silently produced 1-slide fallback PPTs.
    The profile flag makes pydantic-ai downgrade to tool_choice=auto.
    """

    @pytest.mark.parametrize("model_name,expected", [
        ("qwen3.7-max", True),
        ("qwen3-max", True),
        ("qwq-plus", True),
        ("qwq-32b", True),
        ("qwen-max", False),
        ("qwen-plus", False),
        ("qwen-turbo", False),
        ("gpt-4o", False),
    ])
    def test_thinking_model_detection(self, model_name, expected):
        from ppt_common.agents.models import _is_qwen_thinking_model

        assert _is_qwen_thinking_model(model_name) is expected

    def test_thinking_model_profile_disables_tool_choice_required(self):
        from ppt_common.agents.models import _build_qwen_profile

        profile = _build_qwen_profile("qwen3.7-max")
        assert profile is not None
        assert profile.get("openai_supports_tool_choice_required") is False

    def test_non_thinking_model_keeps_tool_choice_required(self):
        from ppt_common.agents.models import _build_qwen_profile

        profile = _build_qwen_profile("qwen-plus")
        assert profile is None or profile.get(
            "openai_supports_tool_choice_required") is not False

    @patch.dict("os.environ", {
        "DASHSCOPE_API_KEY": "test-key",
        "DASHSCOPE_MODEL": "qwen3.7-max",
    })
    def test_default_model_carries_flag_for_thinking_model(self):
        """End-to-end: the model handed to agents has the downgrade flag."""
        from ppt_common.agents.models import get_default_model

        model = get_default_model()
        assert model.profile.get("openai_supports_tool_choice_required") is False
