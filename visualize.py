"""
visualize.py — Generate a Graphviz PDF of the network topology and routing state.

Physical links are drawn as black undirected edges labelled with their delay.
Routing decisions are drawn as dashed directed edges, one per (src, dst) pair,
coloured by destination and connecting src to its next hop toward that destination.
"""

from graphviz import Digraph

from network import Network, RoutingRule

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


def generate_network_pdf(network: Network, routing_rules: list[RoutingRule], output_path: str) -> None:
    """
    Render the network topology and final routing state to a PDF.

    Physical links are black undirected edges labelled with delay (ms).
    For each (src, dst) pair a dashed directed edge coloured by dst shows
    the next hop src uses to reach dst.

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
        node_attr={"shape": "plaintext", "fontname": "Helvetica"},
        edge_attr={"fontsize": "9", "fontname": "Helvetica"},
    )

    for name in node_names:
        ifaces = network.ifaces_per_host[name]
        iface_rows = "".join(
            f'<TR><TD PORT="{i.iface}" BORDER="1" ALIGN="LEFT">'
            f'<FONT POINT-SIZE="8" COLOR="white">{i.iface}<BR/>{i.ip}</FONT></TD></TR>'
            for i in ifaces
        )
        label = (
            f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2" BGCOLOR="{node_color[name]}">'
            f'<TR><TD><FONT COLOR="white"><B>{name}</B></FONT></TD></TR>'
            f"{iface_rows}"
            f"</TABLE>>"
        )
        dot.node(name, label=label)

    def _find_iface(node: str, peer: str):
        for iface in network.ifaces_per_host[node]:
            if iface.peer == peer:
                return iface
        return None

    for link in network.links:
        iface1 = _find_iface(link.node1, link.node2)
        iface2 = _find_iface(link.node2, link.node1)
        tail = f"{link.node1}:{iface1.iface}" if iface1 else link.node1
        head = f"{link.node2}:{iface2.iface}" if iface2 else link.node2
        dot.edge(
            tail,
            head,
            label=f" {link.delay_ms}ms",
            color="black",
            dir="none",
            penwidth="2.0",
        )

    for rule in routing_rules:
        dot.edge(
            rule.source_host,
            rule.next_hop,
            color=node_color[rule.destination_host],
            style="dashed",
            penwidth="1.5",
            constraint="false",
        )

    dot.render(output_path, format="pdf", cleanup=True)
