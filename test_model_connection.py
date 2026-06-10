#!/usr/bin/env python3

import argparse

from agentic_networks.agentic_network import MODELS
from agentic_networks.agent_claude import AgentClaude, MODELS as CLAUDE_MODELS
from agentic_networks.agent_openai import AgentOpenAI, MODELS as GPT_MODELS
from agentic_networks.agent_vllm import AgentVLLM, MODELS as VLLM_MODELS


def main():
    parser = argparse.ArgumentParser(description="Test model connectivity")
    parser.add_argument("--model", "-m", required=True, choices=list(MODELS.keys()))
    parser.add_argument("--vllm-host", default="localhost")
    parser.add_argument("--vllm-port", type=int, default=8000)
    args = parser.parse_args()

    model_key = args.model
    model_name = MODELS[model_key]

    print(f"Testing model: {model_key} ({model_name})")

    if model_key in CLAUDE_MODELS:
        agent = AgentClaude(model_name, "test")
    elif model_key in GPT_MODELS:
        agent = AgentOpenAI(model_name, "test")
    elif model_key in VLLM_MODELS:
        agent = AgentVLLM(model_name, "test", args.vllm_host, args.vllm_port)
    else:
        print(f"Unknown model key: {model_key}")
        exit(1)

    print(agent.query("Say hello."))


if __name__ == "__main__":
    main()
