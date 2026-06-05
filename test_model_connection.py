"""Quick connectivity test: asks a model to say hello, with no Mininet involved."""

import argparse

from agentic_networks.agentic_network import MODELS
from agentic_networks.agent_claude import AgentClaude, MODELS as CLAUDE_MODELS
from agentic_networks.agent_openai import AgentOpenAI, MODELS as GPT_MODELS
from agentic_networks.agent_vllm import AgentVLLM


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
        agent = AgentClaude(model=model_name)
    elif model_key in GPT_MODELS:
        agent = AgentOpenAI(model=model_name)
    else:
        base_url = f"http://{args.vllm_host}:{args.vllm_port}/v1"
        agent = AgentVLLM(model=model_name, base_url=base_url)

    response = agent.request_action("Say hello.")
    print(response.extract_text())


if __name__ == "__main__":
    main()
