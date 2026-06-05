import json
import os
from typing import Callable

from openai import OpenAI
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionToolParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam

from .agent import AGENT_TOOLS_DEFINITIONS, LLMResponse, NodeAgent, REPORT_PROMPT, StopReason, ToolUseBlock
from .message_bus import MessageBus
from mininet.node import Host
from .network import Interface

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

TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["schema"],
        },
    }
    for t in AGENT_TOOLS_DEFINITIONS
]

_FINISH_REASON_MAP: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}


class AgentOpenAI(NodeAgent):
    """NodeAgent backed by the OpenAI GPT cloud API."""

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
        extra_tools: list[dict] | None = None,
        context_fn: "Callable[[], str] | None" = None,
    ):
        super().__init__(
            node_name,
            host,
            bus,
            initial_prompt,
            model,
            max_iterations,
            max_tokens,
            ifaces,
            extra_tools=extra_tools,
            context_fn=context_fn,
        )

        if OPENAI_API_KEY_ENV_VAR not in os.environ:
            print(f"Error: {OPENAI_API_KEY_ENV_VAR} environment variable is not set.")
            exit(1)

        self.client = OpenAI(api_key=os.getenv(OPENAI_API_KEY_ENV_VAR))
        self.messages: list[ChatCompletionMessageParam] = []
        self.window_size = window_size

    def _windowed_messages(self) -> list[ChatCompletionMessageParam]:
        msgs = self.messages
        if len(msgs) <= self.window_size:
            return msgs

        trimmed = list(msgs[-self.window_size :])

        # Don't start mid-exchange: skip until we find a user message.
        # This avoids orphaned tool messages whose tool_call_id references
        # an assistant message that was trimmed away.
        while trimmed and trimmed[0]["role"] != "user":
            trimmed.pop(0)

        return trimmed

    def _all_tools(self) -> list[ChatCompletionToolParam]:
        if not self.extra_tool_defs:
            return TOOLS
        extra: list[ChatCompletionToolParam] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["schema"],
                },
            }
            for t in self.extra_tool_defs
        ]
        return TOOLS + extra

    def request_action_from_model(self) -> LLMResponse:
        if not self.messages or self.messages[-1]["role"] != "tool":
            context = self.context_fn() if self.context_fn else ""
            action_text = f"{context}\n\nState the next action." if context else "State the next action."
            self.messages.append({"role": "user", "content": action_text})

        system_message: ChatCompletionMessageParam = {"role": "system", "content": self.initial_prompt}
        full_messages = [system_message] + self._windowed_messages()

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tools=self._all_tools(),
            messages=full_messages,
        )
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

    def store_tool_results(self, tool_use_block: ToolUseBlock, tool_result: str):
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_use_block.id,
                "content": tool_result,
            }
        )

    def process_received_message(self, sender: str, message: str):
        self.messages.append({"role": "user", "content": f"[Message from {sender}]: {message}"})

    def request_report(self) -> str:
        system_message: ChatCompletionMessageParam = {"role": "system", "content": self.initial_prompt}
        messages = [system_message] + self._windowed_messages() + [{"role": "user", "content": REPORT_PROMPT}]
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
        )
        return response.choices[0].message.content or ""
