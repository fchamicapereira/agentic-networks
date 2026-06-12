#!/usr/bin/env python3

import argparse
import subprocess
import sys

import tomli as tomllib
from pathlib import Path

from agentic_networks.agentic_network import MODELS as AVAILABLE_MODELS

SCRIPT_DIR = Path(__file__).resolve().parent
DOCKER_RUNNER = SCRIPT_DIR / "tools" / "run_in_docker.sh"

# ANSI colors
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Fields that are metadata, not CLI arguments
_META_FIELDS = {"name", "script"}


def experiment_to_args(exp: dict, exp_args_overrides: dict) -> list[str]:
    """Convert experiment fields to CLI arguments."""
    merged = {**exp, **exp_args_overrides}
    args = []
    for key, value in merged.items():
        if key in _META_FIELDS:
            continue
        cli_flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                args.append(cli_flag)
        else:
            args.extend([cli_flag, str(value)])
    return args


def build_command(exp: dict, docker: bool, exp_args_overrides: dict) -> list[str]:
    script = exp["script"]
    exp_args = experiment_to_args(exp, exp_args_overrides)
    if docker:
        return ["bash", str(DOCKER_RUNNER), script] + exp_args
    else:
        return [sys.executable, script] + exp_args


def run_experiment(exp: dict, docker: bool, index: int, total: int, exp_args_overrides: dict) -> None:
    cmd = build_command(exp, docker, exp_args_overrides)
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  [{index}/{total}] {exp['name']}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        exit(f"Experiment '{exp['name']}' failed (exit {result.returncode})")


def load_toml(path: str) -> tuple[Path, list[dict]]:
    toml_path = Path(path)
    if not toml_path.is_absolute():
        toml_path = SCRIPT_DIR / toml_path
    if not toml_path.exists():
        exit(f"Experiments file not found: {toml_path}")
    with open(toml_path, "rb") as f:
        config = tomllib.load(f)
    experiments = config.get("experiment", [])
    if not experiments:
        exit("No [[experiment]] entries found in the TOML file.")
    return toml_path, experiments


def parse_args():
    parser = argparse.ArgumentParser(description="Run experiments from a TOML file")
    parser.add_argument("--experiments-file", default="experiments.toml", metavar="FILE", help="Path to the TOML experiments file (default: experiments.toml)")
    models = sorted(AVAILABLE_MODELS)
    parser.add_argument("--model", "-m", required=True, choices=models, metavar="MODEL", help=f"Model to use for all experiments. Choices: {{{', '.join(models)}}}")
    parser.add_argument("--filter", "-f", nargs="+", metavar="NAME", help="Run only experiments with these exact names")
    parser.add_argument("--list", "-l", action="store_true", help="List available experiment names and exit")
    parser.add_argument("--docker", "-d", action="store_true", help=f"Run each experiment via {DOCKER_RUNNER.relative_to(SCRIPT_DIR)}")
    parser.add_argument("--vllm-host", metavar="HOST", help="vLLM server host to pass to each experiment (overrides TOML value)")
    parser.add_argument("--vllm-port", metavar="PORT", type=int, help="vLLM server port to pass to each experiment (overrides TOML value)")
    return parser.parse_args()


def main():
    args = parse_args()
    _, experiments = load_toml(args.experiments_file)

    if args.list:
        print("Available experiments:")
        for exp in experiments:
            print(f"  {exp['name']}")
        return

    selected = experiments
    if args.filter:
        selected = [exp for exp in selected if exp["name"] in args.filter]
        if not selected:
            exit(f"No experiments found with names: {args.filter}")

    overrides = {"model": args.model}
    if args.vllm_host is not None:
        overrides["vllm_host"] = args.vllm_host
    if args.vllm_port is not None:
        overrides["vllm_port"] = args.vllm_port

    print(f"Running {len(selected)} experiment(s)" + (f" in Docker via {DOCKER_RUNNER.relative_to(SCRIPT_DIR)}" if args.docker else ""))

    for i, exp in enumerate(selected, 1):
        run_experiment(exp, docker=args.docker, index=i, total=len(selected), exp_args_overrides=overrides)

    print(f"\n{BOLD}{CYAN}All {len(selected)} experiment(s) completed successfully.{RESET}")


if __name__ == "__main__":
    main()
