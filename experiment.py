"""Shared utilities for experiment entry-point scripts."""

import logging
import os

from pathlib import Path
from typing import Iterable

from tqdm import tqdm
from mininet.log import setLogLevel

from agentic_networks.network_agent import AgentResult
from agentic_networks.agent_vllm import AgentVLLM, MODELS as VLLM_MODELS
from agentic_networks.agent_claude import AgentClaude, MODELS as CLAUDE_MODELS
from agentic_networks.agent_openai import AgentOpenAI, MODELS as GPT_MODELS
from agentic_networks.network import Network
from agentic_networks.routes import Route

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG_DIR = SCRIPT_DIR / "logs"


class TqdmHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            tqdm.write(self.format(record))
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
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  [%(name)-20s]  %(levelname)s  %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logging.root.setLevel(getattr(logging, log_level))
    logging.root.addHandler(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    setLogLevel("warning")  # Suppress Mininet's verbose output
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


def collect_node_logs(log_dir: Path, run_stem: str, node_names: Iterable[str]) -> dict[str, str]:
    logs = {}
    for name in node_names:
        path = log_dir / f"{run_stem}-{name}.log"
        if path.exists():
            logs[name] = path.read_text()
    return logs


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
    results_section = "\n".join(f"{name}: {'SUCCESS' if r.success else f'INCOMPLETE — {r.message}'}" for name, r in sorted(agent_results.items()))
    reports_section = "\n\n".join(f"--- {name} ---\n{text}" for name, text in sorted(agent_reports.items()))
    logs_section = "\n\n".join(f"--- {name} ---\n{text}" for name, text in sorted(node_logs.items()))
    routing_section = "\n\n".join(f"--- {name} ---\n{route_tables.get(name, '(empty)')}" for name in sorted(route_tables))
    context = (
        "=== Agent Final Results ===\n\n"
        + results_section
        + "\n\n=== Agent Self-Reports ===\n\n"
        + reports_section
        + "\n\n=== Agent Logs ===\n\n"
        + logs_section
        + "\n\n=== Connectivity Matrix ===\n\n"
        + connectivity
        + "\n\n=== Routing Tables ===\n\n"
        + routing_section
    )

    logger.info("Generating final report with model %s...", model_key)

    if model_key in CLAUDE_MODELS:
        agent = AgentClaude(CLAUDE_MODELS[model_key], "final-report", system_prompt=final_prompt, max_tokens=max_tokens)
        report_context = context
    elif model_key in GPT_MODELS:
        agent = AgentOpenAI(GPT_MODELS[model_key], "final-report", system_prompt=final_prompt, max_tokens=max_tokens)
        report_context = context
    else:
        agent = AgentVLLM(VLLM_MODELS[model_key], "final-report", vllm_host, vllm_port, system_prompt=final_prompt, max_tokens=max_tokens)
        compressed_logs = {name: agent.log_summarizer.summarize(log_text, name) for name, log_text in node_logs.items()}
        compressed_logs_section = "\n\n".join(f"--- {name} ---\n{t}" for name, t in sorted(compressed_logs.items()))
        report_context = (
            "=== Agent Final Results ===\n\n"
            + results_section
            + "\n\n=== Agent Self-Reports ===\n\n"
            + reports_section
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
