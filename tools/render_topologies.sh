#!/usr/bin/env bash
# render_topologies.sh — Generate topology and optimal-routing PDFs for every
# topology CSV in the topologies/ directory.
#
# Run from anywhere; the script resolves paths relative to the repo root.
#
# Output:
#   topologies/<name>.pdf                  — physical topology
#   topologies/<name>-optimal-routing.pdf  — min-delay optimal routing overlay

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
REPO_ROOT="$SCRIPT_DIR/.."
TOPO_DIR="$REPO_ROOT/topologies"

cd "$REPO_ROOT"

for csv in "$TOPO_DIR"/*.csv; do
    name="$(basename "$csv" .csv)"
    echo "==> $name"
    python tools/render_topology.py "$csv" -o "$TOPO_DIR/$name.pdf"
    python tools/optimal_routing.py       "$csv" -o "$TOPO_DIR/$name-optimal-routing.pdf"
done
