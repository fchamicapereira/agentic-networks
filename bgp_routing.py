#!/usr/bin/env python3

import argparse

from pathlib import Path

from agentic_networks.network import load_topology, Network
from experiment import (
    DEFAULT_LOG_DIR,
    chown_to_user,
    collect_route_tables,
    generate_routes_pdf,
    setup_logging,
)


def parse_args():
    parser = argparse.ArgumentParser(description="BGP baseline routing experiment")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--topology", required=True, metavar="FILE")
    parser.add_argument("--policies-dir", "-p", metavar="DIR", help="Directory of per-node FRR policy files (<NODE>.frr)")
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR), metavar="DIR")
    return parser.parse_args()


def collect_bgp_routes(network: Network) -> dict[str, str]:
    """Read only BGP-installed routes from every host."""
    result = {}
    for name, host in network.hosts.items():
        assert host is not None
        result[name] = host.cmd("ip route show proto bgp").strip()
    return result


def print_route_tables(route_tables: dict[str, str], bgp_routes: dict[str, str]) -> None:
    print("\n=== BGP-installed Routes ===")
    for name in sorted(bgp_routes):
        routes = bgp_routes[name] or "(none)"
        print(f"  --- {name} ---\n{routes}")
    print("\n=== Full Routing Tables ===")
    for name in sorted(route_tables):
        routes = route_tables[name] or "(empty)"
        print(f"  --- {name} ---\n{routes}")


def write_report(network: Network, route_tables: dict[str, str], bgp_routes: dict[str, str], report_path: Path) -> None:
    connectivity_str = network.test_all_connectivity()
    bgp_section = "\n".join(f"--- {name} ---\n{bgp_routes[name] or '(none)'}" for name in sorted(bgp_routes))
    full_section = "\n".join(f"--- {name} ---\n{route_tables[name] or '(empty)'}" for name in sorted(route_tables))
    report_path.write_text(
        "=== Connectivity Matrix ===\n"
        + connectivity_str
        + "\n\n=== BGP-installed Routes ===\n\n"
        + bgp_section
        + "\n\n=== Full Routing Tables ===\n\n"
        + full_section
        + "\n"
    )


def main():
    args = parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(args.log_level)

    policies: dict[str, str] | None = None
    if args.policies_dir:
        policies_path = Path(args.policies_dir)
        policies = {f.stem: f.read_text() for f in sorted(policies_path.glob("*.frr"))}
    policies_stem = Path(args.policies_dir).name if args.policies_dir else "default"
    topology_stem = Path(args.topology).stem
    run_stem = f"bgp-{policies_stem}-{topology_stem}"

    logger.info("Building Mininet network...")
    network = Network(load_topology(args.topology))
    network.start()

    try:
        logger.info("Starting eBGP (one AS per node)...")
        asn_map = network.start_bgp(policies=policies)
        for node, asn in sorted(asn_map.items()):
            logger.info("  %s → AS%d", node, asn)
        logger.info("BGP converged.")

        route_tables = collect_route_tables(network)
        bgp_routes = collect_bgp_routes(network)
        print_route_tables(route_tables, bgp_routes)
        write_report(network, route_tables, bgp_routes, log_dir / f"{run_stem}.txt")
        logger.info("Report written to %s/%s.txt", log_dir, run_stem)

        generate_routes_pdf(network, route_tables, log_dir, run_stem, logger)

        network.stop_bgp()
        network.stop()
    finally:
        chown_to_user(log_dir)


if __name__ == "__main__":
    main()
