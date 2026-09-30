"""Shared utilities for experiment entry-point scripts."""

import logging
import os
import re

from pathlib import Path
from typing import Iterable

from tqdm import tqdm
from mininet.log import setLogLevel

from .network_agent import AgentResult
from .agent_vllm import AgentVLLM, MODELS as VLLM_MODELS
from .agent_claude import AgentClaude, MODELS as CLAUDE_MODELS
from .agent_openai import AgentOpenAI, MODELS as GPT_MODELS
from .agent_together import AgentTogether, MODELS as TOGETHER_MODELS
from .network import Network
from .paths import LOGS_DIR
from .routes import Route
from .visualize_logs import render_logs

DEFAULT_LOG_DIR = LOGS_DIR

# The final report is a summary — it never needs the large output budget the action loop uses.
# Capping it leaves room for the input context on small-context (e.g. 32k) local models.
REPORT_MAX_TOKENS = 4096

# Matches a log record header: "HH:MM:SS  LEVEL  ...". Continuation lines (no header) belong to
# the preceding record.
_LOG_RECORD_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\s+(\w+)\s+")


class TqdmHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Write on the same stream the bars use (stderr by default). tqdm.write()
            # otherwise defaults to stdout, so the log text and the bar clear/redraw land
            # on different streams with different buffering and interleave on the TTY.
            tqdm.write(self.format(record), file=self.stream)
        except Exception:
            self.handleError(record)


def chown_to_user(path: Path) -> None:
    uid = os.environ.get("SUDO_UID")
    gid = os.environ.get("SUDO_GID")
    if not (uid and gid):
        return
    uid_i, gid_i = int(uid), int(gid)
    for dirpath, _, filenames in os.walk(path):
        os.chown(dirpath, uid_i, gid_i)
        for filename in filenames:
            os.chown(os.path.join(dirpath, filename), uid_i, gid_i)


def setup_logging(log_level: str) -> logging.Logger:
    handler = TqdmHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  [%(name)-20s]  %(levelname)s  %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logging.root.setLevel(getattr(logging, log_level))
    logging.root.addHandler(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    setLogLevel("error")  # Suppress Mininet's verbose output (incl. resource-limit warnings on Linux 5.x)
    return logging.getLogger("main")


def setup_node_logs(node_names: Iterable[str], log_dir: Path, run_stem: str) -> None:
    for name in node_names:
        handler = logging.FileHandler(log_dir / f"{run_stem}-{name}.log", mode="w")
        handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s", datefmt="%H:%M:%S"))
        node_logger = logging.getLogger(f"agent.{name}")
        node_logger.addHandler(handler)
        node_logger.propagate = False


def collect_route_tables(network: Network) -> dict[str, str]:
    return {name: host.cmd("ip route show").strip() for name, host in network.hosts.items()}


def strip_debug_records(text: str) -> str:
    """Drop DEBUG records (and their continuation lines), keeping INFO/WARNING/ERROR.

    Per-node log files contain large raw API dumps when running with --log-level DEBUG. The final
    report is built from these files, so without this filter the report would depend on console
    verbosity (and balloon past the model's context window). Filtering here keeps the debug files
    intact on disk while feeding the report only INFO-level semantic events.
    """
    kept: list[str] = []
    keeping = True
    for line in text.splitlines():
        m = _LOG_RECORD_RE.match(line)
        if m:
            keeping = m.group(1) != "DEBUG"
        if keeping:
            kept.append(line)
    return "\n".join(kept)


def collect_node_logs(log_dir: Path, run_stem: str, node_names: Iterable[str]) -> dict[str, str]:
    logs = {}
    for name in node_names:
        path = log_dir / f"{run_stem}-{name}.log"
        if path.exists():
            logs[name] = strip_debug_records(path.read_text())
    return logs


def write_timeline_html(log_dir: Path, run_stem: str, node_names: Iterable[str], logger: logging.Logger) -> None:
    """Render the per-node logs into a self-contained interactive HTML timeline."""
    log_files = [log_dir / f"{run_stem}-{name}.log" for name in node_names]
    log_files = [f for f in log_files if f.exists()]
    if not log_files:
        return
    out_path = log_dir / f"{run_stem}.html"
    render_logs(log_files, output_path=out_path)
    logger.info("Timeline HTML written to %s", out_path)


def write_agent_reports(reports: dict[str, str], log_dir: Path, run_stem: str, logger: logging.Logger) -> None:
    for name, text in reports.items():
        path = log_dir / f"{run_stem}-{name}-report.md"
        path.write_text(text)
        logger.info("Agent report written to %s", path)


def write_final_report(
    model_key: str,
    vllm_host: str,
    vllm_port: int,
    max_tokens: int,
    final_prompt: str,
    agent_reports: dict[str, str],
    agent_results: dict[str, AgentResult],
    node_logs: dict[str, str],
    connectivity: str,
    route_tables: dict[str, str],
    log_dir: Path,
    run_stem: str,
    logger: logging.Logger,
) -> None:
    # Agent self-reports are deliberately excluded from the final-report context: they are
    # themselves LLM-generated and have been observed to confabulate outcomes that contradict the
    # logs. The final report must be grounded only in the raw logs and the collected routing state.
    results_section = "\n".join(f"{name}: {'SUCCESS' if r.success else f'INCOMPLETE — {r.message}'}" for name, r in sorted(agent_results.items()))
    logs_section = "\n\n".join(f"--- {name} ---\n{text}" for name, text in sorted(node_logs.items()))
    routing_section = "\n\n".join(f"--- {name} ---\n{route_tables.get(name, '(empty)')}" for name in sorted(route_tables))
    context = (
        "=== Agent Final Results ===\n\n"
        + results_section
        + "\n\n=== Agent Logs ===\n\n"
        + logs_section
        + "\n\n=== Connectivity Matrix ===\n\n"
        + connectivity
        + "\n\n=== Routing Tables ===\n\n"
        + routing_section
    )

    logger.info("Generating final report with model %s...", model_key)

    report_max_tokens = min(max_tokens, REPORT_MAX_TOKENS)

    if model_key in CLAUDE_MODELS:
        agent = AgentClaude(CLAUDE_MODELS[model_key], "final-report", system_prompt=final_prompt, max_tokens=report_max_tokens)
        report_context = context
    elif model_key in GPT_MODELS:
        agent = AgentOpenAI(GPT_MODELS[model_key], "final-report", system_prompt=final_prompt, max_tokens=report_max_tokens)
        report_context = context
    elif model_key in TOGETHER_MODELS:
        # Together-hosted models (e.g. GLM) speak the same Chat Completions protocol as vLLM and
        # inherit its log_summarizer; they take the compressed-log path below (their context
        # window may be limited, unlike the full-context Claude/GPT branches above).
        agent = AgentTogether(TOGETHER_MODELS[model_key], "final-report", system_prompt=final_prompt, max_tokens=report_max_tokens)
        report_context = None
    elif model_key in VLLM_MODELS:
        agent = AgentVLLM(VLLM_MODELS[model_key], "final-report", vllm_host, vllm_port, system_prompt=final_prompt, max_tokens=report_max_tokens)
        report_context = None
    else:
        raise ValueError(f"Unknown model key: {model_key!r}")

    if report_context is None:
        compressed_logs = {name: agent.log_summarizer.summarize(log_text, name) for name, log_text in node_logs.items()}
        compressed_logs_section = "\n\n".join(f"--- {name} ---\n{t}" for name, t in sorted(compressed_logs.items()))
        report_context = (
            "=== Agent Final Results ===\n\n"
            + results_section
            + "\n\n=== Agent Logs ===\n\n"
            + compressed_logs_section
            + "\n\n=== Connectivity Matrix ===\n\n"
            + connectivity
            + "\n\n=== Routing Tables ===\n\n"
            + routing_section
        )

    text = agent.query(report_context)
    path = log_dir / f"{run_stem}-final-report.md"
    path.write_text(text)
    logger.info("Final report written to %s", path)


def generate_routes_pdf(
    network: Network,
    route_tables: dict[str, str],
    log_dir: Path,
    run_stem: str,
    logger: logging.Logger,
    show_delays: bool = False,
) -> None:
    """Render current routing state as a Graphviz PDF."""
    pdf_path = str(log_dir / f"{run_stem}-routes")
    Route.from_network(network, route_tables).render_matplotlib(pdf_path, show_delays=show_delays)
    logger.info("Network graph written to %s.pdf", pdf_path)
