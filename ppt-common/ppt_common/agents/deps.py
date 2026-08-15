"""
Common dependency types for Pydantic AI agents.

Provides reusable dependency dataclasses that agents can use to access
context, configuration, and services during execution.

Usage:
    from dataclasses import dataclass
    from pydantic_ai import Agent, RunContext
    from ppt_common.agents.deps import BaseDeps
    
    @dataclass
    class MyDeps(BaseDeps):
        user_id: str
        book_id: str
    
    agent = Agent(model, deps_type=MyDeps)
    
    @agent.tool
    async def my_tool(ctx: RunContext[MyDeps], query: str) -> str:
        user_id = ctx.deps.user_id
        # ... use user_id ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaseDeps:
    """Base dependency class for Pydantic AI agents.
    
    Provides common fields that most agents need:
    - request_id: Unique identifier for tracing/logging
    - metadata: Arbitrary metadata dict for passing context
    
    Subclass this to add domain-specific dependencies.
    
    Attributes:
        request_id: Unique request identifier (for tracing/logging)
        metadata: Arbitrary metadata dict
    """
    request_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserDeps(BaseDeps):
    """Dependencies for user-scoped agents.
    
    Adds user identification to the base dependencies.
    
    Attributes:
        user_id: UUID of the authenticated user
    """
    user_id: str = ""


@dataclass
class DocumentDeps(UserDeps):
    """Dependencies for document-scoped agents.
    
    Adds document (book) identification to user dependencies.
    Useful for RAG, chat-with-document, and knowledge extraction agents.
    
    Attributes:
        book_id: UUID of the book/document
        chapter_id: Optional UUID of a specific chapter
    """
    book_id: str = ""
    chapter_id: str = ""


@dataclass
class ConversationDeps(DocumentDeps):
    """Dependencies for conversation/chat agents.
    
    Adds conversation context to document dependencies.
    Useful for chat-with-document agents that need conversation history.
    
    Attributes:
        conversation_id: UUID of the conversation
        conversation_history: List of previous messages [{"role": ..., "content": ...}]
    """
    conversation_id: str = ""
    conversation_history: list[dict[str, str]] = field(default_factory=list)
