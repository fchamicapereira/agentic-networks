#!/usr/bin/env python3

import argparse

from pathlib import Path

from agentic_networks.network import load_topology, Network
from agentic_networks.agentic_network import AgenticNetwork, MODELS
from experiment import (
    DEFAULT_LOG_DIR,
    chown_to_user,
    check_vllm_server_or_exit,
    collect_node_logs,
    collect_route_tables,
    generate_routes_pdf,
    setup_logging,
    setup_node_logs,
    write_agent_reports,
    write_final_report,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Simple routing experiment")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--model", "-m", default="sonnet", choices=list(MODELS.keys()))
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR), metavar="DIR")
    parser.add_argument("--max-iterations", "-i", type=int, default=50, metavar="N")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--window-size", "-w", type=int, default=40, metavar="N",
                        help="Sliding window of messages sent to the model per turn (Claude only). "
                             "Default 40 = last 20 turns, matching half of the default --max-iterations=50. "
                             "Early-iteration discoveries are recoverable from the live routing table.")
    parser.add_argument("--topology", required=True, metavar="FILE")
    parser.add_argument("--sequential", "-s", action="store_true", default=False,
                        help="Run agents sequentially round-robin instead of concurrently")
    parser.add_argument("--vllm-host", default="localhost", metavar="HOST")
    parser.add_argument("--vllm-port", type=int, default=8000, metavar="PORT")

    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", "-p", metavar="FILE",
                              help="Single prompt file given to every agent")
    prompt_group.add_argument("--prompts-dir", metavar="DIR",
                              help="Directory of per-node prompt files ({node}.txt)")
    parser.add_argument("--final-report-prompt", metavar="FILE",
                        help="Optional file containing a one-shot analysis request sent to the model "
                             "after all agents finish; output is written to {run_stem}-final-report.md")
    return parser.parse_args()


def load_prompts(args) -> tuple[str | dict[str, str], str]:
    """Return (prompts, stem) where prompts is either a shared string or a per-node dict."""
    if args.prompt:
        p = Path(args.prompt)
        return p.read_text(), p.stem
    d = Path(args.prompts_dir)
    prompts = {f.stem: f.read_text() for f in sorted(d.glob("*.txt"))}
    if not prompts:
        raise SystemExit(f"No .txt files found in {d}")
    return prompts, d.name


def write_report(network: Network, route_tables: dict[str, str], report_path: Path) -> str:
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
    return connectivity_str


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

    vllm_base_url = f"http://{args.vllm_host}:{args.vllm_port}/v1"
    check_vllm_server_or_exit(args.model, vllm_base_url, logger)

    logger.info("Building Mininet network...")
    network = Network(load_topology(args.topology))
    network.start()
    network.clear_routing_tables()

    prompts, prompt_stem = load_prompts(args)
    topology_stem = Path(args.topology).stem
    run_stem = f"{prompt_stem}-{args.model}-{topology_stem}"

    setup_node_logs(network.hosts, log_dir, run_stem)
    logger.info("Writing per-node logs to %s/", log_dir)
    logger.info("Using model: %s (%s)", args.model, MODELS[args.model])

    try:
        anet = AgenticNetwork(
            network=network,
            initial_prompts=prompts,
            model_key=args.model,
            max_iterations=args.max_iterations,
            max_tokens=args.max_tokens,
            vllm_base_url=vllm_base_url,
            window_size=args.window_size,
        )
        results = anet.run(concurrent=not args.sequential)

        print_agent_results(results, network.hosts)

        route_tables = collect_route_tables(network)
        connectivity_str = write_report(network, route_tables, log_dir / f"{run_stem}.txt")
        logger.info("Report written to %s/%s.txt", log_dir, run_stem)

        logger.info("Gathering agent self-reports...")
        agent_reports = anet.gather_reports()
        write_agent_reports(agent_reports, log_dir, run_stem, logger)
        generate_routes_pdf(network, route_tables, log_dir, run_stem, logger, show_delays=False)

        if args.final_report_prompt:
            final_prompt = Path(args.final_report_prompt).read_text()
            node_logs = collect_node_logs(log_dir, run_stem, network.hosts)
            write_final_report(
                model_key=args.model,
                vllm_base_url=vllm_base_url,
                max_tokens=args.max_tokens,
                final_prompt=final_prompt,
                agent_reports=agent_reports,
                agent_results=results,
                node_logs=node_logs,
                connectivity=connectivity_str,
                route_tables=route_tables,
                log_dir=log_dir,
                run_stem=run_stem,
                logger=logger,
            )

        network.stop()
    finally:
        chown_to_user(log_dir)


if __name__ == "__main__":
    main()
