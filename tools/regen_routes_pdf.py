#!/usr/bin/env python3
"""
regen_routes_pdf.py — Re-render all *-routes.pdf figures from experiment logs.

Reads the final routing tables recorded in each .txt log file and regenerates
the corresponding *-routes.pdf without re-running the experiment.

Usage:
    python tools/regen_routes_pdf.py            # regenerate all logs/*.txt
    python tools/regen_routes_pdf.py path/to/x.txt ...  # specific files
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agentic_networks.network import load_topology, Network
from agentic_networks.routes import Route


def _normalize_hosts(
    route_tables: dict[str, str],
    topo_nodes: list[str],
) -> dict[str, str]:
    """Remap old host names to current topology node names if they differ.

    Matches by sorted order: the i-th sorted host in the route tables maps to
    the i-th sorted node in the topology (e.g. h1→A, h2→B, h3→C, h4→D).
    Also rewrites interface references inside route lines (e.g. "h1-eth0"→"A-eth0").
    """
    old_names = sorted(route_tables.keys())
    new_names = sorted(topo_nodes)
    if old_names == new_names:
        return route_tables
    if len(old_names) != len(new_names):
        return route_tables  # can't map — return as-is and let caller skip

    mapping = dict(zip(old_names, new_names))
    result: dict[str, str] = {}
    for old_host, content in route_tables.items():
        # Replace "hN-eth" with "X-eth" in route lines, longest names first
        # to avoid partial substitution (e.g. h1 matching inside h10).
        for old, new in sorted(mapping.items(), key=lambda x: -len(x[0])):
            content = re.sub(rf"\b{re.escape(old)}-eth\b", f"{new}-eth", content)
        result[mapping[old_host]] = content
    return result


def parse_route_tables(txt: str) -> dict[str, str]:
    """Extract per-host routing table text from an experiment log.

    Looks for the '=== Routing Tables ===' section and splits it on
    '--- hN ---' host headers.  Returns {host_name: raw_route_lines}.
    """
    route_tables: dict[str, str] = {}
    in_section = False
    current_host: str | None = None
    current_lines: list[str] = []

    for line in txt.splitlines():
        if "=== Routing Tables ===" in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("==="):
            break  # next top-level section — stop
        m = re.match(r"^---\s+(\S+)\s+---", line)
        if m:
            if current_host is not None:
                route_tables[current_host] = "\n".join(current_lines)
            current_host = m.group(1)
            current_lines = []
        elif current_host is not None:
            current_lines.append(line)

    if current_host is not None:
        route_tables[current_host] = "\n".join(current_lines)

    return route_tables


def find_topology(log_stem: str, topo_dir: Path) -> Path | None:
    """Return the topology CSV whose name appears as a suffix in log_stem.

    Tries longer names first so 'full_mesh_4' is matched before a hypothetical
    shorter name that could be a substring.
    """
    topos = sorted(topo_dir.glob("*.csv"), key=lambda p: len(p.stem), reverse=True)
    for topo in topos:
        if log_stem.endswith(f"-{topo.stem}") or log_stem == topo.stem:
            return topo
    return None


def regen(txt_path: Path, topo_dir: Path) -> None:
    topo_path = find_topology(txt_path.stem, topo_dir)
    if topo_path is None:
        print(f"  [skip] {txt_path.name}: no matching topology CSV")
        return

    txt = txt_path.read_text()
    route_tables = parse_route_tables(txt)
    if not route_tables:
        print(f"  [skip] {txt_path.name}: no routing tables found")
        return

    links = load_topology(topo_path)
    network = Network(links)
    topo_nodes = list(network.hosts.keys())
    route_tables = _normalize_hosts(route_tables, topo_nodes)
    route = Route.from_network(network, route_tables)

    out = str(txt_path.with_suffix("")) + "-routes"
    route.render_matplotlib(out)
    print(f"  [done] {out}.pdf  ({len(route.rules)} rules from {len(route_tables)} hosts)")


def main() -> None:
    topo_dir = REPO_ROOT / "topologies"

    if len(sys.argv) > 1:
        txt_files = [Path(p) for p in sys.argv[1:]]
    else:
        logs_dir = REPO_ROOT / "logs"
        txt_files = sorted(
            p for p in logs_dir.glob("*.txt")
            if not p.stem.endswith("-report")
        )

    for txt_path in txt_files:
        regen(txt_path, topo_dir)


if __name__ == "__main__":
    main()
