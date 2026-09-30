#!/usr/bin/env python3
"""
regen_final_report.py — Re-run only the final-report generation for finished experiments.

An experiment persists everything the final report is built from: the per-node logs
('{run_stem}-{node}.log'), the agent self-reports ('{run_stem}-{node}-report.md') and the
connectivity matrix plus routing tables ('{run_stem}.txt'). This tool reconstructs that
context from disk and re-queries the model with the current 'final-report.txt' prompt,
overwriting '{run_stem}-final-report.md'. Nothing is re-simulated — no Mininet, no sudo.

Useful after editing a final-report prompt: the existing runs can be re-judged under the
new prompt without spending a full experiment per model.

By default the report is generated with the same model that ran the experiment (inferred
from the run stem), matching what the experiment itself does. --report-model overrides it,
e.g. to judge every run with one strong model.

Usage:
    # every run under logs/optimizing_billing_policy, each judged by its own model
    python tools/regen_final_report.py logs/optimizing_billing_policy

    # both billing experiments, only the local models, judged by opus
    python tools/regen_final_report.py logs/optimizing_billing_policy logs/optimizing_billing_policy_oracle \
        --model qwq-32b qwen2.5-72b-awq --report-model opus-4-7

    # see what would run, without querying anything
    python tools/regen_final_report.py logs/optimizing_billing_policy --dry-run

vLLM-backed models need a live server (--vllm-host/--vllm-port); Claude/GPT models need
their API keys in the environment, as in a normal run.
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic_networks.agentic_network import MODELS
from agentic_networks.network_agent import AgentResult
from agentic_networks.experiment import collect_node_logs, setup_logging, write_final_report

DEFAULT_PROMPTS_ROOT = REPO_ROOT / "prompts"

# "Agent run complete. Final report: AgentResult(success=True, message='...')" — the last
# such record in a node log is that node's outcome.
_RESULT_RE = re.compile(r"Final report: AgentResult\(success=(True|False), message=(['\"])(.*?)\2\)", re.DOTALL)


def find_runs(log_dir: Path) -> list[str]:
    """Run stems in a log directory, identified by their '{run_stem}.txt' summary."""
    return sorted(p.stem for p in log_dir.glob("*.txt"))


def infer_model_key(run_stem: str) -> str | None:
    """Recover the model key from a run stem ('{prompts_dir}-{model}-{topology}').

    Model keys may themselves contain dashes, so match against the known keys and keep the
    longest hit ('qwq-32b-awq' must win over 'qwq-32b').
    """
    matches = [key for key in MODELS if f"-{key}-" in run_stem]
    return max(matches, key=len) if matches else None


def parse_sections(summary: Path) -> tuple[str, dict[str, str]]:
    """Split '{run_stem}.txt' back into the connectivity matrix and per-node routing tables."""
    text = summary.read_text()
    conn_part, _, routing_part = text.partition("=== Routing Tables ===")
    connectivity = conn_part.replace("=== Connectivity Matrix ===", "", 1).strip()

    route_tables: dict[str, str] = {}
    name = None
    lines: list[str] = []
    for line in routing_part.splitlines():
        header = re.fullmatch(r"--- (\S+) ---", line.strip())
        if header:
            if name:
                route_tables[name] = "\n".join(lines).strip()
            name, lines = header.group(1), []
        elif name:
            lines.append(line)
    if name:
        route_tables[name] = "\n".join(lines).strip()

    return connectivity, route_tables


def parse_agent_results(log_dir: Path, run_stem: str, nodes: list[str]) -> dict[str, AgentResult]:
    results: dict[str, AgentResult] = {}
    for node in nodes:
        log = log_dir / f"{run_stem}-{node}.log"
        found = _RESULT_RE.findall(log.read_text()) if log.exists() else []
        if found:
            success, _, message = found[-1]
            results[node] = AgentResult(success=success == "True", message=message)
        else:
            # Agents told never to terminate (e.g. ISP here) end without emitting a result.
            results[node] = AgentResult(success=False, message="Max iterations reached without completion")
    return results


def load_agent_reports(log_dir: Path, run_stem: str) -> dict[str, str]:
    """Per-node self-reports. '{run_stem}-final-report.md' matches the same glob — it is the
    output we are about to overwrite, not a node, so it is excluded."""
    reports = {}
    for path in sorted(log_dir.glob(f"{run_stem}-*-report.md")):
        if path.name == f"{run_stem}-final-report.md":
            continue
        node = path.stem[len(run_stem) + 1 : -len("-report")]
        reports[node] = path.read_text()
    return reports


def regen(log_dir: Path, run_stem: str, args, logger) -> None:
    model_key = infer_model_key(run_stem)
    if model_key is None:
        print(f"  [skip] {run_stem}: cannot infer the model from the run stem")
        return
    if args.model and model_key not in args.model:
        return

    prompts_dir = Path(args.prompts_dir) if args.prompts_dir else DEFAULT_PROMPTS_ROOT / log_dir.name
    prompt_file = prompts_dir / "final-report.txt"
    if not prompt_file.exists():
        print(f"  [skip] {run_stem}: no final-report.txt in {prompts_dir}")
        return

    agent_reports = load_agent_reports(log_dir, run_stem)
    nodes = sorted(agent_reports)
    if not nodes:
        print(f"  [skip] {run_stem}: no agent self-reports found")
        return

    summary = log_dir / f"{run_stem}.txt"
    connectivity, route_tables = parse_sections(summary)
    node_logs = collect_node_logs(log_dir, run_stem, nodes)
    agent_results = parse_agent_results(log_dir, run_stem, nodes)
    report_model = args.report_model or model_key

    if args.dry_run:
        print(f"  [dry-run] {run_stem}: {len(nodes)} nodes, prompt {prompt_file}, report model {report_model}")
        return

    write_final_report(
        model_key=report_model,
        vllm_host=args.vllm_host,
        vllm_port=args.vllm_port,
        max_tokens=args.max_tokens,
        final_prompt=prompt_file.read_text(),
        agent_reports=agent_reports,
        agent_results=agent_results,
        node_logs=node_logs,
        connectivity=connectivity,
        route_tables=route_tables,
        log_dir=log_dir,
        run_stem=run_stem,
        logger=logger,
    )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("log_dirs", nargs="+", type=Path, metavar="LOG_DIR", help="Experiment log directories (e.g. logs/optimizing_billing_policy)")
    parser.add_argument("--model", "-m", nargs="+", choices=list(MODELS.keys()), metavar="MODEL", help="Only regenerate runs of these models (default: all runs found)")
    parser.add_argument("--report-model", default=None, choices=list(MODELS.keys()), metavar="MODEL", help="Model used to write the report (default: the model that ran the experiment)")
    parser.add_argument("--prompts-dir", default=None, metavar="DIR", help="Prompts directory holding final-report.txt (default: prompts/<log dir name>)")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--vllm-host", default="localhost", metavar="HOST")
    parser.add_argument("--vllm-port", type=int, default=8000, metavar="PORT")
    parser.add_argument("--dry-run", action="store_true", help="List what would be regenerated without querying any model")
    parser.add_argument("--log-level", default="INFO", metavar="LEVEL")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = setup_logging(args.log_level)

    for log_dir in args.log_dirs:
        if not log_dir.is_dir():
            print(f"[skip] {log_dir}: not a directory")
            continue
        runs = find_runs(log_dir)
        if not runs:
            print(f"[skip] {log_dir}: no runs found")
            continue
        print(f"{log_dir}: {len(runs)} run(s)")
        for run_stem in runs:
            regen(log_dir, run_stem, args, logger)


if __name__ == "__main__":
    main()
