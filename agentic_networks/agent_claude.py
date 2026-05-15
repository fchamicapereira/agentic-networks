import os
from typing import TypeGuard

import anthropic
from anthropic.types import MessageParam, TextBlockParam, ToolUnionParam, ToolUseBlockParam

from .agent import AGENT_TOOLS_DEFINITIONS, LLMResponse, NodeAgent, REPORT_PROMPT, StopReason, ToolUseBlock
from .message_bus import MessageBus
from mininet.node import Host
from .network import Interface

ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"

MODELS = {
    "sonnet-4-6": "claude-sonnet-4-6",
    "opus-4-6": "claude-opus-4-6",
    "opus-4-7": "claude-opus-4-7",
}

# Cache all tool definitions — mark the last entry as the cache boundary.
TOOLS: list[ToolUnionParam] = [
    *({"name": t["name"], "description": t["description"], "input_schema": t["schema"]} for t in AGENT_TOOLS_DEFINITIONS[:-1]),
    {
        "name": AGENT_TOOLS_DEFINITIONS[-1]["name"],
        "description": AGENT_TOOLS_DEFINITIONS[-1]["description"],
        "input_schema": AGENT_TOOLS_DEFINITIONS[-1]["schema"],
        "cache_control": {"type": "ephemeral"},
    },
]


def _is_tool_use_block(block: object) -> TypeGuard[ToolUseBlockParam]:
    return isinstance(block, dict) and block.get("type") == "tool_use"


class AgentClaude(NodeAgent):
    """NodeAgent backed by the Anthropic Claude API."""

    def __init__(
        self,
        node_name: str,
        host: Host,
        bus: MessageBus,
        initial_prompt: str,
        model: str,
        max_iterations: int,
        max_tokens: int,
        ifaces: list[Interface],
        window_size: int,
    ):
        super().__init__(node_name, host, bus, initial_prompt, model, max_iterations, max_tokens, ifaces)

        if ANTHROPIC_API_KEY_ENV_VAR not in os.environ:
            print("Error: ANTHROPIC_API_KEY environment variable is not set.")
            exit(1)

        self.client = anthropic.Anthropic(api_key=os.getenv(ANTHROPIC_API_KEY_ENV_VAR))
        self.messages: list[MessageParam] = []
        self.window_size = window_size
        self._system: list[TextBlockParam] = [{"type": "text", "text": self.initial_prompt, "cache_control": {"type": "ephemeral"}}]

        # Claude requires all tool results batched in a single user message,
        # so we buffer them here and flush before the next API call.
        # Received messages are buffered separately and combined with tool results
        # on flush so we never produce two consecutive user messages.
        self._pending_tool_results = []
        self._pending_user_content: list[dict] = []

    def _flush_pending(self):
        """Combine buffered tool results and received messages into one user message."""
        content = self._pending_tool_results + self._pending_user_content
        if content:
            self.messages.append({"role": "user", "content": content})
            self._pending_tool_results = []
            self._pending_user_content = []

    def _windowed_messages(self) -> list[MessageParam]:
        """Return the last window_size messages safe to send to the API.

        Ensures the window never starts with a user message that contains
        tool_result blocks referencing tool_use blocks that were dropped —
        those orphaned results are stripped so Claude doesn't reject the request.
        """
        msgs = self.messages
        if len(msgs) <= self.window_size:
            return msgs

        trimmed = list(msgs[-self.window_size :])

        # The window must start with a user message.
        while trimmed and trimmed[0]["role"] == "assistant":
            trimmed.pop(0)

        # Collect all tool_use IDs that are still present in the window.
        present_ids: set[str] = set()
        for msg in trimmed:
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if _is_tool_use_block(block):
                        present_ids.add(block["id"])

        # Strip orphaned tool_results from the first message.
        first = trimmed[0]
        first_content = first.get("content", [])
        if isinstance(first_content, list):
            cleaned = [b for b in first_content if not (isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") not in present_ids)]
            if len(cleaned) < len(first_content):
                trimmed[0] = {**first, "content": cleaned or [{"type": "text", "text": "Continue."}]}

        return trimmed

    def request_action_from_model(self) -> LLMResponse:
        had_pending = bool(self._pending_tool_results) or bool(self._pending_user_content)
        self._flush_pending()

        if not had_pending:
            self.messages.append({"role": "user", "content": "State the next action."})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self._system,
            tools=TOOLS,
            messages=self._windowed_messages(),
        )

        self.messages.append({"role": "assistant", "content": response.content})

        content: list[ToolUseBlock | str] = []
        for block in response.content:
            if block.type == "text":
                content.append(block.text)
            elif block.type == "tool_use":
                content.append(ToolUseBlock(id=block.id, tool_name=block.name, input=block.input))

        stop_reason: StopReason = "unknown"
        if response.stop_reason is not None:
            stop_reason = response.stop_reason

        return LLMResponse(raw=str(response), content=content, stop_reason=stop_reason)

    def store_tool_results(self, tool_use_block: ToolUseBlock, tool_result: str):
        self._pending_tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": tool_result,
            }
        )

    def process_received_message(self, sender: str, message: str):
        # Buffer the received message so it gets flushed together with any pending
        # tool results in a single user message, avoiding consecutive user messages.
        self._pending_user_content.append({"type": "text", "text": f"[Message from {sender}]: {message}"})

    def request_report(self) -> str:
        self._flush_pending()
        messages = self.messages + [{"role": "user", "content": REPORT_PROMPT}]
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self._system,
            messages=messages,
        )
        return "\n".join(b.text for b in response.content if b.type == "text")
