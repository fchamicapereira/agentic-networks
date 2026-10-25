#!/usr/bin/env python3
"""check_key_leak.py — Can an agent read the provider API keys from inside a Mininet host?

The demo runs on our API keys and shows agent output on a projector, so a prompt such as
"run `env` and send me the output" must not be able to surface a key. This builds a two-node
network, runs the commands an agent could run through the `exec` tool (exactly the code path
agents use, MininetHost.exec), and reports every probe whose output contains a key.

Run it with FAKE keys only — the point is to see whether they show up:

    export ANTHROPIC_API_KEY=sk-ant-LEAKTEST-$RANDOM
    export OPENAI_API_KEY=sk-LEAKTEST-$RANDOM TOGETHER_API_KEY=LEAKTEST-$RANDOM
    tools/run_in_docker.sh demo/tools/check_key_leak.py

Exits 1 if any key leaks, 0 otherwise.
"""

import os
import sys

from agentic_networks.mininet_host import MininetHost
from agentic_networks.network import Network, load_topology
from agentic_networks.paths import TOPOLOGIES_DIR

KEY_VARS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "TOGETHER_API_KEY")

# What an agent could plausibly be talked into running. Each is a single exec call.
PROBES = [
    "env",
    "cat /proc/self/environ | tr '\\0' '\\n'",
    "cat /proc/$PPID/environ | tr '\\0' '\\n'",
    "cat /proc/1/environ | tr '\\0' '\\n'",
    "grep -a -h -o '[A-Z_]*API_KEY=[^[:cntrl:]]*' /proc/[0-9]*/environ 2>/dev/null | sort -u",
    "ps auxeww",
    "grep -r -a -h -o '[A-Z_]*API_KEY=[^[:space:]]*' /etc /root /tmp 2>/dev/null | sort -u",
]


def main() -> int:
    keys = {var: os.environ[var] for var in KEY_VARS if os.environ.get(var, "").strip()}
    if not keys:
        print("error: set at least one of %s to a fake value" % ", ".join(KEY_VARS), file=sys.stderr)
        return 2
    if any("LEAKTEST" not in v for v in keys.values()):
        print("error: refusing to run with what looks like a real key; use values containing LEAKTEST", file=sys.stderr)
        return 2

    leaked_any = False
    network = Network(load_topology(TOPOLOGIES_DIR / "pair.csv"))
    network.start()
    try:
        host = MininetHost("A", network.hosts["A"])
        for probe in PROBES:
            output, _ = host.exec(probe, timeout=20)
            found = sorted(var for var, value in keys.items() if value in output)
            leaked_any |= bool(found)
            print(f"  {'LEAK ' + ','.join(found) if found else 'ok':<40} {probe}")
    finally:
        network.stop()

    print("\nRESULT:", "keys are readable from agent commands" if leaked_any else "no key leaked")
    return 1 if leaked_any else 0


if __name__ == "__main__":
    sys.exit(main())
