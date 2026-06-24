#!/usr/bin/env python3

"""
optimal_routing.py — Compute min-delay optimal routes and render a Graphviz PDF.

Uses Dijkstra's algorithm on the link-delay graph to find the shortest-latency
path between every pair of hosts, then visualises the resulting next-hop
routing decisions using the same PDF renderer as the live experiments.

Usage:
    python optimal_routing.py <topology.csv> [-o <output>]

Arguments:
    topology    Path to a topology CSV file (same format as topologies/).
    -o/--output Output path for the PDF (default: topology filename without .csv).
"""

import argparse
import heapq

from collections import defaultdict

from agentic_networks.network import Link, Network, load_topology
from agentic_networks.routes import Route, RoutingRule


def _build_adjacency(links: list[Link]) -> dict[str, list[tuple[int, str]]]:
    """Return an adjacency list {node: [(delay_ms, neighbour), ...]} for both directions."""
    adj: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for link in links:
        adj[link.node1].append((link.delay_ms, link.node2))
        adj[link.node2].append((link.delay_ms, link.node1))
    return dict(adj)


def _dijkstra(source: str, adj: dict[str, list[tuple[int, str]]]) -> dict[str, str]:
    """
    Run Dijkstra from *source* and return a dict {destination: first_hop}.

    first_hop is the immediate neighbour of *source* on the min-delay path to
    each reachable destination.
    """
    # (cumulative_delay, node, first_hop_from_source)
    heap: list[tuple[int, str, str]] = [(0, source, source)]
    visited: set[str] = set()
    first_hop: dict[str, str] = {}

    while heap:
        dist, node, hop = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        if node != source:
            first_hop[node] = hop

        for edge_delay, neighbour in adj.get(node, []):
            if neighbour not in visited:
                # Propagate the first hop: if we are still at source, the
                # first hop toward neighbour is neighbour itself.
                next_hop = neighbour if node == source else hop
                heapq.heappush(heap, (dist + edge_delay, neighbour, next_hop))

    return first_hop


def compute_optimal_rules(links: list[Link]) -> list[RoutingRule]:
    """Return RoutingRule objects for every (src, dst) pair using min-delay paths."""
    adj = _build_adjacency(links)
    nodes = sorted(adj.keys())
    rules: list[RoutingRule] = []

    for source in nodes:
        first_hops = _dijkstra(source, adj)
        for destination, next_hop in first_hops.items():
            rules.append(RoutingRule(
                source_host=source,
                destination=destination,
                next_hop=next_hop,
            ))

    return rules


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute optimal min-delay routing and render a Graphviz PDF."
    )
    parser.add_argument("topology", help="Path to the topology CSV file")
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output path (with or without .pdf; default: topology filename without .csv)",
    )
    args = parser.parse_args()

    topo = load_topology(args.topology)
    rules = compute_optimal_rules(topo.links)

    output = (args.output or args.topology.removesuffix(".csv")).removesuffix(".pdf")
    Route(Network(topo), rules).render_matplotlib(output)
    print(f"Written to {output}.pdf")

    # Print a human-readable summary of the routing table.
    nodes = sorted({link.node1 for link in topo.links} | {link.node2 for link in topo.links})
    width = max(len(n) for n in nodes)
    print()
    print(f"{'Source':<{width}}  {'Destination':<{width}}  Next-hop")
    print("-" * (width * 2 + 14))
    for rule in sorted(rules):
        print(f"{rule.source_host:<{width}}  {rule.destination:<{width}}  {rule.next_hop}")


if __name__ == "__main__":
    main()
