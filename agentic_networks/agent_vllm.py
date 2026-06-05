import json
import re
import uuid
import pprint
from typing import Callable

from openai import OpenAI, APIConnectionError
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionToolParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam

from .agent import AGENT_TOOLS_DEFINITIONS, LLMResponse, NodeAgent, REPORT_PROMPT, StopReason, ToolUseBlock
from .message_bus import MessageBus
from mininet.node import Host
from .network import Interface

MODELS = {
    "qwen2.5-72b-awq": "Qwen/Qwen2.5-72B-Instruct-AWQ",
    "qwen2.5-72b-gptq": "Qwen/Qwen2.5-72B-Instruct-GPTQ-Int4",
    "qwq-32b": "Qwen/QwQ-32B",
    "qwq-32b-awq": "Qwen/QwQ-32B-AWQ",
    "deepseek-r1-32b": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    "deepseek-r1-70b-awq": "Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ",
    "llama3.3-70b-awq": "casperhansen/llama-3.3-70b-instruct-awq",
    "mistral-small-24b": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
    "phi-4-14b": "microsoft/phi-4",
    "gemma-3-27b": "google/gemma-3-27b-it",
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


def _build_tool_guide() -> str:
    lines = [
        "To call a tool, output a <tool_call> block anywhere in your response:",
        '<tool_call>{"name": "<tool_name>", "arguments": {"param": "value", ...}}</tool_call>',
        "You may call multiple tools per response. Available tools:",
    ]
    for t in AGENT_TOOLS_DEFINITIONS:
        props = t["schema"].get("properties", {})
        required = set(t["schema"].get("required", []))
        sig = ", ".join((p if p in required else f"[{p}]") for p in props)
        lines.append(f"  {t['name']}({sig}) — {t['description']}")
        for pname, pinfo in props.items():
            opt = "" if pname in required else " (optional)"
            lines.append(f"    - {pname}{opt}: {pinfo['description']}")
    return "\n".join(lines)


def _split_json_objects(text: str) -> list[str]:
    """Extract top-level JSON objects from text that may contain several concatenated ones."""
    objects = []
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(text[start : i + 1])
                start = None
    return objects


def _strip_thinking(content: str) -> str:
    """Remove <think>...</think> blocks from assistant content before storing in history.

    Reasoning models (QwQ) emit multi-thousand-token thinking blocks that
    are scratch-pad reasoning — useful once, but dead weight when re-sent on every
    subsequent iteration. The tool calls extracted from the content are stored separately,
    so stripping the thinking block loses no operational information.
    """
    # Some models (QwQ) emit <think>...</think>; others (DeepSeek-R1) omit the opening tag.
    stripped = re.sub(r"(<think>)?.*?</think>", "", content, flags=re.DOTALL).strip()
    if stripped == content:
        print("Content:", content, flush=True)
        assert stripped != content, "Expected to find and strip a <think> block from the assistant content"
    return stripped


def _parse_call_tags(content: str) -> list[tuple[str, str, dict]]:
    # Tool call text format (in addition to the structured tool_calls API field):
    #   <tool_call>JSON</tool_call>  — Qwen/Hermes native and our explicit system prompt format.
    call_tag_regex = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
    results = []
    for match in call_tag_regex.finditer(content):
        try:
            data = json.loads(match.group(1))
            results.append((f"call_{uuid.uuid4().hex[:24]}", data["name"], data.get("arguments", {})))
        except (json.JSONDecodeError, KeyError):
            pass

    if results:
        return results

    # Fallback: DeepSeek-R1 and similar models emit a ```json fence containing one or
    # more bare JSON objects (not an array) with "name"/"arguments" keys.
    json_fence_regex = re.compile(r"```json\s*(.*?)```", re.DOTALL)
    for fence_match in json_fence_regex.finditer(content):
        for obj_str in _split_json_objects(fence_match.group(1)):
            try:
                data = json.loads(obj_str)
                if "name" in data:
                    results.append((f"call_{uuid.uuid4().hex[:24]}", data["name"], data.get("arguments", {})))
            except json.JSONDecodeError:
                pass

    return results


def check_server(base_url: str, api_key: str) -> bool:
    """Return True if the OpenAI-compatible server is reachable and responding."""
    try:
        OpenAI(base_url=base_url, api_key=api_key).models.list()
        return True
    except APIConnectionError:
        return False


class AgentVLLM(NodeAgent):
    """NodeAgent backed by a local OpenAI-compatible API (vLLM, Ollama, etc.)."""

    def __init__(
        self,
        node_name: str,
        host: Host,
        bus: MessageBus,
        initial_prompt: str,
        model: str,
        max_iterations: int,
        max_tokens: int,
        base_url: str,
        api_key: str,
        ifaces: list[Interface],
        window_size: int = 0,
        extra_tools: list[dict] | None = None,
        context_fn: "Callable[[], str] | None" = None,
    ):
        # Append the tool guide so every model can fall back to text-based calls.
        augmented_prompt = f"{initial_prompt.rstrip()}\n\n{_build_tool_guide()}"
        super().__init__(
            node_name,
            host,
            bus,
            augmented_prompt,
            model,
            max_iterations,
            max_tokens,
            ifaces,
            extra_tools=extra_tools,
            context_fn=context_fn,
        )
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.messages: list[ChatCompletionMessageParam] = []
        self.window_size = window_size

    def _windowed_messages(self) -> list[ChatCompletionMessageParam]:
        msgs = self.messages
        if not self.window_size or len(msgs) <= self.window_size:
            return msgs
        trimmed = list(msgs[-self.window_size :])
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

    def _do_completion(self, messages: list[ChatCompletionMessageParam]) -> tuple:
        """Call the model and return (response, msg, finish_reason, tool_calls, assistant_content)."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tools=self._all_tools(),
            messages=messages,
        )
        assert len(response.choices) == 1, "Expected exactly one choice from the model"
        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        assistant_content = msg.content
        content = msg.content or ""

        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            self.log.info("[reasoning]\n%s", reasoning)

        tool_calls: list[tuple[str, str, dict]] = []

        # Path A: structured tool_calls field (standard OpenAI / vLLM --enable-auto-tool-choice)
        if msg.tool_calls:
            tool_calls = [(tc.id, tc.function.name, json.loads(tc.function.arguments)) for tc in msg.tool_calls if isinstance(tc, ChatCompletionMessageToolCall)]
        # Path B: text-based tool calls — <tool_call> tags (Qwen/Hermes) or ```json``` fences (DeepSeek-R1)
        else:
            tool_calls = _parse_call_tags(content)

        return response, msg, finish_reason, tool_calls, assistant_content

    def request_action_from_model(self) -> LLMResponse:
        # Don't inject a user turn if the last message is already a tool result —
        # Mistral (and some other models) reject user → tool → user sequences.
        if not self.messages or self.messages[-1]["role"] != "tool":
            context = self.context_fn() if self.context_fn else ""
            action_text = f"{context}\n\nState the next action." if context else "State the next action."
            self.messages.append({"role": "user", "content": action_text})

        # System prompt is prepended on every call; not stored in self.messages
        # so the history stays clean (user/assistant/tool turns only).
        system_message: ChatCompletionMessageParam = {"role": "system", "content": self.initial_prompt}
        full_messages: list[ChatCompletionMessageParam] = [system_message] + self._windowed_messages()

        self.log.debug("Messages sent to model:\n%s", pprint.pformat(full_messages, indent=2))
        response, _, finish_reason, tool_calls, assistant_content = self._do_completion(full_messages)

        if assistant_content and ("<think>" in assistant_content or "</think>" in assistant_content):
            assistant_content = _strip_thinking(assistant_content)

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

        # If the model produced text but no tool calls, inject a brief warning.
        if not tool_calls and finish_reason == "stop" and (assistant_content or "").strip():
            self.log.warning("No tool call detected in response. Injecting feedback for next iteration.")
            self.messages.append(
                {
                    "role": "user",
                    "content": (
                        "Warning: your last response contained no tool call. "
                        "You MUST issue a tool call for every action, including report_done. "
                        "Plain text descriptions of actions are ignored — only tool calls are executed."
                    ),
                }
            )

        content: list[ToolUseBlock | str] = []
        if assistant_content:
            content.append(assistant_content)
        for tid, name, args in tool_calls:
            content.append(ToolUseBlock(id=tid, tool_name=name, input=args))

        # If we found tool calls via text parsing, override finish_reason → tool_use
        if tool_calls and finish_reason == "stop":
            stop_reason: StopReason = "tool_use"
        else:
            stop_reason = _FINISH_REASON_MAP.get(finish_reason, "unknown")

        return LLMResponse(raw=str(response), content=content, stop_reason=stop_reason)

    def store_tool_results(self, tool_use_block: ToolUseBlock, tool_result: str):
        # OpenAI expects one message per tool result (no batching required)
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
        content = response.choices[0].message.content or ""
        if "<think>" in content or "</think>" in content:
            content = _strip_thinking(content)
        return content
