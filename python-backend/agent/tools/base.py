# TradingTool abstract base — Phase 22g / ABP.2
# Phase 22g+: ABP.2b — Pydantic input_model classvar + auto-validation
# Onyx-pattern: definition() / validate() / execute()
# All tools must subclass TradingTool and implement name, definition, execute.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, ValidationError

from agent.errors import ToolValidationError

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class TradingTool(ABC):
    """Abstract base for all agent tools in TradeView Fusion."""

    # Subclasses may set this to a Pydantic model for automatic input validation
    # and JSON schema generation via model_json_schema().
    input_model: type[BaseModel] | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name — must match definition()['name']."""
        ...

    @abstractmethod
    def definition(self) -> dict:
        """Return Anthropic tool definition dict:
        {"name": ..., "description": ..., "input_schema": {"type": "object", ...}}
        """
        ...

    def validate(self, tool_input: dict, ctx: "AgentExecutionContext") -> None:
        """Policy/schema validation before execute().
        Default: validates against input_model if set (auto-JSON-Schema, ABP.2b).
        Raise ToolValidationError to surface as error result to the LLM.
        Raise CapabilityViolation to abort the loop entirely.
        Subclasses should call super().validate() first when overriding.
        """
        if self.input_model is not None:
            try:
                self.input_model(**tool_input)
            except ValidationError as e:
                raise ToolValidationError(self.name, str(e))

    @abstractmethod
    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        """Execute the tool and return a JSON-serialisable result dict."""
        ...
