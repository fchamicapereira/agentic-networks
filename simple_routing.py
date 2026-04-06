import argparse
import logging
import os

from pathlib import Path
from tqdm import tqdm
from mininet.log import setLogLevel

from network import load_topology, build_network, Network
from agent_openai import check_server
from agent_openai import MODELS as OPENAI_MODELS
from agentic_network import AgenticNetwork, MODELS
from visualize_network_routes import generate_network_pdf


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


SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG_DIR = SCRIPT_DIR / "logs"
DEFAULT_TOPOLOGY = SCRIPT_DIR / "topologies" / "triangle.csv"


def setup_node_log(node_name: str, log_dir: Path, prompt_stem: str, model: str, topology_stem: str) -> logging.FileHandler:
    """Attach a file handler to the agent.<node_name> logger."""
    log_dir.mkdir(exist_ok=True)
    handler = logging.FileHandler(log_dir / f"{prompt_stem}-{model}-{topology_stem}-{node_name}.log", mode="w")
    handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s", datefmt="%H:%M:%S"))
    node_logger = logging.getLogger(f"agent.{node_name}")
    node_logger.addHandler(handler)
    node_logger.propagate = False
    return handler


def write_report(network: Network, route_tables: dict[str, str], report_path: Path) -> None:
    connectivity_str = network.test_all_connectivity()
    routing_section = "\n".join(f"--- {name} ---\n{route_tables[name] or '(empty)'}" for name in sorted(route_tables))
    with open(report_path, "w") as f:
        f.write("=== Connectivity Matrix ===\n")
        f.write(connectivity_str)
        f.write("\n\n=== Routing Tables ===\n\n")
        f.write(routing_section)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Talkative Control Protocol")
    parser.add_argument(
        "--log-level",
        "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--prompt",
        "-p",
        required=True,
        metavar="FILE",
        help="Path to the prompt file to send to each agent (e.g. prompts/simple.txt)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="sonnet",
        choices=list(MODELS.keys()),
        help="Model to use for agents (default: sonnet)",
    )
    parser.add_argument(
        "--log-dir",
        "-d",
        default=str(DEFAULT_LOG_DIR),
        metavar="DIR",
        help="Directory to write per-node log files (default: logs/)",
    )
    parser.add_argument(
        "--max-iterations",
        "-i",
        type=int,
        default=50,
        metavar="N",
        help="Maximum number of agent iterations per node (default: 50)",
    )
    parser.add_argument(
        "--max-tokens",
        "-t",
        type=int,
        default=16384,
        metavar="N",
        help="Maximum number of tokens per LLM response (default: 16384)",
    )
    parser.add_argument(
        "--topology",
        required=True,
        metavar="FILE",
        help="Path to topology CSV file",
    )
    parser.add_argument(
        "--sequential",
        "-s",
        action="store_true",
        default=False,
        help="Run agents sequentially round-robin instead of concurrently (default: concurrent)",
    )
    parser.add_argument(
        "--openai-host",
        default="localhost",
        metavar="HOST",
        help="Hostname for the OpenAI-compatible API server (default: localhost)",
    )
    parser.add_argument(
        "--openai-port",
        type=int,
        default=8000,
        metavar="PORT",
        help="Port for the OpenAI-compatible API server (default: 8000)",
    )
    args = parser.parse_args()
    log_dir = Path(args.log_dir)
    topology = load_topology(args.topology)

    log_dir.mkdir(parents=True, exist_ok=True)
    chown_to_user(log_dir)

    with open(args.prompt) as f:
        initial_prompt = f.read()

    handler = TqdmHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  [%(name)-14s]  %(levelname)s  %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logging.root.setLevel(getattr(logging, args.log_level))
    logging.root.addHandler(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    setLogLevel("warning")  # Suppress Mininet's verbose output

    logger = logging.getLogger("main")

    openai_base_url = f"http://{args.openai_host}:{args.openai_port}/v1"
    if args.model in OPENAI_MODELS:
        if not check_server(openai_base_url, api_key="none"):
            logger.error("No OpenAI-compatible server responding at %s", openai_base_url)
            exit(1)

    logger.info("Building Mininet network...")

    network = build_network(topology)

    prompt_stem = Path(args.prompt).stem
    topology_stem = Path(args.topology).stem

    try:
        mode = "sequentially (round-robin)" if args.sequential else "concurrently"
        logger.info("Network is up. Starting %d agents %s ...", len(network.hosts), mode)

        for name in network.hosts:
            setup_node_log(name, log_dir, prompt_stem, args.model, topology_stem)

        logger.info("Writing per-node logs to %s/", log_dir)
        logger.info("Using model: %s (%s)", args.model, MODELS[args.model])

        results = AgenticNetwork(
            network=network,
            initial_prompt=initial_prompt,
            model_key=args.model,
            max_iterations=args.max_iterations,
            max_tokens=args.max_tokens,
            openai_base_url=openai_base_url,
        ).run(concurrent=not args.sequential)

        print("\n=== Agent Reports ===")
        for name in network.hosts:
            if results[name].success:
                print(f"  {name} [SUCCESS]")
            else:
                print(f"  {name} [INCOMPLETE] {results[name].message}")

        run_stem = f"{prompt_stem}-{args.model}-{topology_stem}"

        print("=== Final Routing Tables ===")
        route_tables: dict[str, str] = {}
        for name, host in network.hosts.items():
            routes = (host.cmd("ip route show") or "").strip()
            route_tables[name] = routes
            print(f"\n--- {name} ---")
            print(routes or "(empty)")
        print()

        report_path = log_dir / f"{run_stem}-report.txt"
        write_report(network, route_tables, report_path)
        logger.info("Report written to %s", report_path)

        network.net.stop()

        pdf_path = str(log_dir / f"{run_stem}-routes")
        generate_network_pdf(network, network.get_routing_rules(route_tables), pdf_path)
        logger.info("Network graph written to %s.pdf", pdf_path)

    finally:
        chown_to_user(log_dir)


if __name__ == "__main__":
    main()
