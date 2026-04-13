#!/usr/bin/env python3

"""
visualize_network_routes.py — Render a network topology and routing state to PDF.

Physical links are drawn as thick grey lines labelled with their delay at the
midpoint.  Routing decisions are shown as compact text labels placed just
outside each source node along the edge toward the next hop.  Each label lists
the destinations routed via that edge, coloured to match the source node.

Layout uses networkx's Kamada-Kawai algorithm with fourth-root-compressed
all-pairs shortest-path distances so nodes that are latency-close appear
spatially close without dense clusters collapsing into a single point.
"""

import argparse

from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # headless — no display required
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import networkx as nx
import numpy as np

from network import Interface, Link, Network, RoutingRule, load_topology


PALETTE = [
    "#e6194b",  # red
    "#3cb44b",  # green
    "#4363d8",  # blue
    "#f58231",  # orange
    "#911eb4",  # purple
    "#42d4f4",  # cyan
    "#f032e6",  # magenta
    "#bfef45",  # lime
    "#469990",  # teal
    "#800000",  # maroon
]

# ── geometry constants (in normalised axis-data units) ────────────────────────
_NODE_RADIUS = 0.030  # radius of the filled node circle


def _layout(links: list[Link]) -> dict[str, np.ndarray]:
    """
    Kamada-Kawai layout with fourth-root-compressed shortest-path distances.

    Kamada-Kawai minimises the difference between Euclidean distances and
    graph-theoretic distances, producing clean layouts that reflect network
    latency structure.

    The challenge with real topologies is that path distances accumulate over
    hops: a leaf-to-leaf path through a backbone ring has a much larger total
    delay than any single link.  Using raw delays as edge weights makes KK
    compress dense clusters into tiny regions while stretching long-haul paths
    across most of the canvas.

    Fix: compute all-pairs shortest-path distances in real delay-ms, then apply
    a fourth-root (^0.25) compression before passing the distance matrix to KK.
    This gives a ~3× wider relative spread to close-together nodes while still
    preserving the global topology structure.

    X and Y are normalised independently to fill the full 10:7 figure canvas.
    Y is scaled to 7/10 of the X range so that node circles stay circular
    under set_aspect("equal").
    """
    G = nx.Graph()
    for link in links:
        G.add_edge(link.node1, link.node2, delay=link.delay_ms)

    nodes = sorted(G.nodes())
    sp = dict(nx.all_pairs_dijkstra_path_length(G, weight="delay"))
    dist = {a: {b: sp[a][b] ** 0.10 for b in nodes} for a in nodes}

    raw = nx.kamada_kawai_layout(G, dist=dist)

    coords = np.array([raw[n] for n in nodes])
    lo, hi = coords.min(axis=0), coords.max(axis=0)
    span = np.where(hi - lo > 0, hi - lo, 1.0)

    # Normalise X to [0.09, 0.91] (span 0.82) and Y to [0.063, 0.637]
    # (span 0.574 = 0.82 × 7/10) so equal-aspect axes fill the 10×7 figure.
    return {
        node: np.array([
            (raw[node][0] - lo[0]) / span[0] * 0.82 + 0.09,
            (raw[node][1] - lo[1]) / span[1] * 0.574 + 0.063,
        ])
        for node in nodes
    }


def generate_network_pdf(
    network: Network,
    routing_rules: list[RoutingRule],
    output_path: str,
) -> None:
    """
    Render the network topology and routing state to a PDF.

    Physical links → thick grey lines with a boxed delay label at the midpoint.
    Routing rules  → compact text labels just outside each source node along the
                     edge toward the next hop.  Each label lists all destinations
                     routed via that edge, coloured to match the source node.

    Args:
        network:       Network dataclass (topology + interface info).
        routing_rules: RoutingRule(source_host, destination, next_hop) list.
        output_path:   Destination path without extension; .pdf is appended.
    """
    node_names = sorted(network.hosts.keys())
    node_color: dict[str, str] = {
        name: PALETTE[i % len(PALETTE)] for i, name in enumerate(node_names)
    }

    pos = _layout(network.links)

    n = len(node_names)
    node_radius = min(_NODE_RADIUS, 0.10 / np.sqrt(n))
    node_fontsize = max(5.5, 9.0 * node_radius / _NODE_RADIUS)

    # ── figure ────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_aspect("equal")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.05, 0.69)  # span 0.74 ≈ 1.04 × 7/10; keeps circles circular
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # ── physical links ────────────────────────────────────────────────────────
    # Build a quick lookup: (node, peer) → interface name
    iface_name: dict[tuple[str, str], str] = {}
    for node, ifaces in network.ifaces_per_host.items():
        for iface in ifaces:
            iface_name[(node, iface.peer)] = iface.iface

    for link in network.links:
        p1, p2 = pos[link.node1], pos[link.node2]
        ax.plot(
            [p1[0], p2[0]], [p1[1], p2[1]],
            color="#666666", linewidth=2.5, zorder=1, solid_capstyle="round",
        )
        mid = (p1 + p2) / 2.0
        edge_vec = p2 - p1
        edge_len = np.linalg.norm(edge_vec)
        perp = (
            np.array([-edge_vec[1], edge_vec[0]]) / edge_len
            if edge_len > 0 else np.array([0.0, 1.0])
        )
        left_iface = iface_name.get((link.node1, link.node2), link.node1).replace("-eth", "")
        right_iface = iface_name.get((link.node2, link.node1), link.node2).replace("-eth", "")
        delay_label = f"{left_iface}<-{link.delay_ms}ms->{right_iface}"
        ax.text(
            mid[0] + perp[0] * 0.03, mid[1] + perp[1] * 0.03,
            delay_label,
            ha="center", va="center", fontsize=9, color="#222222",
            bbox=dict(
                boxstyle="round,pad=0.18", facecolor="white",
                edgecolor="#bbbbbb", linewidth=0.8, alpha=0.92,
            ),
            zorder=2,
        )

    # ── routing labels ────────────────────────────────────────────────────────
    # For each directed edge (src → next_hop), show a compact comma-separated
    # list of destinations just outside the source node along the edge.
    # Coloured to match the source node so the association is unambiguous.
    edge_dests: dict[tuple[str, str], list[str]] = defaultdict(list)
    for rule in routing_rules:
        edge_dests[(rule.source_host, rule.next_hop)].append(rule.destination)

    for (src, nhop), dests in edge_dests.items():
        p_src = pos[src]
        p_nhop = pos[nhop]
        vec = p_nhop - p_src
        edge_len = np.linalg.norm(vec)
        if edge_len == 0:
            continue
        unit = vec / edge_len
        label_pos = p_src + unit * (node_radius + 0.022)
        ax.text(
            label_pos[0], label_pos[1],
            ",".join(sorted(dests)),
            ha="center", va="center",
            fontsize=6.5, color=node_color[src], fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.10", facecolor="white",
                edgecolor="none", alpha=0.85,
            ),
            zorder=4,
        )

    # ── nodes (on top of everything) ──────────────────────────────────────────
    for name in node_names:
        x, y = pos[name]
        ax.add_patch(plt.Circle((x, y), node_radius, color=node_color[name], zorder=5))
        ax.text(
            x, y, name,
            ha="center", va="center",
            fontsize=node_fontsize, fontweight="bold", color="white", zorder=6,
        )

    plt.tight_layout(pad=0.3)
    out = output_path if output_path.endswith(".pdf") else output_path + ".pdf"
    with PdfPages(out) as pdf:
        pdf.savefig(fig, bbox_inches="tight", dpi=150)
    plt.close(fig)


# ── helper shared by simple_routing.py and optimal_routing.py ────────────────

def _network_from_links(links: list[Link]) -> Network:
    """Build a Network dataclass from a list of links without starting Mininet."""
    ifaces_per_host: dict[str, list[Interface]] = defaultdict(list)
    counters: dict[str, int] = defaultdict(int)
    for link in links:
        for node, ip, peer, peer_ip in [
            (link.node1, link.node1_ip, link.node2, link.node2_ip),
            (link.node2, link.node2_ip, link.node1, link.node1_ip),
        ]:
            ifaces_per_host[node].append(
                Interface(
                    iface=f"{node}-eth{counters[node]}",
                    ip=ip,
                    peer=peer,
                    peer_ip=peer_ip,
                )
            )
            counters[node] += 1
    hosts = {name: None for name in ifaces_per_host}  # type: ignore[dict-item]
    return Network(net=None, hosts=hosts, ifaces_per_host=dict(ifaces_per_host), links=links)  # type: ignore[arg-type]


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize a network topology CSV as a PDF.")
    parser.add_argument("topology", help="Path to the topology CSV file")
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output path (with or without .pdf; default: topology filename without .csv)",
    )
    args = parser.parse_args()

    links  = load_topology(args.topology)
    output = (args.output or args.topology.removesuffix(".csv")).removesuffix(".pdf")
    generate_network_pdf(_network_from_links(links), [], output)
    print(f"Written to {output}.pdf")


if __name__ == "__main__":
    main()
