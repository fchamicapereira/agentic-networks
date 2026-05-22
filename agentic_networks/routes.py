"""Routing state and visualization for agentic network experiments."""

import ipaddress
from collections import defaultdict
from typing import NamedTuple

import matplotlib
matplotlib.use("Agg")  # headless — no display required
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import networkx as nx
import numpy as np
from graphviz import Digraph

from .network import Interface, Link, Network


class RoutingRule(NamedTuple):
    source_host: str
    destination: str  # destination interface name (e.g. "h4-eth0") or host name
    next_hop: str


_PALETTE = [
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

# Matplotlib geometry constants (in normalised axis-data units)
_NODE_RADIUS = 0.030


class Route:
    """Routing state for a network: the set of routing decisions and their visualization."""

    def __init__(self, network: Network, rules: list[RoutingRule]):
        self.network = network
        self.rules = rules

    @classmethod
    def from_network(cls, network: Network, route_tables: dict[str, str]) -> "Route":
        """Parse pre-collected routing tables and return a Route instance.

        Correlates raw `ip route show` output with the topology to produce
        RoutingRule(source_host, destination, next_hop) entries.  If all
        interfaces of a destination host are reached via the same next hop,
        destination is collapsed to the host name (e.g. "h4").  Otherwise one
        rule per interface is emitted using the interface name (e.g. "h4-eth0"),
        making split routing visible in figures.
        """
        rules = _parse_routing_rules(network, route_tables)
        return cls(network, rules)

    def render_matplotlib(self, output_path: str, show_delays: bool = False) -> None:
        """Render routing state to a PDF using matplotlib (Kamada-Kawai layout).

        Physical links → thick grey lines with a boxed delay label at the midpoint.
        Routing rules  → compact text labels just outside each source node along the
                         edge toward the next hop, coloured to match the source node.

        Args:
            output_path: Destination path without extension; .pdf is appended.
            show_delays: Whether to draw delay labels on each link.
        """
        _render_matplotlib(self.network, self.rules, output_path, show_delays)

    def render_graphviz(self, output_path: str) -> None:
        """Render routing state to a PDF using Graphviz.

        Physical links → black undirected edges labelled with delay (ms).
        Routing decisions → small coloured arrow glyphs (▶dest) at the source
                            end of the physical edge they traverse.

        Args:
            output_path: Destination path without extension; .pdf is appended.
        """
        _render_graphviz(self.network, self.rules, output_path)


# ── routing rule parsing ──────────────────────────────────────────────────────

def _parse_routing_rules(network: Network, route_tables: dict[str, str]) -> list[RoutingRule]:
    ip_to_node: dict[str, str] = {}
    for node_name, ifaces in network.ifaces_per_host.items():
        for iface in ifaces:
            ip_to_node[iface.ip.split("/")[0]] = node_name

    rules: list[RoutingRule] = []

    for src_name in network.hosts:
        raw = route_tables.get(src_name, "").strip()
        if not raw:
            continue

        routes: list[tuple[ipaddress.IPv4Network, str]] = []
        for line in raw.splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                dest = "0.0.0.0/0" if parts[0] == "default" else parts[0]
                net = ipaddress.ip_network(dest, strict=False)
            except ValueError:
                continue

            next_hop_node = None
            if "via" in parts:
                next_hop_node = ip_to_node.get(parts[parts.index("via") + 1])
            elif "dev" in parts:
                dev = parts[parts.index("dev") + 1]
                for iface in network.ifaces_per_host[src_name]:
                    if iface.iface == dev:
                        next_hop_node = ip_to_node.get(iface.peer_ip.split("/")[0])
                        break

            if next_hop_node:
                routes.append((net, next_hop_node))

        routes.sort(key=lambda r: r[0].prefixlen, reverse=True)

        def lpm(ip: str) -> str | None:
            addr = ipaddress.ip_address(ip)
            for net, next_hop_node in routes:
                if addr in net:
                    return next_hop_node
            return None

        for dst_name in network.hosts:
            if dst_name == src_name:
                continue
            loopback_entry = network.loopback_per_host.get(dst_name)
            if loopback_entry is None:
                continue
            nh = lpm(loopback_entry.split("/")[0])
            if nh is not None:
                rules.append(RoutingRule(src_name, dst_name, nh))

    return rules


# ── matplotlib renderer ───────────────────────────────────────────────────────

def _layout(links: list[Link]) -> dict[str, np.ndarray]:
    """
    Kamada-Kawai layout using hop-count distances.

    A spring-layout pass is used to seed KK's initial positions. This breaks
    the symmetry that causes KK to produce crossings on graphs where many
    nodes are equidistant from each other (e.g. bipartite-like topologies).
    """
    G = nx.Graph()
    for link in links:
        G.add_edge(link.node1, link.node2, delay=link.delay_ms)

    nodes = sorted(G.nodes())
    sp = dict(nx.all_pairs_shortest_path_length(G))
    dist = {a: {b: float(sp[a][b]) for b in nodes} for a in nodes}
    seed_pos = nx.spring_layout(G, seed=42, iterations=100)
    raw = nx.kamada_kawai_layout(G, dist=dist, pos=seed_pos)

    coords = np.array([raw[n] for n in nodes])
    lo, hi = coords.min(axis=0), coords.max(axis=0)
    span = np.where(hi - lo > 0, hi - lo, 1.0)

    return {
        node: np.array([
            (raw[node][0] - lo[0]) / span[0] * 0.82 + 0.09,
            (raw[node][1] - lo[1]) / span[1] * 0.574 + 0.063,
        ])
        for node in nodes
    }


def _render_matplotlib(network: Network, rules: list[RoutingRule], output_path: str, show_delays: bool = False) -> None:
    node_names = sorted(network.ifaces_per_host.keys())
    node_color: dict[str, str] = {
        name: _PALETTE[i % len(_PALETTE)] for i, name in enumerate(node_names)
    }

    pos = _layout(network.links)

    n = len(node_names)
    node_radius = min(_NODE_RADIUS, 0.10 / np.sqrt(n))
    node_fontsize = max(5.5, 9.0 * node_radius / _NODE_RADIUS)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_aspect("equal")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.05, 0.69)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    iface_name: dict[tuple[str, str], str] = {}
    for node, ifaces in network.ifaces_per_host.items():
        for iface in ifaces:
            iface_name[(node, iface.peer)] = iface.iface

    for link in network.links:
        p1, p2 = pos[link.node1], pos[link.node2]
        mid = (p1 + p2) / 2.0
        edge_vec = p2 - p1
        edge_len = np.linalg.norm(edge_vec)
        unit = edge_vec / edge_len if edge_len > 0 else np.array([0.0, 1.0])
        perp = np.array([-unit[1], unit[0]])

        if link.relationship == "peer/peer":
            ax.plot(
                [p1[0], p2[0]], [p1[1], p2[1]],
                color="#666666", linewidth=2.5, zorder=1, solid_capstyle="round",
            )
        else:
            cust_pos = p1 if link.relationship == "customer/provider" else p2
            prov_pos = p2 if link.relationship == "customer/provider" else p1
            vec = prov_pos - cust_pos
            vlen = np.linalg.norm(vec)
            if vlen > 0:
                vunit = vec / vlen
                ax.annotate(
                    "", xy=prov_pos - vunit * node_radius, xytext=cust_pos + vunit * node_radius,
                    xycoords="data", textcoords="data",
                    arrowprops=dict(arrowstyle="-|>", color="#666666", lw=2.5, mutation_scale=15),
                    zorder=1,
                )

        if show_delays:
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

    edge_dests: dict[tuple[str, str], list[str]] = defaultdict(list)
    for rule in rules:
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


# ── graphviz renderer ─────────────────────────────────────────────────────────

def _make_arrow_label(annotations: list[tuple[str, str]]) -> str:
    """Build an HTML-like Graphviz label with one coloured arrow per routing rule."""
    parts = [f'<FONT COLOR="{color}" POINT-SIZE="11">&#x25B6;{dst}</FONT>' for color, dst in annotations]
    return "<" + "<BR/>".join(parts) + ">"


def _render_graphviz(network: Network, rules: list[RoutingRule], output_path: str) -> None:
    node_names = sorted(network.ifaces_per_host.keys())
    node_color = {name: _PALETTE[i % len(_PALETTE)] for i, name in enumerate(node_names)}

    dot = Digraph(
        name="network",
        graph_attr={"rankdir": "LR", "overlap": "false", "splines": "true"},
        node_attr={"shape": "circle", "fontname": "Helvetica", "fontcolor": "white", "style": "filled", "width": "0.6"},
        edge_attr={"fontsize": "9", "fontname": "Helvetica"},
    )

    for name in node_names:
        dot.node(name, label=name, fillcolor=node_color[name])

    tail_annotations: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for rule in rules:
        dst_host = rule.destination.rstrip("0123456789")
        tail_annotations[(rule.source_host, rule.next_hop)].append(
            (node_color.get(dst_host, node_color[rule.destination]), rule.destination)
        )

    for link in network.links:
        if link.relationship == "customer/provider":
            tail_node, head_node = link.node1, link.node2
        elif link.relationship == "provider/customer":
            tail_node, head_node = link.node2, link.node1
        else:
            tail_node, head_node = link.node1, link.node2

        fwd = tail_annotations.get((tail_node, head_node), [])
        rev = tail_annotations.get((head_node, tail_node), [])

        extra: dict[str, str] = {}
        if fwd:
            extra["taillabel"] = _make_arrow_label(fwd)
        if rev:
            extra["headlabel"] = _make_arrow_label(rev)

        dot.edge(
            tail_node,
            head_node,
            label=f" {link.delay_ms}ms",
            color="black",
            dir="none" if link.relationship == "peer/peer" else "forward",
            penwidth="2.0",
            labeldistance="2.5",
            labelangle="20",
            **extra,
        )

    out = output_path.removesuffix(".pdf")
    dot.render(out, format="pdf", cleanup=True)
