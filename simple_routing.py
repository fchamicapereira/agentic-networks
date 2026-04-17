#!/usr/bin/env python3

import argparse

from pathlib import Path

from agentic_networks.network import load_topology, Network
from agentic_networks.agentic_network import AgenticNetwork, MODELS
from experiment import (
    DEFAULT_LOG_DIR,
    chown_to_user,
    check_openai_server_or_exit,
    collect_route_tables,
    generate_routes_pdf,
    setup_logging,
    setup_node_logs,
    write_agent_reports,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Simple routing experiment")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--prompt", "-p", required=True, metavar="FILE", help="Path to the prompt file")
    parser.add_argument("--model", "-m", default="sonnet", choices=list(MODELS.keys()))
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR), metavar="DIR")
    parser.add_argument("--max-iterations", "-i", type=int, default=50, metavar="N")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--topology", required=True, metavar="FILE")
    parser.add_argument("--sequential", "-s", action="store_true", default=False,
                        help="Run agents sequentially round-robin instead of concurrently")
    parser.add_argument("--openai-host", default="localhost", metavar="HOST")
    parser.add_argument("--openai-port", type=int, default=8000, metavar="PORT")
    return parser.parse_args()


def write_report(network: Network, route_tables: dict[str, str], report_path: Path) -> None:
    connectivity_str = network.test_all_connectivity()
    routing_section = "\n".join(
        f"--- {name} ---\n{route_tables[name] or '(empty)'}" for name in sorted(route_tables)
    )
    report_path.write_text(
        "=== Connectivity Matrix ===\n"
        + connectivity_str
        + "\n\n=== Routing Tables ===\n\n"
        + routing_section
        + "\n"
    )


def print_agent_results(results, node_names) -> None:
    print("\n=== Agent Results ===")
    for name in node_names:
        if results[name].success:
            print(f"  {name} [SUCCESS]")
        else:
            print(f"  {name} [INCOMPLETE] {results[name].message}")


def main():
    args = parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(args.log_level)

    openai_base_url = f"http://{args.openai_host}:{args.openai_port}/v1"
    check_openai_server_or_exit(args.model, openai_base_url, logger)

    logger.info("Building Mininet network...")
    network = Network(load_topology(args.topology))
    network.start()

    prompt_stem = Path(args.prompt).stem
    topology_stem = Path(args.topology).stem
    run_stem = f"{prompt_stem}-{args.model}-{topology_stem}"

    setup_node_logs(network.hosts, log_dir, run_stem)
    logger.info("Writing per-node logs to %s/", log_dir)
    logger.info("Using model: %s (%s)", args.model, MODELS[args.model])

    try:
        anet = AgenticNetwork(
            network=network,
            initial_prompt=Path(args.prompt).read_text(),
            model_key=args.model,
            max_iterations=args.max_iterations,
            max_tokens=args.max_tokens,
            openai_base_url=openai_base_url,
        )
        results = anet.run(concurrent=not args.sequential)

        print_agent_results(results, network.hosts)

        route_tables = collect_route_tables(network)
        write_report(network, route_tables, log_dir / f"{run_stem}.txt")
        logger.info("Report written to %s/%s.txt", log_dir, run_stem)

        write_agent_reports(anet, log_dir, run_stem, logger)
        generate_routes_pdf(network, route_tables, log_dir, run_stem, logger)

        network.stop()
    finally:
        chown_to_user(log_dir)


if __name__ == "__main__":
    main()
