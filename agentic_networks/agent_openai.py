import json
import logging
import os
import time

from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionToolParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam

from .agent import Agent, LLMResponse, REPORT_PROMPT, StopReason, ToolUseBlock
from .agent import DEFAULT_SYSTEM_PROMPT, DEFAULT_MAX_TOKENS, DEFAULT_TOOL_DEFS, DEFAULT_WINDOW_SIZE

OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"

MODELS = {
    "gpt-5.4": "gpt-5.4",
    "gpt-4.1": "gpt-4.1",
    "gpt-4.1-mini": "gpt-4.1-mini",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "o3": "o3",
    "o4-mini": "o4-mini",
}

_FINISH_REASON_MAP: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}


class AgentOpenAI(Agent):
    """Agent backed by the OpenAI GPT cloud API."""

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

        if OPENAI_API_KEY_ENV_VAR not in os.environ:
            self.log.error("%s environment variable is not set.", OPENAI_API_KEY_ENV_VAR)
            exit(1)
        self.client = OpenAI(api_key=os.getenv(OPENAI_API_KEY_ENV_VAR))
        self.messages: list[ChatCompletionMessageParam] = []
        self._tools: list[ChatCompletionToolParam] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["schema"],
                },
            }
            for t in self.tool_defs
        ]

    def _call_api(self, messages: list[ChatCompletionMessageParam], tools: list[ChatCompletionToolParam] | None = None):
        for attempt in range(20):
            try:
                kwargs = {"model": self.model, "max_tokens": self.max_tokens, "messages": messages}
                if tools:
                    kwargs["tools"] = tools
                return self.client.chat.completions.create(**kwargs)
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

    def _windowed_messages(self) -> list[ChatCompletionMessageParam]:
        msgs = self.messages
        if len(msgs) <= self.window_size:
            return msgs
        trimmed = list(msgs[-self.window_size :])
        while trimmed and trimmed[0]["role"] != "user":
            trimmed.pop(0)
        return trimmed

    def request_action(self, user_message: str) -> LLMResponse:
        if not self.messages or self.messages[-1]["role"] != "tool":
            self.messages.append({"role": "user", "content": user_message})

        system_message: ChatCompletionMessageParam = {"role": "system", "content": self.system_prompt}
        full_messages = [system_message] + self._windowed_messages()

        response = self._call_api(full_messages, self._tools or None)
        assert len(response.choices) == 1
        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        tool_calls: list[tuple[str, str, dict]] = []
        if msg.tool_calls:
            tool_calls = [(tc.id, tc.function.name, json.loads(tc.function.arguments)) for tc in msg.tool_calls if isinstance(tc, ChatCompletionMessageToolCall)]

        tool_calls_param: list[ChatCompletionMessageToolCallParam] = [
            {
                "id": tid,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
            for tid, name, args in tool_calls
        ]

        assistant_message: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": msg.content,
            "tool_calls": tool_calls_param,
        }
        self.messages.append(assistant_message)

        content: list[ToolUseBlock | str] = []
        if msg.content:
            content.append(msg.content)
        for tid, name, args in tool_calls:
            content.append(ToolUseBlock(id=tid, tool_name=name, input=args))

        stop_reason: StopReason = _FINISH_REASON_MAP.get(finish_reason, "unknown")
        return LLMResponse(raw=str(response), content=content, stop_reason=stop_reason)

    def query(self, user_message: str) -> str:
        response = self._call_api([
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ])
        return response.choices[0].message.content or ""

    def store_tool_result(self, block: ToolUseBlock, result: str) -> None:
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": block.id,
                "content": result,
            }
        )

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def request_report(self) -> str:
        system_message: ChatCompletionMessageParam = {"role": "system", "content": self.system_prompt}
        messages = [system_message] + self._windowed_messages() + [{"role": "user", "content": REPORT_PROMPT}]
        response = self._call_api(messages)
        return response.choices[0].message.content or ""
