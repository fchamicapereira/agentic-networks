#!/usr/bin/env python3
import argparse

from agentic_networks.network import load_topology, Network
from agentic_networks.routes import Route


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a topology-only PDF")
    parser.add_argument("topology", help="Path to topology CSV")
    parser.add_argument("-o", "--output", default=None, help="Output PDF path (without .pdf)")
    args = parser.parse_args()

    links = load_topology(args.topology)
    output = (args.output or args.topology.removesuffix(".csv")).removesuffix(".pdf")
    Route(Network(links), []).render_matplotlib(output)
    print(f"Written to {output}.pdf")


if __name__ == "__main__":
    main()
