from pathlib import Path

import argparse
import logging
import os
import threading

from mininet.log import setLogLevel
from mininet.node import Host

from agent import AgentResult
from network import load_topology, build_network
from message_bus import MessageBus
from agent_claude import AgentClaude
from agent_claude import MODELS as CLAUDE_MODELS
from agent_openai import AgentOpenAI
from agent_openai import MODELS as OPENAI_MODELS
from visualize import generate_network_pdf


MODELS = {**CLAUDE_MODELS, **OPENAI_MODELS}


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
    logging.getLogger(f"agent.{node_name}").addHandler(handler)
    return handler


def run_agent_thread(
    node_name: str,
    host: Host,
    bus: MessageBus,
    initial_prompt: str,
    model_key: str,
    max_iterations: int,
    max_tokens: int,
    results: dict,
    openai_host: str,
    openai_port: int,
):
    model = MODELS[model_key]
    if model_key in CLAUDE_MODELS:
        agent = AgentClaude(
            node_name=node_name,
            mininet_host_cmd=host.cmd,
            bus=bus,
            initial_prompt=initial_prompt,
            model=model,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
        )
    else:
        agent = AgentOpenAI(
            node_name=node_name,
            mininet_host_cmd=host.cmd,
            bus=bus,
            initial_prompt=initial_prompt,
            model=model,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
            base_url=f"http://{openai_host}:{openai_port}/v1",
            api_key="none",
        )
    results[node_name] = agent.run()
    agent.mininet_host.get_network_info()


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
        default=30,
        metavar="N",
        help="Maximum number of agent iterations per node (default: 30)",
    )
    parser.add_argument(
        "--max-tokens",
        "-t",
        type=int,
        default=4096,
        metavar="N",
        help="Maximum number of tokens per LLM response (default: 4096)",
    )
    parser.add_argument(
        "--topology",
        required=True,
        metavar="FILE",
        help="Path to topology CSV file",
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

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  [%(name)-14s]  %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    setLogLevel("warning")  # Suppress Mininet's verbose output

    logger = logging.getLogger("main")
    logger.info("Building Mininet network...")

    network = build_network(topology)

    prompt_stem = Path(args.prompt).stem
    topology_stem = Path(args.topology).stem

    try:
        logger.info("Network is up. Starting %d agents in parallel ...", len(network.hosts))

        for name in network.hosts:
            setup_node_log(name, log_dir, prompt_stem, args.model, topology_stem)
        logger.info("Writing per-node logs to %s/", log_dir)

        bus = MessageBus(list(network.hosts.keys()))

        logger.info("Using model: %s (%s)", args.model, MODELS[args.model])

        results: dict[str, AgentResult] = {}
        threads = [
            threading.Thread(
                target=run_agent_thread,
                args=(
                    name,
                    host,
                    bus,
                    initial_prompt,
                    args.model,
                    args.max_iterations,
                    args.max_tokens,
                    results,
                    args.openai_host,
                    args.openai_port,
                ),
                name=f"agent-{name}",
                daemon=True,
            )
            for name, host in network.hosts.items()
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print("\n=== Agent Reports ===")
        for name in network.hosts:
            if results[name].success:
                print(f"  {name} [SUCCESS]")
            else:
                print(f"  {name} [INCOMPLETE] {results[name].message}")

        run_stem = f"{prompt_stem}-{args.model}-{topology_stem}"

        connectivity_path = log_dir / f"{run_stem}-connectivity.txt"
        network.test_all_connectivity(connectivity_path)
        logger.info("Connectivity matrix written to %s", connectivity_path)

        print("=== Final Routing Tables ===")
        route_tables: dict[str, str] = {}
        for name, host in network.hosts.items():
            routes = (host.cmd("ip route show") or "").strip()
            route_tables[name] = routes
            print(f"\n--- {name} ---")
            print(routes or "(empty)")
        print()

        network.net.stop()

        pdf_path = str(log_dir / f"{run_stem}-routes")
        generate_network_pdf(network, network.get_routing_rules(route_tables), pdf_path)
        logger.info("Network graph written to %s.pdf", pdf_path)

    finally:
        chown_to_user(log_dir)


if __name__ == "__main__":
    main()
