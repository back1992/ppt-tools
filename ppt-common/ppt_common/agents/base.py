"""
Base agent factory for Pydantic AI agents.

Provides a generic factory for creating Pydantic AI agents with shared
configuration (model, system prompt, retries).

Usage:
    from pydantic import BaseModel
    from ppt_common.agents.base import AgentFactory
    
    class StudyPlan(BaseModel):
        steps: list[str]
        total_minutes: int
    
    factory = AgentFactory[StudyPlan](
        output_type=StudyPlan,
        system_prompt="You are a study planning assistant.",
    )
    agent = factory.create()
    result = await agent.run("Plan a study schedule for chapter 3")
    # result.output is StudyPlan — fully validated
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from .models import get_default_model

T = TypeVar("T")


class AgentFactory(Generic[T]):
    """Factory for creating Pydantic AI agents with shared configuration.
    
    This factory encapsulates common agent setup (model, system prompt, retries)
    so that callers can create agents with minimal boilerplate.
    
    Type Parameters:
        T: The output type (a Pydantic BaseModel) that the agent will return
    
    Attributes:
        output_type: The Pydantic model class for structured output
        system_prompt: System prompt for the agent
        model: The LLM model to use (defaults to DashScope/Qwen)
        retries: Number of retry attempts for transient failures
    
    Examples:
        >>> from pydantic import BaseModel
        >>> class Answer(BaseModel):
        ...     text: str
        ...     confidence: float
        >>> factory = AgentFactory[Answer](
        ...     output_type=Answer,
        ...     system_prompt="You are a helpful assistant.",
        ... )
        >>> agent = factory.create()
        >>> result = await agent.run("What is 2+2?")
        >>> isinstance(result.output, Answer)
        True
    """
    
    def __init__(
        self,
        output_type: type[T],
        system_prompt: str = "",
        model: Any | None = None,
        retries: int = 2,
    ):
        """Initialize the agent factory.
        
        Args:
            output_type: Pydantic model class for structured output
            system_prompt: System prompt for the agent
            model: LLM model to use (defaults to get_default_model())
            retries: Number of retry attempts (default: 2)
        """
        self.output_type = output_type
        self.system_prompt = system_prompt
        self.model = model
        self.retries = retries
    
    def create(self, **kwargs) -> Any:
        """Create a Pydantic AI agent with the factory's configuration.
        
        Args:
            **kwargs: Additional arguments passed to Agent constructor
        
        Returns:
            Pydantic AI Agent instance
        
        Raises:
            ImportError: If pydantic-ai is not installed
        
        Examples:
            >>> factory = AgentFactory[Answer](output_type=Answer)
            >>> agent = factory.create()
            >>> agent_with_tools = factory.create(tools=[my_tool])
        """
        try:
            from pydantic_ai import Agent
        except ImportError as e:
            raise ImportError(
                "pydantic-ai is not installed. Install with: pip install 'ppt-common[agents]'"
            ) from e
        
        # Use provided model or get default
        model = self.model if self.model is not None else get_default_model()
        
        return Agent(
            model,
            output_type=self.output_type,
            system_prompt=self.system_prompt,
            retries=self.retries,
            **kwargs,
        )
    
    def create_with_tools(self, tools: list[Any], **kwargs) -> Any:
        """Create an agent with the given tools.
        
        Convenience method for creating agents with tool support.
        
        Args:
            tools: List of tool functions or Tool instances
            **kwargs: Additional arguments passed to Agent constructor
        
        Returns:
            Pydantic AI Agent instance with tools registered
        
        Examples:
            >>> def search(query: str) -> str:
            ...     return f"Results for: {query}"
            >>> factory = AgentFactory[Answer](output_type=Answer)
            >>> agent = factory.create_with_tools(tools=[search])
        """
        return self.create(tools=tools, **kwargs)
