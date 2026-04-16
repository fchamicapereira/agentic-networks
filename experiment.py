"""Shared utilities for experiment entry-point scripts."""

import logging
import os

from pathlib import Path
from typing import Iterable

from tqdm import tqdm
from mininet.log import setLogLevel

from agent_openai import check_server
from agent_openai import MODELS as OPENAI_MODELS
from agentic_network import AgenticNetwork
from network import Network
from visualize_network_routes import generate_network_pdf


SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG_DIR = SCRIPT_DIR / "logs"


class TqdmHandler(logging.StreamHandler):
    """Log handler that writes through tqdm.write() to avoid overwriting progress bars."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            tqdm.write(self.format(record))
        except Exception:
            self.handleError(record)


def chown_to_user(path: Path) -> None:
    """Recursively restore ownership to the user who invoked sudo."""
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
    """Configure the root logger with a TqdmHandler and return the 'main' logger."""
    handler = TqdmHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s  [%(name)-14s]  %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    ))
    logging.root.setLevel(getattr(logging, log_level))
    logging.root.addHandler(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    setLogLevel("warning")  # Suppress Mininet's verbose output
    return logging.getLogger("main")


def check_openai_server_or_exit(model: str, base_url: str, logger: logging.Logger) -> None:
    """Exit if the model requires an OpenAI-compatible server that isn't responding."""
    if model in OPENAI_MODELS:
        if not check_server(base_url, api_key="none"):
            logger.error("No OpenAI-compatible server responding at %s", base_url)
            exit(1)


def setup_node_logs(node_names: Iterable[str], log_dir: Path, run_stem: str) -> None:
    """Attach a per-node file handler to each agent.<name> logger."""
    for name in node_names:
        handler = logging.FileHandler(log_dir / f"{run_stem}-{name}.log", mode="w")
        handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s", datefmt="%H:%M:%S"))
        node_logger = logging.getLogger(f"agent.{name}")
        node_logger.addHandler(handler)
        node_logger.propagate = False


def collect_route_tables(network: Network) -> dict[str, str]:
    """Read the routing table from every host and return {node_name: routes}."""
    return {
        name: (host.cmd("ip route show") or "").strip()
        for name, host in network.hosts.items()
    }


def write_agent_reports(anet: AgenticNetwork, log_dir: Path, run_stem: str, logger: logging.Logger) -> None:
    """Ask each agent to write a self-report and save it to {run_stem}-{name}-report.txt."""
    logger.info("Gathering agent self-reports...")
    for name, text in anet.gather_reports().items():
        path = log_dir / f"{run_stem}-{name}-report.md"
        path.write_text(text)
        logger.info("Agent report written to %s", path)


def generate_routes_pdf(
    network: Network,
    route_tables: dict[str, str],
    log_dir: Path,
    run_stem: str,
    logger: logging.Logger,
) -> None:
    """Render current routing state as a Graphviz PDF."""
    pdf_path = str(log_dir / f"{run_stem}-routes")
    generate_network_pdf(network, network.get_routing_rules(route_tables), pdf_path)
    logger.info("Network graph written to %s.pdf", pdf_path)
