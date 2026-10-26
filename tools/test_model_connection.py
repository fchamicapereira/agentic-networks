#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path

from agentic_networks.agentic_network import MODELS
from agentic_networks.agent_claude import AgentClaude, MODELS as CLAUDE_MODELS
from agentic_networks.agent_openai import AgentOpenAI, MODELS as GPT_MODELS
from agentic_networks.agent_vllm import AgentVLLM, MODELS as VLLM_MODELS
from agentic_networks.agent_together import AgentTogether, MODELS as TOGETHER_MODELS


RESULTS_PREFIX = "MODEL_CHECK_RESULTS "


def connect(model_key: str, vllm_host: str, vllm_port: int):
    model_name = MODELS[model_key]
    if model_key in CLAUDE_MODELS:
        return AgentClaude(model_name, "test")
    if model_key in GPT_MODELS:
        return AgentOpenAI(model_name, "test")
    if model_key in VLLM_MODELS:
        return AgentVLLM(model_name, "test", vllm_host, vllm_port)
    if model_key in TOGETHER_MODELS:
        return AgentTogether(model_name, "test")
    raise ValueError(f"Unknown model key: {model_key}")


def main():
    parser = argparse.ArgumentParser(description="Test model connectivity")
    parser.add_argument("--model", "-m", required=True, nargs="+", choices=list(MODELS.keys()))
    parser.add_argument("--vllm-host", default="localhost")
    parser.add_argument("--vllm-port", type=int, default=8000)
    parser.add_argument("--json", action="store_true",
                        help=f"End with one line, {RESULTS_PREFIX!r} + JSON {{model: error or null}}, for programs (demo/server.py)")
    args = parser.parse_args()

    errors: dict[str, str | None] = {}
    for model_key in args.model:
        print(f"Testing model: {model_key} ({MODELS[model_key]})")
        try:
            print(connect(model_key, args.vllm_host, args.vllm_port).query("Say hello."))
            errors[model_key] = None
        except (Exception, SystemExit) as exc:  # report every model, then fail at the end (a missing key exits)
            print(f"FAILED: {exc.__class__.__name__}: {exc}")
            errors[model_key] = f"{exc.__class__.__name__}: {exc}"
    if args.json:
        print(RESULTS_PREFIX + json.dumps(errors), flush=True)
    failed = [m for m, e in errors.items() if e]
    if failed:
        exit(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
