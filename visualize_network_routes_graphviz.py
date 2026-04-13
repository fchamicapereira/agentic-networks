#!/usr/bin/env python3

"""
visualize.py — Generate a Graphviz PDF of the network topology and routing state.

Physical links are drawn as black undirected edges labelled with their delay.
Routing decisions are shown as small coloured arrow glyphs (▶dest) attached to
the source end of the physical edge they traverse, coloured by destination.
This keeps the diagram uncluttered: no extra edges are drawn, just small
per-direction labels on existing links.
"""

import argparse

from collections import defaultdict
from graphviz import Digraph

from network import Interface, Link, Network, RoutingRule, load_topology

PALETTE = [
    "#e6194b",
    "#3cb44b",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#42d4f4",
    "#f032e6",
    "#bfef45",
    "#fabed4",
    "#469990",
]


def _make_arrow_label(annotations: list[tuple[str, str]]) -> str:
    """
    Build an HTML-like Graphviz label containing one coloured arrow per routing rule.

    Each annotation is (color_hex, destination_name).  The result is placed as a
    taillabel or headlabel so it appears close to the source node, not spanning
    the full edge.
    """
    parts = [f'<FONT COLOR="{color}" POINT-SIZE="11">&#x25B6;{dst}</FONT>' for color, dst in annotations]
    return "<" + "<BR/>".join(parts) + ">"


def generate_network_pdf(network: Network, routing_rules: list[RoutingRule], output_path: str) -> None:
    """
    Render the network topology and final routing state to a PDF.

    Physical links are black undirected edges labelled with delay (ms).
    Routing decisions are shown as small coloured arrow glyphs (▶dest) placed
    at the source end of the physical edge they traverse, one glyph per
    (source, destination) pair.  Colour encodes the destination.

    Args:
        network:       The Mininet network (used for topology and interface info).
        routing_rules: Pre-parsed routing rules from Network.get_routing_rules().
        output_path:   Destination path without extension; .pdf is appended.
    """
    node_names = sorted(network.hosts.keys())
    node_color = {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(node_names)}

    dot = Digraph(
        name="network",
        graph_attr={"rankdir": "LR", "overlap": "false", "splines": "true"},
        node_attr={"shape": "circle", "fontname": "Helvetica", "fontcolor": "white", "style": "filled", "width": "0.6"},
        edge_attr={"fontsize": "9", "fontname": "Helvetica"},
    )

    for name in node_names:
        dot.node(name, label=name, fillcolor=node_color[name])

    # Build routing annotation index: directed edge (tail, head) -> [(color, dst)]
    # The edge is stored as (source_host, next_hop) which matches link.node1/node2 order
    # or the reverse, so we index both orderings.
    tail_annotations: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for rule in routing_rules:
        dst_host = rule.destination.rstrip("0123456789")
        tail_annotations[(rule.source_host, rule.next_hop)].append(
            (node_color.get(dst_host, node_color[rule.destination]), rule.destination)
        )

    for link in network.links:
        # node1→node2 direction annotations (taillabel = near node1)
        fwd = tail_annotations.get((link.node1, link.node2), [])
        # node2→node1 direction annotations (headlabel = near node2)
        rev = tail_annotations.get((link.node2, link.node1), [])

        extra: dict[str, str] = {}
        if fwd:
            extra["taillabel"] = _make_arrow_label(fwd)
        if rev:
            extra["headlabel"] = _make_arrow_label(rev)

        dot.edge(
            link.node1,
            link.node2,
            label=f" {link.delay_ms}ms",
            color="black",
            dir="none",
            penwidth="2.0",
            labeldistance="2.5",
            labelangle="20",
            **extra,
        )

    dot.render(output_path, format="pdf", cleanup=True)


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
    parser.add_argument("-o", "--output", default=None, help="Output path (with or without .pdf extension; default: topology filename)")
    args = parser.parse_args()

    links = load_topology(args.topology)
    output = (args.output or args.topology.removesuffix(".csv")).removesuffix(".pdf")
    generate_network_pdf(_network_from_links(links), [], output)
    print(f"Written to {output}.pdf")


if __name__ == "__main__":
    main()
