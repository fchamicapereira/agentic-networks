import json
import logging
import re
import uuid
import pprint

from openai import OpenAI, APIConnectionError
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionToolParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam

from .agent import Agent, LLMResponse, REPORT_PROMPT, StopReason, ToolUseBlock
from .agent import DEFAULT_SYSTEM_PROMPT, DEFAULT_MAX_TOKENS, DEFAULT_TOOL_DEFS, DEFAULT_WINDOW_SIZE

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

_FINISH_REASON_MAP: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}

_VERBOSE_THRESHOLD_WORDS = 100  # untagged content longer than this gets summarized
_VLLM_CONTEXT_LIMIT = 40_960  # token context window for vLLM models
_HISTORY_COMPRESS_AT = 0.70  # compress when history exceeds this fraction of the limit
_SUMMARIZER_INPUT_CAP_TOKENS = 20_000  # beyond this, summarizer input is trimmed to first+last halves

# Conservative word↔token conversion: actual average is ~1.33 tokens/word for English prose,
# but technical/network output skews higher. Overestimating prevents exceeding the token budget.
_TOKENS_PER_WORD = 1.5

_SUMMARIZER_SYSTEM_PROMPT = (
    "You are a reasoning summarizer. When given the internal thinking of an AI agent, "
    "write a concise first-person summary covering: (1) what was observed, "
    "(2) what was decided, and (3) why. "
    "Do not restate known context — focus only on what is specific to this step. "
    "Be brief and direct."
)

_HISTORY_SUMMARIZER_SYSTEM_PROMPT = (
    "You are summarizing the decision history of an autonomous AI agent. "
    "Write a concise first-person summary covering: (1) the overall goal established, "
    "(2) the key decisions made and their outcomes so far, and "
    "(3) the current state of the system. "
    "Be brief and factual. Do not re-explain the task setup."
)

_LOG_SUMMARIZER_SYSTEM_PROMPT = (
    "You are summarizing a network agent's activity log. "
    "Write a concise first-person summary covering: (1) what the agent's goal was, "
    "(2) the key actions taken and their outcomes (routing changes, traffic measurements, "
    "messages sent/received), and (3) the final configuration state. "
    "Include specific values, addresses, and metrics where relevant. "
    "Be factual and direct."
)


def _count_tokens(text: str) -> int:
    """Conservative token count estimate for a string. Overestimates to prevent exceeding budget."""
    return int(len(text.split()) * _TOKENS_PER_WORD)


def _tokens_to_words(token_count: int) -> int:
    """Convert a token budget to a conservative word-count limit."""
    return int(token_count / _TOKENS_PER_WORD)


def _build_tool_guide(tool_defs: list[dict]) -> str:
    lines = [
        "To call a tool, output a <tool_call> block anywhere in your response:",
        '<tool_call>{"name": "<tool_name>", "arguments": {"param": "value", ...}}</tool_call>',
        "You may call multiple tools per response. Available tools:",
    ]
    for t in tool_defs:
        props = t["schema"].get("properties", {})
        required = set(t["schema"].get("required", []))
        sig = ", ".join((p if p in required else f"[{p}]") for p in props)
        lines.append(f"  {t['name']}({sig}) — {t['description']}")
        for pname, pinfo in props.items():
            opt = "" if pname in required else " (optional)"
            lines.append(f"    - {pname}{opt}: {pinfo['description']}")
    return "\n".join(lines)


def _split_json_objects(text: str) -> list[str]:
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


class _Summarizer:
    """Shared base: calls the model with no tools, strips its own <think> block,
    returns only the after-</think> answer, or None if no clean answer exists."""

    _max_tokens: int = 512
    _system_prompt: str = ""

    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model
        self._log = logging.getLogger(__name__)

    def summarize(self, text: str) -> str:
        if _count_tokens(text) > _SUMMARIZER_INPUT_CAP_TOKENS:
            half = _tokens_to_words(_SUMMARIZER_INPUT_CAP_TOKENS) // 2
            words = text.split()
            text = " ".join(words[:half]) + "\n...[middle omitted]...\n" + " ".join(words[-half:])
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": text},
                ],
            )
            raw = response.choices[0].message.content or ""
        except Exception as exc:
            raise RuntimeError(f"summarizer API call failed: {exc}") from exc

        match = re.search(r"(?:<think>)?(.*?)</think>(.*)", raw, re.DOTALL)
        if match:
            answer = match.group(2).strip()
            if answer:
                return answer
            failure = "produced a </think> block but wrote no summary after it"
        else:
            answer = raw.strip()
            if answer:
                # No </think> — model answered directly without think tags
                return answer
            failure = "produced an empty response"

        self._log.error(
            "[summarizer %s]\n--- input ---\n%s\n--- raw output ---\n%s",
            failure, text, raw,
        )
        raise RuntimeError(f"summarizer {failure}")


class ThinkingSummarizer(_Summarizer):
    """Condenses a single verbose reasoning block into a brief first-person summary."""

    _max_tokens = 4096
    _system_prompt = _SUMMARIZER_SYSTEM_PROMPT


class HistorySummarizer(_Summarizer):
    """Condenses the full accumulated conversation history into a compact summary."""

    _max_tokens = 4096
    _system_prompt = _HISTORY_SUMMARIZER_SYSTEM_PROMPT


class LogSummarizer(_Summarizer):
    """Condenses a node activity log into a compact summary for final report generation."""

    _max_tokens = 4096
    _system_prompt = _LOG_SUMMARIZER_SYSTEM_PROMPT


def _serialize_messages(messages: list[ChatCompletionMessageParam]) -> str:
    """Flatten a message list to a readable text dump for the history summarizer."""
    parts = []
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content") or ""
        if content:
            parts.append(f"[{role}]: {content}")
    return "\n\n".join(parts)


def _parse_call_tags(content: str) -> list[tuple[str, str, dict]]:
    # Tool call text format: <tool_call>JSON</tool_call>  — Qwen/Hermes native format.
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


class AgentVLLM(Agent):
    """Agent backed by a local OpenAI-compatible API (vLLM, Ollama, etc.)."""

    def __init__(
        self,
        model: str,
        base_url: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tool_defs: list[dict] | None = DEFAULT_TOOL_DEFS,
        window_size: int = DEFAULT_WINDOW_SIZE,
        temperature: float = 0.3,
    ):
        # Augment the system prompt with a text-based tool guide so local models
        # can fall back to <tool_call> tags if structured tool_calls fails.
        augmented_prompt = f"{system_prompt.rstrip()}\n\n{_build_tool_guide(tool_defs or [])}"
        super().__init__(model, augmented_prompt, max_tokens, tool_defs, window_size)
        self.temperature = temperature

        self.log = logging.getLogger(__name__)
        if not check_server(base_url, api_key="none"):
            print(f"Error: no vLLM server responding at {base_url}")
            exit(1)
        self.client = OpenAI(base_url=base_url, api_key="none")
        self._summarizer = ThinkingSummarizer(self.client, self.model)
        self._history_summarizer = HistorySummarizer(self.client, self.model)
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

    def _strip_thinking(self, content: str) -> str:
        """Replace <think> blocks with a concise first-person summary."""
        if "<think>" in content or "</think>" in content:
            match = re.search(r"(?:<think>)?(.*?)</think>(.*)", content, re.DOTALL)
            if match:
                thinking, after = match.group(1).strip(), match.group(2).strip()
                self.log.debug("[thinking]\n%s", thinking)
                summary = self._summarizer.summarize(thinking)
                self.log.info("[thinking summarized: %d → %d chars]", len(thinking), len(summary))
                return f"{summary}\n{after}".strip() if after else summary
            # Malformed tags — strip whatever we can
            return re.sub(r"(<think>)?.*?</think>", "", content, flags=re.DOTALL).strip()

        if len(content.split()) > _VERBOSE_THRESHOLD_WORDS:
            summary = self._summarizer.summarize(content)
            self.log.info("[content summarized: %d → %d chars]", len(content), len(summary))
            return summary

        return content

    def _maybe_compress_history(self) -> None:
        """Compress self.messages into a single summary when approaching the context limit."""
        estimated_tokens = _count_tokens(self.system_prompt) + sum(_count_tokens(str(m.get("content", ""))) for m in self.messages)
        if estimated_tokens < int(_VLLM_CONTEXT_LIMIT * _HISTORY_COMPRESS_AT):
            return

        n = len(self.messages)
        history_text = _serialize_messages(self.messages)
        summary = self._history_summarizer.summarize(history_text)
        self.messages = [
            {"role": "user", "content": "What is the context from prior iterations?"},
            {"role": "assistant", "content": f"[History compressed — {n} messages]\n\n{summary}"},
        ]
        msg = f"[history compressed: {n} messages, {len(history_text)} → {len(summary)} chars]"
        print(msg, flush=True)
        self.log.info(msg)

    def _windowed_messages(self) -> list[ChatCompletionMessageParam]:
        msgs = self.messages
        if not self.window_size or len(msgs) <= self.window_size:
            return msgs
        trimmed = list(msgs[-self.window_size :])
        while trimmed and trimmed[0]["role"] != "user":
            trimmed.pop(0)
        return trimmed

    def _do_completion(self, messages: list[ChatCompletionMessageParam]) -> tuple:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            tools=self._tools,
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

    def request_action(self, user_message: str) -> LLMResponse:
        self._maybe_compress_history()

        # Don't inject a user turn if the last message is already a tool result —
        # Mistral (and some other models) reject user → tool → user sequences.
        if not self.messages or self.messages[-1]["role"] != "tool":
            self.messages.append({"role": "user", "content": user_message})

        system_message: ChatCompletionMessageParam = {"role": "system", "content": self.system_prompt}
        full_messages: list[ChatCompletionMessageParam] = [system_message] + self._windowed_messages()

        self.log.debug("Messages sent to model:\n%s", pprint.pformat(full_messages, indent=2))
        response, _, finish_reason, tool_calls, assistant_content = self._do_completion(full_messages)

        if assistant_content:
            assistant_content = self._strip_thinking(assistant_content)

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
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
        )
        content = response.choices[0].message.content or ""
        return self._strip_thinking(content)
