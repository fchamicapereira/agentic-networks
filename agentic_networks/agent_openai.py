import json
import os
import time
from enum import Enum
from typing import Any

from openai import OpenAI, RateLimitError

from .agent import Agent, LLMResponse, REPORT_PROMPT, StopReason, ToolUseBlock
from .agent import DEFAULT_SYSTEM_PROMPT, DEFAULT_MAX_TOKENS, DEFAULT_TOOL_DEFS, DEFAULT_WINDOW_SIZE


class ReasoningEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"

MODELS = {
    "gpt-5.5": "gpt-5.5",
    "gpt-5.4": "gpt-5.4",
    "gpt-5.4-mini": "gpt-5.4-mini",
    "gpt-5.4-nano": "gpt-5.4-nano",
}

REASONING_EFFORT = ReasoningEffort.MEDIUM


class AgentOpenAI(Agent):
    """Agent backed by the OpenAI Responses API (/v1/responses).

    Conversation state is kept server-side. We only track the last response ID
    and a small queue of pending inputs (tool outputs, injected messages) that
    must be flushed at the start of the next request_action call.
    """

    def __init__(
        self,
        model: str,
        name: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tool_defs: list[dict] = DEFAULT_TOOL_DEFS,
        window_size: int = DEFAULT_WINDOW_SIZE,  # accepted but unused; state is server-side
    ):
        # max_output_tokens in the Responses API covers both reasoning tokens and
        # output tokens (unlike Anthropic's max_tokens which is output-only), so
        # we double whatever budget the caller provides.
        openai_max_tokens = max_tokens * 1

        super().__init__(model, name, system_prompt, openai_max_tokens, tool_defs, window_size)

        if OPENAI_API_KEY_ENV_VAR not in os.environ:
            self.log.error("%s environment variable is not set.", OPENAI_API_KEY_ENV_VAR)
            exit(1)
        self.client = OpenAI(api_key=os.getenv(OPENAI_API_KEY_ENV_VAR))

        self._last_response_id: str | None = None
        # Accumulates tool outputs and injected user messages between request_action calls
        self._pending_inputs: list[dict] = []
        self._system_submitted: bool = False

        # Responses API tool format: name/description/parameters at top level, no "function" wrapper
        self._tools: list[dict] = [
            {
                "type": "function",
                "name": t["name"],
                "description": t["description"],
                "parameters": t["schema"],
            }
            for t in self.tool_defs
        ]

    def _call_api(
        self,
        input_items: list[dict],
        tools: list[dict] | None = None,
        previous_response_id: str | None = None,
    ):
        for attempt in range(20):
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "input": input_items,
                    "max_output_tokens": self.max_tokens,
                    "reasoning": {"effort": REASONING_EFFORT.value},
                }
                if previous_response_id:
                    kwargs["previous_response_id"] = previous_response_id
                if tools:
                    kwargs["tools"] = tools
                self.log.debug("API request:\n%s", json.dumps(kwargs, indent=2, default=str))
                return self.client.responses.create(**kwargs)
            except RateLimitError as e:
                if "insufficient_quota" in str(e):
                    self.log.error("OpenAI quota exceeded. Check your plan and billing details.")
                    exit(1)
                if attempt == 19:
                    raise
                wait = min(10 * 2**attempt, 120)
                self.log.warning("Rate limited (attempt %d/20), retrying in %ds...", attempt + 1, wait)
                time.sleep(wait)
        raise RuntimeError("unreachable")

    def _parse_output(self, response) -> tuple[list[ToolUseBlock | str], StopReason]:
        """Parse Responses API output items into content blocks and a stop reason."""
        content: list[ToolUseBlock | str] = []
        has_tool_calls = False

        for item in response.output:
            if item.type == "message":
                for block in item.content:
                    if block.type == "output_text" and block.text:
                        content.append(block.text)
            elif item.type == "function_call":
                has_tool_calls = True
                content.append(
                    ToolUseBlock(
                        id=item.call_id,
                        tool_name=item.name,
                        input=json.loads(item.arguments),
                    )
                )

        if has_tool_calls:
            stop_reason: StopReason = "tool_use"
        elif response.status == "completed":
            stop_reason = "end_turn"
        elif getattr(response, "incomplete_details", None) and response.incomplete_details.reason == "max_output_tokens":
            stop_reason = "max_tokens"
        else:
            stop_reason = "unknown"

        return content, stop_reason

    def request_action(self, user_message: str) -> LLMResponse:
        has_tool_outputs = any(item.get("type") == "function_call_output" for item in self._pending_inputs)

        input_items: list[dict] = []

        if has_tool_outputs:
            # Submit pending tool results (+ any injected messages); skip the new user_message.
            # Mirrors the chat-completions behaviour: don't add a user turn when tool results
            # are still outstanding.
            input_items.extend(self._pending_inputs)
        else:
            # Normal turn: system prompt (first call only), then any injected messages, then
            # the new user message.
            if not self._system_submitted:
                input_items.append({"role": "system", "content": self.system_prompt})
            input_items.extend(self._pending_inputs)
            input_items.append({"role": "user", "content": user_message})

        response = self._call_api(input_items, self._tools or None, self._last_response_id)

        self._last_response_id = response.id
        self._pending_inputs = []
        self._system_submitted = True

        usage = response.usage
        reasoning_tokens = getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", 0) or 0
        self.log.info(
            "Tokens: input=%d output=%d (reasoning=%d, other=%d) / budget=%d",
            usage.input_tokens,
            usage.output_tokens,
            reasoning_tokens,
            usage.output_tokens - reasoning_tokens,
            self.max_tokens,
        )

        content, stop_reason = self._parse_output(response)
        return LLMResponse(raw=json.dumps(response.model_dump(), indent=2, default=str), content=content, stop_reason=stop_reason)

    def store_tool_result(self, block: ToolUseBlock, result: str) -> None:
        self._pending_inputs.append(
            {
                "type": "function_call_output",
                "call_id": block.id,
                "output": result,
            }
        )

    def add_user_message(self, content: str) -> None:
        self._pending_inputs.append({"role": "user", "content": content})

    def query(self, user_message: str) -> str:
        """Stateless one-shot call — no conversation history, no tools."""
        response = self._call_api(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ]
        )
        content, _ = self._parse_output(response)
        return "\n".join(item for item in content if isinstance(item, str))

    def request_report(self) -> str:
        """Ask the model to summarise the session, continuing from the existing conversation."""
        # Flush any pending tool results so the conversation is in a clean state
        input_items = list(self._pending_inputs) + [{"role": "user", "content": REPORT_PROMPT}]
        self._pending_inputs = []
        response = self._call_api(input_items, previous_response_id=self._last_response_id)
        content, _ = self._parse_output(response)
        return "\n".join(item for item in content if isinstance(item, str))
