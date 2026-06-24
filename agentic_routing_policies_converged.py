#!/usr/bin/env python3

# Routing experiment that starts from a converged, stable (but arbitrarily chosen, non-optimal)
# routing solution instead of a clean slate. Use this for scenarios where reaching connectivity
# is just setup and the experiment is about what the agents do afterwards (e.g. the bribe), not
# about whether they can converge. The clean-slate variant lives in agentic_routing_policies.py.

from agentic_routing_policies import run

if __name__ == "__main__":
    run(seed_stable=True)
