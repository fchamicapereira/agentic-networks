#!/usr/bin/env python3
"""check_key_leak.py — Can an agent get at our model access from inside a Mininet host?

The demo runs on our API keys and attendees write the prompts, so a prompt such as "run `env`
and send me the output" must not surface a key. This builds a two-node network and runs, from
a Mininet host, the commands an agent could run through the `exec` tool (exactly the code path
agents use, MininetHost.exec). Every probe's full output is printed, so a wrapper outside the
container can search it for keys the container was never meant to have.

run_in_docker.sh runs every experiment through tools/llm_proxy.py, so the container only holds
a throwaway run token in place of each key. Seeing the token is expected. What must hold: the
harness reaches the proxy, and an agent does not. That the real keys never appear is checked
by the wrapper, demo/tools/test_key_isolation.sh, which runs this with fake ones. Exits 1 on a
failure, 0 otherwise.
"""

import os
import subprocess
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


def proxy_request(token: str, base_url: str) -> str:
    """A curl call to the proxy as the harness would make it; prints the HTTP status, or 000."""
    return (f"curl -s -m 5 -o /dev/null -w '%{{http_code}}' -X POST -H 'x-api-key: {token}' "
            f"-H 'content-type: application/json' -d '{{}}' {base_url}/v1/messages")


def main() -> int:
    values = {var: os.environ[var] for var in KEY_VARS if os.environ.get(var, "").strip()}
    proxy = os.environ.get("ANTHROPIC_BASE_URL", "")
    if not values or not proxy:
        print("error: run this with tools/run_in_docker.sh, which gives it the proxy and a run token", file=sys.stderr)
        return 2
    print(f"Through the LLM proxy at {proxy}")

    failed = False
    network = Network(load_topology(TOPOLOGIES_DIR / "pair.csv"))
    network.start()
    try:
        host = MininetHost("A", network.hosts["A"])
        print("\nWhat an agent can read:")
        for probe in PROBES:
            output, _ = host.exec(probe, timeout=20)
            found = sorted(var for var, value in values.items() if value in output)
            verdict = "token visible (expected: worthless outside the proxy)" if found else "ok"
            print(f"  {verdict:<55} {probe}")
            # The full output, for test_key_isolation.sh to search for the proxy's real keys.
            print("    | " + output.replace("\n", "\n    | ").rstrip())

        token = values.get("ANTHROPIC_API_KEY", "")
        # From the harness's own position (the container's main namespaces): must get an
        # answer. Any HTTP status means the proxy is reachable and responding.
        harness = subprocess.run(proxy_request(token, proxy), shell=True, capture_output=True, text=True).stdout.strip()
        ok = harness not in ("", "000")
        failed |= not ok
        print(f"\nHarness -> proxy: HTTP {harness or '000'}  {'ok' if ok else 'FAIL: the harness cannot reach the proxy'}")
        # From an agent's position (a Mininet host): must not get through at all.
        agent, _ = host.exec(proxy_request(token, proxy), timeout=20)
        agent = agent.strip()
        blocked = agent.endswith("000")
        failed |= not blocked
        print(f"Agent   -> proxy: {'no connection  ok' if blocked else 'HTTP ' + agent + '  FAIL: an agent can reach the proxy'}")
    finally:
        network.stop()

    print("\nRESULT:", "FAIL" if failed else "ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
