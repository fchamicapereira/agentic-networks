#!/usr/bin/env python3
"""
test_converged_routing.py — Validate the converged-start routing seed.

Builds a live Mininet network for each given topology, installs the arbitrary stable
routing solution (Network.seed_stable_routes), and prints the resulting connectivity
matrix. No agents and no experiment are run — this only checks that the seed produces
full all-to-all loopback reachability.

Requires root (Mininet).

Usage:
    sudo python tools/test_converged_routing.py topologies/bribing.csv
    sudo python tools/test_converged_routing.py topologies/*.csv     # check several
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic_networks.network import load_topology, Network


def check(topology_path: str) -> bool:
    """Seed the topology and return True iff the connectivity matrix is all-OK."""
    name = Path(topology_path).name
    network = Network(load_topology(topology_path))
    network.start()
    try:
        network.seed_stable_routes()
        matrix = network.test_all_connectivity(label=f"Converged seed — {name}")
    finally:
        network.stop()
    return "FAIL" not in matrix


def main() -> None:
    topologies = sys.argv[1:]
    if not topologies:
        sys.exit("usage: test_converged_routing.py <topology.csv> [<topology.csv> ...]")

    if os.geteuid() != 0:
        print("warning: Mininet usually requires root — run with sudo if this fails.\n")

    results: dict[str, bool] = {}
    for topo in topologies:
        results[topo] = check(topo)

    print("\n=== Summary ===")
    for topo, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {topo}")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
