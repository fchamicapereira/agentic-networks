#!/usr/bin/env python3

import argparse
import os
import sys

MODELS = {
    "qwen2.5-72b-awq": {
        "id": "Qwen/Qwen2.5-72B-Instruct-AWQ",
        "tool_call_parser": "hermes",
        "description": "Qwen 2.5 72B (AWQ 4-bit) — current default, ~36GB",
    },
    "qwen2.5-72b-gptq": {
        "id": "Qwen/Qwen2.5-72B-Instruct-GPTQ-Int4",
        "tool_call_parser": "hermes",
        "description": "Qwen 2.5 72B (GPTQ Int4) — better quality than AWQ, ~36GB",
    },
    "qwq-32b": {
        "id": "Qwen/QwQ-32B",
        "tool_call_parser": "hermes",
        "description": "QwQ 32B reasoning model (FP16) — recommended, ~64GB",
    },
    "deepseek-r1-32b": {
        "id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        "tool_call_parser": "hermes",
        "reasoning_parser": "deepseek_r1",
        "description": "DeepSeek R1 distilled into Qwen 32B (FP16) — strong reasoning, ~64GB",
    },
    "llama3.3-70b-awq": {
        "id": "casperhansen/llama-3.3-70b-instruct-awq",
        "tool_call_parser": "llama3_json",
        "description": "Llama 3.3 70B (AWQ 4-bit) — ~35GB",
    },
    "deepseek-r1-70b-awq": {
        "id": "Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ",
        "tool_call_parser": None,
        "reasoning_parser": "deepseek_r1",
        "description": "DeepSeek R1 distilled into Llama 70B (AWQ 4-bit) — ~35GB",
    },
    "qwq-32b-awq": {
        "id": "Qwen/QwQ-32B-AWQ",
        "tool_call_parser": "hermes",
        "description": "QwQ 32B reasoning model (AWQ 4-bit) — fits on 1 GPU, ~18GB",
    },
    "mistral-small-24b": {
        "id": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
        "tool_call_parser": "mistral",
        "description": "Mistral Small 3.1 24B (FP16) — Apache 2.0, ~48GB FP16",
    },
    "phi-4-14b": {
        "id": "microsoft/phi-4",
        "tool_call_parser": "pythonic",
        "description": "Phi-4 14B (FP16) — MIT license, ~28GB",
    },
    "gemma-3-27b": {
        "id": "google/gemma-3-27b-it",
        "tool_call_parser": "pythonic",
        "description": "Gemma 3 27B (FP16) — ~54GB FP16",
    },
}


def select_model_interactive() -> str:
    print("Available models:\n")
    keys = list(MODELS.keys())
    for i, key in enumerate(keys):
        m = MODELS[key]
        print(f"  [{i + 1}] {key}")
        print(f"      {m['description']}")
        print(f"      HuggingFace: {m['id']}")
        print()
    while True:
        try:
            choice = input(f"Select a model [1-{len(keys)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
        except (ValueError, EOFError):
            pass
        print(f"Please enter a number between 1 and {len(keys)}.")


def build_docker_command(model_key: str, tensor_parallel: int, port: int, max_model_len: int | None) -> list[str]:
    model = MODELS[model_key]
    hf_cache = f"{os.path.expanduser('~')}/.cache/huggingface:/root/.cache/huggingface"

    cmd = ["docker", "run"]
    cmd += ["--rm", "-it"]                          # container lifecycle
    cmd += ["--runtime", "nvidia", "--gpus", "all"] # GPU access
    cmd += ["-p", f"{port}:8000", "--ipc=host"]     # networking / shared memory
    cmd += ["-v", hf_cache]                         # model cache volume
    cmd += ["vllm/vllm-openai:latest"]              # image
    cmd += ["--model", model["id"]]
    cmd += ["--tensor-parallel-size", str(tensor_parallel)]
    if model.get("tool_call_parser"):
        cmd += ["--enable-auto-tool-choice", "--tool-call-parser", model["tool_call_parser"]]
    if model.get("reasoning_parser"):
        cmd += ["--reasoning-parser", model["reasoning_parser"]]
    if max_model_len is not None:
        cmd += ["--max-model-len", str(max_model_len)]
    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Spawn a vLLM OpenAI-compatible server in Docker.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--model",
        "-m",
        choices=list(MODELS.keys()),
        help="Model to serve. If omitted, an interactive selector is shown.\nChoices:\n" + "\n".join(f"  {k}: {v['description']}" for k, v in MODELS.items()),
    )
    parser.add_argument(
        "--tensor-parallel-size",
        "-tp",
        type=int,
        default=2,
        metavar="N",
        help="Number of GPUs for tensor parallelism (default: 2)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Host port to bind (default: 8000)",
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=None,
        metavar="N",
        help="Maximum sequence length (tokens). If omitted, uses the model's default.\nUseful when GPUs lack enough memory for the model's full context length.",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available models and exit",
    )
    args = parser.parse_args()

    if args.list:
        for key, m in MODELS.items():
            print(f"{key}\n  {m['description']}\n  HuggingFace: {m['id']}\n")
        sys.exit(0)

    model_key = args.model or select_model_interactive()
    cmd = build_docker_command(model_key, args.tensor_parallel_size, args.port, args.max_model_len)

    print(f"\nStarting: {MODELS[model_key]['id']}")
    print(f"Command:  {' '.join(cmd)}\n")
    os.execvp("docker", cmd)


if __name__ == "__main__":
    main()
