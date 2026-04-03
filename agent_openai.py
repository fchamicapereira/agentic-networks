import json
import re
import uuid
import pprint

from openai import OpenAI
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionToolParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam

from agent import AGENT_TOOLS_DEFINITIONS, LLMResponse, NodeAgent, StopReason, ToolUseBlock
from message_bus import MessageBus

from typing import Optional

MODELS = {
    "qwen2.5-72b": "Qwen/Qwen2.5-72B-Instruct-AWQ",
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

"""
This is terrible, but we need it to support both the new OpenAI tool_calls format
(used by vLLM and Ollama) and the older Qwen-style <tool_call>JSON</tool_call> format.
"""
_TOOL_CALL_TAG_RE = re.compile(r"(?:<tool_call>\s*)?(\{.*?\})\s*</tool_call>", re.DOTALL)


def _parse_tool_call_tags(content: str) -> list[tuple[str, str, dict]]:
    """Parse Qwen-style <tool_call>JSON</tool_call> blocks from plain text content.

    Returns a list of (synthetic_id, tool_name, arguments) tuples.
    """
    results = []
    for match in _TOOL_CALL_TAG_RE.finditer(content):
        try:
            data = json.loads(match.group(1))
            tool_id = f"call_{uuid.uuid4().hex[:24]}"
            results.append((tool_id, data["name"], data.get("arguments", {})))
        except (json.JSONDecodeError, KeyError):
            pass
    return results


def _strip_tool_call_tags(content: str) -> Optional[str]:
    return _TOOL_CALL_TAG_RE.sub("", content).strip() or None


class AgentOpenAI(NodeAgent):
    """NodeAgent backed by any OpenAI-compatible API (vLLM, Ollama, OpenAI, etc.)."""

    def __init__(
        self,
        node_name: str,
        mininet_host_cmd,
        bus: MessageBus,
        initial_prompt: str,
        model: str,
        max_iterations: int,
        max_tokens: int,
        base_url: str,
        api_key: str,
    ):
        super().__init__(node_name, mininet_host_cmd, bus, initial_prompt, model, max_iterations, max_tokens)
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.messages: list[ChatCompletionMessageParam] = []

    def request_action_from_model(self) -> LLMResponse:
        self.messages.append({"role": "user", "content": "Continue with the next action."})

        # System prompt is prepended on every call; not stored in self.messages
        # so the history stays clean (user/assistant/tool turns only).
        system_message: ChatCompletionMessageParam = {"role": "system", "content": self.initial_prompt}
        full_messages: list[ChatCompletionMessageParam] = [system_message] + self.messages

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tools=TOOLS,
            messages=full_messages,
        )

        self.log.debug("Messages sent to model:\n%s", pprint.pformat(full_messages, indent=2))

        assert len(response.choices) == 1, "Expected exactly one choice from the model"
        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        assistant_content = msg.content

        # Collect (id, name, arguments) from whichever format the model used.
        # Path A: structured tool_calls (standard OpenAI / vLLM with --enable-auto-tool-choice)
        # Path B: <tool_call>JSON</tool_call> blocks embedded in text content (Qwen native)
        tool_calls: list[tuple[str, str, dict]] = []
        if msg.tool_calls:
            tool_calls = [(tc.id, tc.function.name, json.loads(tc.function.arguments)) for tc in msg.tool_calls if isinstance(tc, ChatCompletionMessageToolCall)]
        elif "<tool_call>" in (msg.content or ""):
            tool_calls = _parse_tool_call_tags(msg.content or "")
            # Strip <tool_call> blocks from stored content so history stays clean
            assistant_content = _strip_tool_call_tags(msg.content or "") if tool_calls else msg.content
            self.log.debug("Parsed tool calls from content: %s", pprint.pformat(tool_calls, indent=2))

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
            "content": assistant_content,
            "tool_calls": tool_calls_param,
        }

        self.messages.append(assistant_message)

        # Build the shared LLMResponse
        content: list[ToolUseBlock | str] = []
        if assistant_content:
            self.log.debug("Assistant content after stripping tool calls:\n%s", assistant_content)
            content.append(assistant_content)
        for tid, name, args in tool_calls:
            content.append(ToolUseBlock(id=tid, tool_name=name, input=args))

        # If we found tool calls via text parsing, override finish_reason → tool_use
        if tool_calls and finish_reason == "stop":
            stop_reason: StopReason = "tool_use"
        else:
            stop_reason = _FINISH_REASON_MAP.get(finish_reason, "unknown")

        return LLMResponse(raw=str(response), content=content, stop_reason=stop_reason)

    def store_tool_results(self, tool_use_block: ToolUseBlock, tool_result: str) -> None:
        # OpenAI expects one message per tool result (no batching required)
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_use_block.id,
                "content": tool_result,
            }
        )

    def process_received_message(self, sender: str, message: str) -> None:
        self.messages.append({"role": "user", "content": f"[Message from {sender}]: {message}"})
