"""
Pydantic AI agent integration helpers.

Provides model configuration, agent factories, and common dependency types
for building structured LLM agents with Pydantic AI.

Public API:
    get_default_model()    — Get DashScope/Qwen model
    get_model(provider)    — Get model by provider name
    AgentFactory           — Factory for creating agents with shared config
    BaseDeps, UserDeps,    — Common dependency types
    DocumentDeps,
    ConversationDeps
    parse_json_response()  — Parse JSON from LLM responses
    format_citations()     — Format search results as citations
    truncate_text()        — Truncate text with suffix
    validate_required_fields() — Validate required dict fields

Usage:
    from ppt_common.agents import AgentFactory, get_default_model
    from pydantic import BaseModel
    
    class StudyPlan(BaseModel):
        steps: list[str]
        total_minutes: int
    
    factory = AgentFactory[StudyPlan](
        result_type=StudyPlan,
        system_prompt="You are a study planning assistant.",
    )
    agent = factory.create()
    result = await agent.run("Plan a study schedule for chapter 3")
    # result.data is StudyPlan — fully validated
"""

from .models import get_default_model, get_model
from .base import AgentFactory
from .deps import BaseDeps, UserDeps, DocumentDeps, ConversationDeps
from .tools import (
    parse_json_response,
    format_citations,
    truncate_text,
    validate_required_fields,
)

__all__ = [
    # Model configuration
    "get_default_model",
    "get_model",
    # Agent factory
    "AgentFactory",
    # Dependency types
    "BaseDeps",
    "UserDeps",
    "DocumentDeps",
    "ConversationDeps",
    # Utility functions
    "parse_json_response",
    "format_citations",
    "truncate_text",
    "validate_required_fields",
]
