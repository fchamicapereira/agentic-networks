"""Generic LLM agent interface, independent of any network or experiment logic."""

import logging

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, TypeAlias

StopReason: TypeAlias = Literal[
    "end_turn",
    "max_tokens",
    "stop_sequence",
    "tool_use",
    "pause_turn",
    "refusal",
    "unknown",
]


@dataclass
class ToolUseBlock:
    id: str
    tool_name: str
    input: dict


@dataclass
class LLMResponse:
    raw: str
    content: list[ToolUseBlock | str]
    stop_reason: StopReason

    def extract_text(self) -> str:
        return "\n".join(item for item in self.content if isinstance(item, str))


REPORT_PROMPT = (
    "The experiment is now complete. Please write a concise report describing:\n"
    "1. The actions you took during this experiment\n"
    "2. The justification behind each decision\n"
    "3. What you discovered about the network\n"
    "4. Any coordination you had with other agents\n\n"
    "Be specific about commands you ran, routing rules you configured, and why you made each choice. "
    "Write the report in plain text without tool calls."
)

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant for managing a network node."
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TOOL_DEFS: list[dict] = []
DEFAULT_WINDOW_SIZE = 0


class Agent(ABC):
    def __init__(
        self,
        model: str,
        name: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tool_defs: list[dict] = DEFAULT_TOOL_DEFS,
        window_size: int = DEFAULT_WINDOW_SIZE,
    ):
        self.name = name
        self.log = logging.getLogger(f"agent.{name}")
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.tool_defs = tool_defs or []
        self.window_size = window_size

    @abstractmethod
    def request_action(self, user_message: str) -> LLMResponse:
        """Send user_message and return the model's response."""

    @abstractmethod
    def store_tool_result(self, block: ToolUseBlock, result: str) -> None:
        """Record the result of a tool call in the message history."""

    @abstractmethod
    def add_user_message(self, content: str) -> None:
        """Inject an arbitrary user-role message into the history (e.g. inter-agent messages)."""

    @abstractmethod
    def query(self, user_message: str) -> str:
        """Send a plain-text message and return the model's reply. No tool calls, no history side-effects."""

    @abstractmethod
    def request_report(self) -> str:
        """Ask the model for a plain-text summary of the session."""
