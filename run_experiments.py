#!/usr/bin/env python3
import argparse
import subprocess
import sys

import tomli as tomllib
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DOCKER_RUNNER = SCRIPT_DIR / "tools" / "run_in_docker.sh"

# ANSI colors
CYAN  = "\033[96m"
BOLD  = "\033[1m"
RESET = "\033[0m"

# Fields that are metadata, not CLI arguments
_META_FIELDS = {"name", "script"}


def experiment_to_args(exp: dict) -> list[str]:
    """Convert experiment fields to CLI arguments."""
    args = []
    for key, value in exp.items():
        if key in _META_FIELDS:
            continue
        cli_flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                args.append(cli_flag)
        else:
            args.extend([cli_flag, str(value)])
    return args


def build_command(exp: dict, docker: bool) -> list[str]:
    script = exp["script"]
    exp_args = experiment_to_args(exp)
    if docker:
        return ["bash", str(DOCKER_RUNNER), script] + exp_args
    else:
        return [sys.executable, script] + exp_args


def run_experiment(exp: dict, docker: bool, index: int, total: int) -> None:
    cmd = build_command(exp, docker)
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  [{index}/{total}] {exp['name']}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        sys.exit(f"Experiment '{exp['name']}' failed (exit {result.returncode})")


def load_toml(path: str) -> tuple[Path, list[dict]]:
    toml_path = Path(path)
    if not toml_path.is_absolute():
        toml_path = SCRIPT_DIR / toml_path
    if not toml_path.exists():
        sys.exit(f"Experiments file not found: {toml_path}")
    with open(toml_path, "rb") as f:
        config = tomllib.load(f)
    experiments = config.get("experiment", [])
    if not experiments:
        sys.exit("No [[experiment]] entries found in the TOML file.")
    return toml_path, experiments


def parse_args(experiments: list[dict]):
    models = sorted({exp["model"] for exp in experiments if "model" in exp})
    model_help = f"Run only experiments whose model contains any of these substrings (available: {', '.join(models)})"

    parser = argparse.ArgumentParser(description="Run experiments from a TOML file")
    parser.add_argument("--experiments-file", "-f", default="experiments.toml",
                        metavar="FILE", help="Path to the TOML experiments file (default: experiments.toml)")
    parser.add_argument("--filter", "-e", nargs="+", metavar="NAME",
                        help="Run only experiments whose name contains any of these substrings")
    parser.add_argument("--model", "-m", nargs="+", metavar="MODEL", help=model_help)
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available experiment names and exit")
    parser.add_argument("--docker", "-d", action="store_true",
                        help=f"Run each experiment via {DOCKER_RUNNER.relative_to(SCRIPT_DIR)}")
    return parser.parse_args()


def main():
    # Load TOML first so we can populate the --model help text with available models.
    # Use a pre-parse to extract --experiments-file before building the real parser.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--experiments-file", "-f", default="experiments.toml")
    pre_args, _ = pre.parse_known_args()

    _, experiments = load_toml(pre_args.experiments_file)
    args = parse_args(experiments)

    # Re-load in case --experiments-file was explicitly overridden from the default.
    _, experiments = load_toml(args.experiments_file)

    if args.list:
        print("Available experiments:")
        for exp in experiments:
            print(f"  {exp['name']}")
        return

    selected = experiments
    if args.filter:
        selected = [exp for exp in selected if any(f in exp["name"] for f in args.filter)]
        if not selected:
            sys.exit(f"No experiments matched name filter: {args.filter}")
    if args.model:
        selected = [exp for exp in selected if any(f in exp.get("model", "") for f in args.model)]
        if not selected:
            sys.exit(f"No experiments matched model filter: {args.model}")

    print(f"Running {len(selected)} experiment(s)" +
          (f" in Docker via {DOCKER_RUNNER.relative_to(SCRIPT_DIR)}" if args.docker else ""))

    for i, exp in enumerate(selected, 1):
        run_experiment(exp, docker=args.docker, index=i, total=len(selected))

    print(f"\n{BOLD}{CYAN}All {len(selected)} experiment(s) completed successfully.{RESET}")


if __name__ == "__main__":
    main()
