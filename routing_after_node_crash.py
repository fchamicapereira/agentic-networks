#!/usr/bin/env python3
"""
routing_after_node_crash.py

Experiment: start a fully connected network, immediately crash one node at the
first scheduler step, notify surviving agents via the message bus, and observe
how they react and re-establish routing.

The crash is implemented as an AgenticNetwork reactor — a callable that fires
on step 0 and brings down all interfaces of the target node, then broadcasts
an alert to every surviving agent.
"""

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


SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG_DIR = SCRIPT_DIR / "logs"


def setup_node_log(node_name: str, log_dir: Path, run_stem: str) -> None:
    log_dir.mkdir(exist_ok=True)
    handler = logging.FileHandler(log_dir / f"{run_stem}-{node_name}.log", mode="w")
    handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s", datefmt="%H:%M:%S"))
    node_logger = logging.getLogger(f"agent.{node_name}")
    node_logger.addHandler(handler)
    node_logger.propagate = False


def write_report(network: Network, crashed_node: str, route_tables: dict[str, str], report_path: Path) -> None:
    connectivity_str = network.test_all_connectivity()
    routing_section = "\n".join(f"--- {name} ---\n{route_tables[name] or '(empty)'}" for name in sorted(route_tables))
    with open(report_path, "w") as f:
        f.write("=== Experiment: Node Crash ===\n")
        f.write(f"Crashed node: {crashed_node}\n\n")
        f.write("=== Connectivity Matrix (post-crash) ===\n")
        f.write(connectivity_str)
        f.write("\n\n=== Routing Tables (surviving nodes) ===\n\n")
        f.write(routing_section)
        f.write("\n")


def crash_reactor(net: AgenticNetwork, step: int) -> None:
    if step != 0:
        return
    crashed_node = sorted(net.network.hosts.keys())[-1]
    logging.getLogger("main").info(">>> CRASH EVENT: deleting all links of node %s <<<", crashed_node)
    host = net.network.hosts[crashed_node]
    for link in list(net.network.net.links):
        if host in (link.intf1.node, link.intf2.node):
            net.network.net.delLink(link)
    net.stop_agent(crashed_node)


def main():
    parser = argparse.ArgumentParser(description="Node-crash routing experiment")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--prompt", "-p", required=True, metavar="FILE", help="Prompt file for all agents")
    parser.add_argument("--model", "-m", default="sonnet", choices=list(MODELS.keys()))
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR), metavar="DIR")
    parser.add_argument("--max-iterations", "-i", type=int, default=50, metavar="N")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--topology", required=True, metavar="FILE")
    parser.add_argument("--sequential", "-s", action="store_true", default=False, help="Run agents sequentially round-robin instead of step-parallel")
    parser.add_argument("--openai-host", default="localhost", metavar="HOST")
    parser.add_argument("--openai-port", type=int, default=8000, metavar="PORT")
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    topology = load_topology(args.topology)
    log_dir.mkdir(parents=True, exist_ok=True)
    chown_to_user(log_dir)

    with open(args.prompt) as f:
        initial_prompt = f.read()

    handler = TqdmHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s  [%(name)-14s]  %(levelname)s  %(message)s", datefmt="%H:%M:%S"))
    logging.root.setLevel(getattr(logging, args.log_level))
    logging.root.addHandler(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    setLogLevel("warning")

    logger = logging.getLogger("main")

    openai_base_url = f"http://{args.openai_host}:{args.openai_port}/v1"
    if args.model in OPENAI_MODELS:
        if not check_server(openai_base_url, api_key="none"):
            logger.error("No OpenAI-compatible server responding at %s", openai_base_url)
            exit(1)

    logger.info("Building Mininet network...")
    network = build_network(topology)

    node_names = sorted(network.hosts.keys())
    crashed_node = node_names[-1]

    prompt_stem = Path(args.prompt).stem
    topology_stem = Path(args.topology).stem
    run_stem = f"{prompt_stem}-{args.model}-{topology_stem}-crash_{crashed_node}"

    try:
        mode = "sequentially (round-robin)" if args.sequential else "step-parallel"
        logger.info("Network is up. Starting %d agents %s ...", len(network.hosts), mode)
        logger.info("Node to crash on step 0: %s", crashed_node)

        for name in network.hosts:
            setup_node_log(name, log_dir, run_stem)

        logger.info("Writing per-node logs to %s/", log_dir)
        logger.info("Using model: %s (%s)", args.model, MODELS[args.model])

        results = AgenticNetwork(
            network=network,
            initial_prompt=initial_prompt,
            model_key=args.model,
            max_iterations=args.max_iterations,
            max_tokens=args.max_tokens,
            openai_base_url=openai_base_url,
            reactors=[crash_reactor],
        ).run(concurrent=not args.sequential)

        print("\n=== Agent Reports ===")
        for name in node_names:
            if name == crashed_node:
                print(f"  {name} [CRASHED]")
            elif name not in results:
                print(f"  {name} [NO RESULT]")
            elif results[name].success:
                print(f"  {name} [SUCCESS]")
            else:
                print(f"  {name} [INCOMPLETE] {results[name].message}")

        print("\n=== Final Routing Tables ===")
        route_tables: dict[str, str] = {}
        for name, host in network.hosts.items():
            routes = (host.cmd("ip route show") or "").strip()
            route_tables[name] = routes
            label = " [CRASHED]" if name == crashed_node else ""
            print(f"\n--- {name}{label} ---")
            print(routes or "(empty)")
        print()

        surviving_routes = {name: rt for name, rt in route_tables.items() if name != crashed_node}
        report_path = log_dir / f"{run_stem}.txt"
        write_report(network, crashed_node, surviving_routes, report_path)
        logger.info("Report written to %s", report_path)

        network.net.stop()

        pdf_path = str(log_dir / f"{run_stem}-routes")
        generate_network_pdf(network, network.get_routing_rules(route_tables), pdf_path)
        logger.info("Network graph written to %s.pdf", pdf_path)

    finally:
        chown_to_user(log_dir)


if __name__ == "__main__":
    main()
