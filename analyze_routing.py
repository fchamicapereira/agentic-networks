#!/usr/bin/env python3
"""
Analyze routing experiment efficiency.

Parses routing tables from a .txt experiment file, simulates packet forwarding
hop-by-hop, and compares the resulting delays against Dijkstra-optimal paths.

Metrics reported:
  - Average one-way delay across all host pairs (experiment vs optimal)
  - Maximum per-pair delta (experiment delay minus optimal delay)
  - Full per-pair breakdown for all suboptimal routes
  - Per-IP breakdown highlighting individual IPs with suboptimal paths

Usage:
    python analyze_routing.py \\
        --txt  logs/routing_min_delay-opus-full_mesh_4.txt \\
        --topology topologies/full_mesh_4.csv
"""

import argparse
import csv
import heapq
import ipaddress
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------

@dataclass
class Link:
    node1: str
    node2: str
    delay_ms: int
    node1_ip: str   # CIDR, e.g. "10.0.12.1/30"
    node2_ip: str


def load_topology(path: Path) -> list[Link]:
    links: list[Link] = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].lstrip().startswith("#"):
                continue
            host1, host2, delay_ms, host1_ip, host2_ip = [c.strip() for c in row]
            links.append(Link(host1, host2, int(delay_ms), host1_ip, host2_ip))
    return links


def build_topology_maps(links: list[Link]):
    """
    Returns:
      ip_to_host  : bare IP string -> host name
      host_ips    : host name     -> list of bare IP strings
      link_delay  : (h1, h2)     -> delay_ms  (both directions stored)
    """
    ip_to_host: dict[str, str] = {}
    host_ips: dict[str, list[str]] = {}
    link_delay: dict[tuple[str, str], int] = {}

    for link in links:
        h1, h2 = link.node1, link.node2
        ip1 = link.node1_ip.split("/")[0]
        ip2 = link.node2_ip.split("/")[0]

        ip_to_host[ip1] = h1
        ip_to_host[ip2] = h2

        host_ips.setdefault(h1, []).append(ip1)
        host_ips.setdefault(h2, []).append(ip2)

        link_delay[(h1, h2)] = link.delay_ms
        link_delay[(h2, h1)] = link.delay_ms

    return ip_to_host, host_ips, link_delay


# ---------------------------------------------------------------------------
# Routing table parsing
# ---------------------------------------------------------------------------

@dataclass
class Route:
    network: ipaddress.IPv4Network
    via_ip: str | None   # next-hop IP  (set for "via" routes)
    dev: str | None      # interface    (set for "scope link" routes, via_ip is None)


def parse_routing_tables(txt_path: Path) -> dict[str, list[Route]]:
    """
    Parse the '=== Routing Tables ===' section of a .txt experiment file.

    Works with both raw experiment output and manually annotated report files
    (inline comments after '(' are stripped).

    Returns: host_name -> list[Route]  (unsorted; caller should sort for LPM)
    """
    tables: dict[str, list[Route]] = {}
    current_host: str | None = None
    in_section = False

    with open(txt_path) as f:
        for raw_line in f:
            line = raw_line.rstrip()

            if "=== Routing Tables ===" in line:
                in_section = True
                continue
            if not in_section:
                continue
            # Stop at the start of any subsequent === section
            if line.startswith("===") and "Routing Tables" not in line:
                break

            # Section header: --- HOSTNAME ---
            if line.startswith("--- ") and line.rstrip().endswith("---"):
                current_host = line[4:].rstrip()[:-3].strip()
                tables[current_host] = []
                continue

            if current_host is None:
                continue

            # Strip inline annotations (e.g. "(via B: 10ms — optimal)") and comments
            stripped = line.split("(")[0].split("#")[0].strip()
            if not stripped:
                continue

            parts = stripped.split()
            if not parts:
                continue

            # Destination prefix: bare IP treated as /32 host route
            prefix = parts[0]
            if "/" not in prefix:
                prefix += "/32"
            try:
                network = ipaddress.IPv4Network(prefix, strict=False)
            except ValueError:
                continue

            via_ip: str | None = None
            dev: str | None = None

            if "via" in parts:
                idx = parts.index("via")
                via_ip = parts[idx + 1]
            elif "dev" in parts:
                idx = parts.index("dev")
                dev = parts[idx + 1]
            else:
                continue

            tables[current_host].append(Route(network=network, via_ip=via_ip, dev=dev))

    return tables


# ---------------------------------------------------------------------------
# LPM lookup
# ---------------------------------------------------------------------------

def lpm(routes: list[Route], dst_ip: str) -> Route | None:
    """Longest-prefix match. `routes` must be sorted longest-prefix-first."""
    addr = ipaddress.ip_address(dst_ip)
    for route in routes:
        if addr in route.network:
            return route
    return None


# ---------------------------------------------------------------------------
# Forwarding simulation
# ---------------------------------------------------------------------------

def simulate_delay(
    src: str,
    dst_ip: str,
    tables: dict[str, list[Route]],
    ip_to_host: dict[str, str],
    host_ips: dict[str, list[str]],
    link_delay: dict[tuple[str, str], int],
) -> float | None:
    """
    Simulate one-way packet forwarding from `src` to `dst_ip`.

    At each node:
      - If dst_ip is local, return accumulated delay.
      - For "via <gw>" routes: next hop = host owning gw IP.
      - For "scope link" routes: dst_ip is on a directly-attached subnet,
        next hop = host owning dst_ip.

    Returns total delay (ms) or None if unreachable (loop, no route, or
    unknown next-hop).
    """
    current = src
    total = 0.0
    visited: set[str] = set()

    while True:
        # Packet delivered: dst_ip is a local address of this node
        if dst_ip in host_ips.get(current, []):
            return total

        if current in visited:
            return None  # forwarding loop

        visited.add(current)

        route = lpm(tables.get(current, []), dst_ip)
        if route is None:
            return None  # no matching route

        if route.via_ip is not None:
            next_hop = ip_to_host.get(route.via_ip)
        else:
            # scope link: dst_ip is directly reachable; find which host owns it
            next_hop = ip_to_host.get(dst_ip)

        if next_hop is None:
            return None  # next-hop IP not in topology

        hop_delay = link_delay.get((current, next_hop))
        if hop_delay is None:
            return None  # no physical link between these nodes

        total += hop_delay
        current = next_hop


# ---------------------------------------------------------------------------
# Dijkstra (optimal routing)
# ---------------------------------------------------------------------------

def dijkstra(src: str, link_delay: dict[tuple[str, str], int]) -> dict[str, float]:
    """Compute shortest-path distances from `src` to all reachable nodes."""
    adj: dict[str, list[tuple[str, int]]] = {}
    for (u, v), d in link_delay.items():
        adj.setdefault(u, []).append((v, d))

    dist: dict[str, float] = {src: 0.0}
    pq: list[tuple[float, str]] = [(0.0, src)]

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float("inf")):
            continue
        for v, w in adj.get(u, []):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))

    return dist


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(txt_path: Path, topology_path: Path) -> None:
    links = load_topology(topology_path)
    ip_to_host, host_ips, link_delay = build_topology_maps(links)
    hosts = sorted(host_ips.keys())

    tables = parse_routing_tables(txt_path)
    # Sort each host's routes longest-prefix-first for correct LPM
    for routes in tables.values():
        routes.sort(key=lambda r: r.network.prefixlen, reverse=True)

    # Optimal distances (Dijkstra from each source)
    optimal_dist: dict[str, dict[str, float]] = {h: dijkstra(h, link_delay) for h in hosts}

    # ------------------------------------------------------------------
    # Per-IP simulation
    # For every (src, dst_ip), compute experiment delay and optimal delay.
    # Optimal delay to dst_ip = Dijkstra distance from src to host(dst_ip).
    # ------------------------------------------------------------------
    @dataclass
    class IPResult:
        src: str
        dst_host: str
        dst_ip: str
        exp_delay: float | None   # None = unreachable or loop
        opt_delay: float

    ip_results: list[IPResult] = []
    for src in hosts:
        for dst in hosts:
            if src == dst:
                continue
            opt = optimal_dist[src].get(dst, float("inf"))
            for dst_ip in host_ips.get(dst, []):
                exp = simulate_delay(src, dst_ip, tables, ip_to_host, host_ips, link_delay)
                ip_results.append(IPResult(src, dst, dst_ip, exp, opt))

    # ------------------------------------------------------------------
    # Aggregate to host-to-host level.
    # Delay = average over all of dst's IPs (captures per-IP inefficiencies).
    # If ANY IP of dst is unreachable the pair is flagged as unreachable.
    # ------------------------------------------------------------------
    @dataclass
    class PairResult:
        src: str
        dst: str
        exp_delay: float | None
        opt_delay: float

    pair_results: list[PairResult] = []
    for src in hosts:
        for dst in hosts:
            if src == dst:
                continue
            relevant = [r for r in ip_results if r.src == src and r.dst_host == dst]
            opt = relevant[0].opt_delay if relevant else float("inf")
            if any(r.exp_delay is None for r in relevant):
                pair_results.append(PairResult(src, dst, None, opt))
            else:
                avg_exp = sum(r.exp_delay for r in relevant if r.exp_delay is not None) / len(relevant)
                pair_results.append(PairResult(src, dst, avg_exp, opt))

    reachable = [p for p in pair_results if p.exp_delay is not None]
    unreachable = [p for p in pair_results if p.exp_delay is None]

    # ------------------------------------------------------------------
    # Summary metrics
    # ------------------------------------------------------------------
    avg_exp = sum(p.exp_delay for p in reachable if p.exp_delay is not None) / len(reachable) if reachable else float("nan")
    avg_opt = sum(p.opt_delay for p in reachable) / len(reachable) if reachable else float("nan")

    pair_deltas = sorted(
        [(p.src, p.dst, p.exp_delay - p.opt_delay, p.exp_delay, p.opt_delay) for p in reachable if p.exp_delay is not None],
        key=lambda x: -x[2],
    )
    worst = pair_deltas[0] if pair_deltas else None

    # Per-IP results that are worse than optimal (> 0.5 ms tolerance)
    subopt_ips = sorted(
        [r for r in ip_results if r.exp_delay is not None and r.exp_delay > r.opt_delay + 0.5],
        key=lambda r: -(r.exp_delay - r.opt_delay) if r.exp_delay is not None else 0,
    )

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    print(f"Experiment : {txt_path.name}")
    print(f"Topology   : {topology_path.name}")
    print(f"Hosts      : {', '.join(hosts)}")
    print(f"Pairs      : {len(pair_results)}  ({len(hosts)} hosts × {len(hosts) - 1} destinations)")
    if unreachable:
        pairs_str = ", ".join(f"{p.src}→{p.dst}" for p in unreachable)
        print(f"Unreachable: {pairs_str}")
    print()

    overhead_abs = avg_exp - avg_opt
    overhead_pct = 100 * overhead_abs / avg_opt if avg_opt else float("nan")
    print("Average host-to-host delay  (mean over all pairs; per-pair = avg over dst IPs):")
    print(f"  Experiment : {avg_exp:.2f} ms")
    print(f"  Optimal    : {avg_opt:.2f} ms")
    print(f"  Overhead   : +{overhead_abs:.2f} ms  ({overhead_pct:.1f}%)")
    print()

    if worst:
        ws, wd, wdelta, wexp, wopt = worst
        print(f"Max delta (host-to-host):")
        print(f"  {ws} → {wd}  —  {wexp:.2f} ms experiment  vs  {wopt:.0f} ms optimal  (delta = +{wdelta:.2f} ms)")
    print()

    # Non-optimal host pairs table
    non_opt = [(s, d, delta, exp, opt) for s, d, delta, exp, opt in pair_deltas if delta > 0.5]
    if non_opt:
        print(f"Suboptimal host pairs  ({len(non_opt)} of {len(reachable)}, sorted by penalty):")
        hdr = f"  {'src→dst':<10}  {'experiment':>12}  {'optimal':>10}  {'delta':>10}"
        print(hdr)
        print(f"  {'-'*10}  {'-'*12}  {'-'*10}  {'-'*10}")
        for s, d, delta, exp, opt in non_opt:
            print(f"  {s+'→'+d:<10}  {exp:>10.2f} ms  {opt:>8.0f} ms  {delta:>+9.2f} ms")
        print()
    else:
        print("All host pairs are optimally routed (host level).")
        print()

    # Non-optimal IP-level paths table
    if subopt_ips:
        print(f"Suboptimal IP-level paths  ({len(subopt_ips)} IPs, sorted by penalty):")
        hdr = f"  {'src → dst_ip':<24}  {'host':>6}  {'experiment':>12}  {'optimal':>10}  {'delta':>10}"
        print(hdr)
        print(f"  {'-'*24}  {'-'*6}  {'-'*12}  {'-'*10}  {'-'*10}")
        for r in subopt_ips:
            label = f"{r.src} → {r.dst_ip}"
            delta = r.exp_delay - r.opt_delay if r.exp_delay is not None else 0
            print(f"  {label:<24}  {r.dst_host:>6}  {r.exp_delay:>10.2f} ms  {r.opt_delay:>8.0f} ms  {delta:>+9.2f} ms")
    else:
        print("All IP-level paths are optimal.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare experiment routing tables against Dijkstra-optimal paths.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--txt", "-x", required=True, metavar="FILE",
        help="Experiment .txt file containing the routing tables",
    )
    parser.add_argument(
        "--topology", "-t", required=True, metavar="FILE",
        help="Topology CSV file (same format as topologies/*.csv)",
    )
    args = parser.parse_args()
    analyze(Path(args.txt), Path(args.topology))


if __name__ == "__main__":
    main()
