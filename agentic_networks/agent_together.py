import os
import sys

from openai import OpenAI

from .agent import Agent, DEFAULT_SYSTEM_PROMPT, DEFAULT_MAX_TOKENS, DEFAULT_TOOL_DEFS, DEFAULT_WINDOW_SIZE
from .agent_vllm import (
    AgentVLLM,
    HistorySummarizer,
    LogSummarizer,
    ThinkingSummarizer,
    _build_tool_guide,
    _sampling_for_model,
    fetch_context_limit,
    _MAX_REQUEST_RETRIES,
    _REQUEST_TIMEOUT_SECONDS,
)

TOGETHER_API_KEY_ENV_VAR = "TOGETHER_API_KEY"

# Together.ai's inference endpoint is OpenAI-compatible (Chat Completions), so we speak to it
# with the same client and message/tool handling as a self-hosted vLLM server — only the base
# URL and authentication differ (a hosted API with a key, rather than a local host:port).
TOGETHER_BASE_URL = "https://api.together.xyz/v1"

MODELS = {
    # Together's catalog names models as "<org>/<Model>"; GLM is published by Z.ai (zai-org).
    "glm-5.2": "zai-org/GLM-5.2",
}


class AgentTogether(AgentVLLM):
    """Agent backed by Together.ai's OpenAI-compatible Chat Completions API.

    Together hosts open-weight models (GLM, Qwen, Llama, ...) behind the same wire
    protocol as vLLM, so this reuses every method of AgentVLLM (tool-call parsing,
    history compression, thinking summarization, reporting). Only the client setup
    differs: a hosted endpoint reached over HTTPS with an API key instead of a local
    vLLM server on host:port with no auth. AgentVLLM.__init__ is vLLM-specific
    (host/port + check_server + api_key="none"), so we replicate the small, shared
    tail of its setup here rather than calling it.
    """

    def __init__(
        self,
        model: str,
        name: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tool_defs: list[dict] = DEFAULT_TOOL_DEFS,
        window_size: int = DEFAULT_WINDOW_SIZE,
        temperature: float = 0.3,
    ):
        augmented_prompt = f"{system_prompt.rstrip()}\n\n{_build_tool_guide(tool_defs or [])}"
        Agent.__init__(self, model, name, augmented_prompt, max_tokens, tool_defs, window_size)
        self.temperature = temperature
        self._sampling = _sampling_for_model(model, temperature)

        api_key = os.environ.get(TOGETHER_API_KEY_ENV_VAR, "").strip()
        if not api_key:
            self.log.error("%s environment variable is not set.", TOGETHER_API_KEY_ENV_VAR)
            sys.exit(1)

        self.client = OpenAI(
            base_url=TOGETHER_BASE_URL,
            api_key=api_key,
            timeout=_REQUEST_TIMEOUT_SECONDS,
            max_retries=_MAX_REQUEST_RETRIES,
        )
        self.context_limit = fetch_context_limit(self.client, self.model)
        self.log.info("Together context window for %s: %d tokens", self.model, self.context_limit)
        self.log.info("Sampling for %s: %s", self.model, self._sampling)
        self.thinking_summarizer = ThinkingSummarizer(self.client, self.model)
        self.history_summarizer = HistorySummarizer(self.client, self.model)
        self.log_summarizer = LogSummarizer(self.client, self.model)
        self.messages = []
        self._tools = [
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
