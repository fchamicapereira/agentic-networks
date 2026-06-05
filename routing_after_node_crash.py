#!/usr/bin/env python3
"""
routing_after_node_crash.py

Experiment: start a fully connected network, immediately crash one node at the
first scheduler step, notify surviving agents via the message bus, and observe
how they react and re-establish routing.

The crash is implemented as an AgenticNetwork reactor — a callable that fires
on step 0 and brings down all interfaces of the target node.
"""

import argparse
import logging

from pathlib import Path

from agentic_networks.network import load_topology, Network
from agentic_networks.agentic_network import AgenticNetwork, MODELS
from experiment import (
    DEFAULT_LOG_DIR,
    chown_to_user,
    collect_route_tables,
    generate_routes_pdf,
    setup_logging,
    setup_node_logs,
    write_agent_reports,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Node-crash routing experiment")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--prompt", "-p", required=True, metavar="FILE", help="Prompt file for all agents")
    parser.add_argument("--model", "-m", default="sonnet", choices=list(MODELS.keys()))
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR), metavar="DIR")
    parser.add_argument("--max-iterations", "-i", type=int, default=50, metavar="N")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--topology", required=True, metavar="FILE")
    parser.add_argument("--sequential", "-s", action="store_true", default=False,
                        help="Run agents sequentially round-robin instead of step-parallel")
    parser.add_argument("--vllm-host", default="localhost", metavar="HOST")
    parser.add_argument("--vllm-port", type=int, default=8000, metavar="PORT")
    return parser.parse_args()


def write_report(network: Network, crashed_node: str, route_tables: dict[str, str], report_path: Path) -> None:
    connectivity_str = network.test_all_connectivity()
    routing_section = "\n".join(
        f"--- {name} ---\n{route_tables[name] or '(empty)'}" for name in sorted(route_tables)
    )
    report_path.write_text(
        "=== Experiment: Node Crash ===\n"
        + f"Crashed node: {crashed_node}\n\n"
        + "=== Connectivity Matrix (post-crash) ===\n"
        + connectivity_str
        + "\n\n=== Routing Tables (surviving nodes) ===\n\n"
        + routing_section
        + "\n"
    )


def print_agent_results(results, node_names, crashed_node) -> None:
    print("\n=== Agent Results ===")
    for name in node_names:
        if name == crashed_node:
            print(f"  {name} [CRASHED]")
        elif name not in results:
            print(f"  {name} [NO RESULT]")
        elif results[name].success:
            print(f"  {name} [SUCCESS]")
        else:
            print(f"  {name} [INCOMPLETE] {results[name].message}")


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
    args = parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(args.log_level)

    vllm_base_url = f"http://{args.vllm_host}:{args.vllm_port}/v1"

    logger.info("Building Mininet network...")
    network = Network(load_topology(args.topology))
    network.start()

    node_names = sorted(network.hosts.keys())
    crashed_node = node_names[-1]

    prompt_stem = Path(args.prompt).stem
    topology_stem = Path(args.topology).stem
    run_stem = f"{prompt_stem}-{args.model}-{topology_stem}-crash_{crashed_node}"

    setup_node_logs(network.hosts, log_dir, run_stem)
    logger.info("Writing per-node logs to %s/", log_dir)
    logger.info("Using model: %s (%s)", args.model, MODELS[args.model])
    logger.info("Node to crash on step 0: %s", crashed_node)

    try:
        anet = AgenticNetwork(
            network=network,
            initial_prompt=Path(args.prompt).read_text(),
            model_key=args.model,
            max_iterations=args.max_iterations,
            max_tokens=args.max_tokens,
            vllm_base_url=vllm_base_url,
            reactors=[crash_reactor],
        )
        results = anet.run(concurrent=not args.sequential)

        print_agent_results(results, node_names, crashed_node)

        route_tables = collect_route_tables(network)
        surviving_routes = {name: rt for name, rt in route_tables.items() if name != crashed_node}
        write_report(network, crashed_node, surviving_routes, log_dir / f"{run_stem}.txt")
        logger.info("Report written to %s/%s.txt", log_dir, run_stem)

        write_agent_reports(anet, log_dir, run_stem, logger)
        generate_routes_pdf(network, route_tables, log_dir, run_stem, logger)

        network.stop()
    finally:
        chown_to_user(log_dir)


if __name__ == "__main__":
    main()
