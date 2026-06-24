import os
import sys
import time
import anthropic

from typing import TypeGuard

from anthropic.types import MessageParam, TextBlockParam, ToolResultBlockParam, ToolUnionParam, ToolUseBlockParam

from .agent import Agent, LLMResponse, REPORT_PROMPT, StopReason, ToolUseBlock
from .agent import DEFAULT_SYSTEM_PROMPT, DEFAULT_MAX_TOKENS, DEFAULT_TOOL_DEFS, DEFAULT_WINDOW_SIZE

ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
ANTHROPIC_STATUS_ERROR_HTTP_OVERLOADED = 529

MODELS = {
    "sonnet-4-6": "claude-sonnet-4-6",
    "opus-4-6": "claude-opus-4-6",
    "opus-4-7": "claude-opus-4-7",
}


def _is_tool_use_block(block: object) -> TypeGuard[ToolUseBlockParam]:
    return isinstance(block, dict) and block.get("type") == "tool_use"


class AgentClaude(Agent):
    """Agent backed by the Anthropic Claude API."""

    def __init__(
        self,
        model: str,
        name: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tool_defs: list[dict] = DEFAULT_TOOL_DEFS,
        window_size: int = DEFAULT_WINDOW_SIZE,
    ):
        super().__init__(model, name, system_prompt, max_tokens, tool_defs, window_size)

        api_key = os.environ.get(ANTHROPIC_API_KEY_ENV_VAR, "").strip()
        if not api_key:
            print(f"error: {ANTHROPIC_API_KEY_ENV_VAR} is not set or empty", file=sys.stderr)
            exit(1)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.messages: list[MessageParam] = []
        self._system: list[TextBlockParam] = [
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # Build tools list with cache_control on the last entry.
        self._tools: list[ToolUnionParam] = (
            [
                *({"name": t["name"], "description": t["description"], "input_schema": t["schema"]} for t in self.tool_defs[:-1]),
                {
                    "name": self.tool_defs[-1]["name"],
                    "description": self.tool_defs[-1]["description"],
                    "input_schema": self.tool_defs[-1]["schema"],
                    "cache_control": {"type": "ephemeral"},
                },
            ]
            if self.tool_defs
            else []
        )

        # Claude requires all tool results batched in a single user message.
        # Received messages are buffered separately and combined with tool results
        # on flush so we never produce two consecutive user messages.
        self._pending_tool_results: list[ToolResultBlockParam] = []
        self._pending_user_content: list[TextBlockParam] = []

    def _flush_pending(self):
        content = self._pending_tool_results + self._pending_user_content
        if content:
            self.messages.append({"role": "user", "content": content})
            self._pending_tool_results = []
            self._pending_user_content = []

    def _windowed_messages(self) -> list[MessageParam]:
        msgs = self.messages
        if len(msgs) <= self.window_size:
            return msgs

        trimmed = list(msgs[-self.window_size :])

        while trimmed and trimmed[0]["role"] == "assistant":
            trimmed.pop(0)

        present_ids: set[str] = set()
        for msg in trimmed:
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if _is_tool_use_block(block):
                        present_ids.add(block["id"])

        first = trimmed[0]
        first_content = first.get("content", [])
        if isinstance(first_content, list):
            cleaned = [b for b in first_content if not (isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") not in present_ids)]
            if len(cleaned) < len(first_content):
                trimmed[0] = {**first, "content": cleaned or [{"type": "text", "text": "Continue."}]}

        return trimmed

    def request_action(self, user_message: str) -> LLMResponse:
        had_pending = bool(self._pending_tool_results) or bool(self._pending_user_content)

        if had_pending:
            self._pending_user_content.append({"type": "text", "text": user_message})
            self._flush_pending()
        else:
            self.messages.append({"role": "user", "content": user_message})

        for attempt in range(20):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=self._system,
                    tools=self._tools,
                    messages=self._windowed_messages(),
                )
                break
            except anthropic.APIStatusError as e:
                if e.status_code != ANTHROPIC_STATUS_ERROR_HTTP_OVERLOADED:
                    raise
                if attempt == 19:
                    raise
                wait = min(10 * 2**attempt, 120)
                self.log.warning("API overloaded (attempt %d/20), retrying in %ds...", attempt + 1, wait)
                time.sleep(wait)

        self.messages.append({"role": "assistant", "content": response.content})

        content: list[ToolUseBlock | str] = []
        for block in response.content:
            if block.type == "text":
                content.append(block.text)
            elif block.type == "tool_use":
                content.append(ToolUseBlock(id=block.id, tool_name=block.name, input=block.input))

        stop_reason: StopReason = response.stop_reason if response.stop_reason is not None else "unknown"
        return LLMResponse(raw=str(response), content=content, stop_reason=stop_reason)

    def query(self, user_message: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return "\n".join(b.text for b in response.content if b.type == "text")

    def store_tool_result(self, block: ToolUseBlock, result: str) -> None:
        self._pending_tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            }
        )

    def add_user_message(self, content: str) -> None:
        self._pending_user_content.append({"type": "text", "text": content})

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
