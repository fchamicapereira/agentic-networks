"""Quick connectivity test: initializes a model client and asks it to say hello."""

import argparse
import os

from agentic_networks.agentic_network import MODELS
from agentic_networks.agent_claude import MODELS as CLAUDE_MODELS
from agentic_networks.agent_claude import anthropic
from agentic_networks.agent_openai import MODELS as GPT_MODELS
from agentic_networks.agent_openai import OpenAI
from agentic_networks.agent_vllm import MODELS as VLLM_MODELS
from agentic_networks.agent_vllm import check_server


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
        if "ANTHROPIC_API_KEY" not in os.environ:
            print("Error: ANTHROPIC_API_KEY is not set.")
            return
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model_name,
            max_tokens=64,
            messages=[{"role": "user", "content": "Say hello."}],
        )
        print("\n".join(b.text for b in response.content if b.type == "text"))

    elif model_key in GPT_MODELS:
        if "OPENAI_API_KEY" not in os.environ:
            print("Error: OPENAI_API_KEY is not set.")
            return
        client = OpenAI()
        response = client.chat.completions.create(
            model=model_name,
            max_tokens=64,
            messages=[{"role": "user", "content": "Say hello."}],
        )
        print(response.choices[0].message.content)

    else:  # VLLM
        base_url = f"http://{args.vllm_host}:{args.vllm_port}/v1"
        if not check_server(base_url, api_key="none"):
            print(f"Error: no vLLM server responding at {base_url}")
            return
        client = OpenAI(base_url=base_url, api_key="none")
        response = client.chat.completions.create(
            model=model_name,
            max_tokens=64,
            messages=[{"role": "user", "content": "Say hello."}],
        )
        print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
