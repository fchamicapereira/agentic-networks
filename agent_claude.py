import logging
import os

import anthropic
from anthropic.types import MessageParam, ToolUnionParam

from agent import AGENT_TOOLS_DEFINITIONS, LLMResponse, NodeAgent, StopReason, ToolUseBlock
from message_bus import MessageBus

ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"

MODELS = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

TOOLS: list[ToolUnionParam] = [
    {
        "name": t["name"],
        "description": t["description"],
        "input_schema": t["schema"],
    }
    for t in AGENT_TOOLS_DEFINITIONS
]


class AgentClaude(NodeAgent):
    """NodeAgent backed by the Anthropic Claude API."""

    def __init__(
        self,
        node_name: str,
        mininet_host_cmd,
        bus: MessageBus,
        initial_prompt: str,
        model: str,
        max_iterations: int,
        max_tokens: int,
    ):
        super().__init__(node_name, mininet_host_cmd, bus, initial_prompt, model, max_iterations, max_tokens)

        if ANTHROPIC_API_KEY_ENV_VAR not in os.environ:
            print("Error: ANTHROPIC_API_KEY environment variable is not set.")
            exit(1)

        self.client = anthropic.Anthropic(api_key=os.getenv(ANTHROPIC_API_KEY_ENV_VAR))
        self.messages: list[MessageParam] = []

        # Claude requires all tool results batched in a single user message,
        # so we buffer them here and flush before the next API call.
        self._pending_tool_results = []

    def _flush_tool_results(self) -> None:
        """Append buffered tool results as one user message, then clear the buffer."""
        if self._pending_tool_results:
            self.messages.append({"role": "user", "content": self._pending_tool_results})
            self._pending_tool_results = []

    def request_action_from_model(self) -> LLMResponse:
        # Flush any tool results accumulated since the last call
        self._flush_tool_results()

        self.messages.append({"role": "user", "content": "Continue with the next action."})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.initial_prompt,
            tools=TOOLS,
            messages=self.messages,
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

    def store_tool_results(self, tool_use_block: ToolUseBlock, tool_result: str) -> None:
        self._pending_tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": tool_result,
            }
        )

    def process_received_message(self, sender: str, message: str) -> None:
        # Flush pending tool results first so ordering is correct
        self._flush_tool_results()
        self.messages.append({"role": "user", "content": f"[Message from {sender}]: {message}"})
