#!/usr/bin/env python3
"""Prototype and test for per-host PID/mount-namespace isolation (option 1).

Vanilla Mininet hosts get their own *network* namespace but share the *PID* (and
procfs) namespace with every other host — and with the experiment orchestrator.
As a result, any host running `ps` sees every other host's processes and the
runner's own command line (e.g. `kp_why_fix.py --fault overload`), letting an
agent read another org's private workload — and the scenario itself — straight
out of the process table.

Design of the fix (validated here):
  * Do NOT touch mininet's host shell or link setup. Mininet builds veths by
    running `ip link ... netns <other_host_pid>` *through a host's own shell*
    (mininet.util.makeIntfPair uses node1.cmd); if that shell lived in a private
    PID namespace it could not resolve the other host's root-namespace pid, and
    addLink fails with ESRCH. So the persistent shell stays in the root PID
    namespace and the network is built normally.
  * AFTER the network is built, give each host its own PID+mount-namespace
    "anchor" — a long-lived `unshare --pid --mount --fork --mount-proc sleep`
    process, running in that host's network namespace. Per-host anchors are
    *siblings* (all children of root), so a process in one anchor cannot see
    processes in another (nor the root-namespace orchestrator), while root still
    sees all.
  * Route BOTH the agent's commands and the host's own workload (fault loads,
    services) through `nsenter` into that host's anchor. An agent then sees only
    its own host's processes; the network-level signal (`ss`) is unaffected
    because the anchor shares the host's network namespace.

Why nsenter and not host.popen: mnexec's `-a` only re-enters the *network* and
*mount* namespaces (see `mnexec -h`), never the PID namespace, so it cannot give
an isolated `ps` view. nsenter can (`--pid`).

This script builds a tiny two-host network twice and checks whether h2 can see a
marker process planted on h1, and whether either host can see the orchestrator:
  * "vanilla"  — marker via host.cmd, agent exec via host.popen. Expected LEAK.
  * "isolated" — marker and agent exec via nsenter into per-host anchors.
                 Expected: h2 cannot see h1's marker or the orchestrator, yet
                 still sees the established connection from h1 in `ss`.

Requires root (Mininet). Run:  sudo python3 tools/test_host_isolation.py
"""

import os
import shutil
import subprocess
import sys
import time

from mininet.net import Mininet
from mininet.node import Host
from mininet.link import TCLink
from mininet.log import setLogLevel

MARKER = "ISOLATION_MARKER_7f3a91"          # unique token to grep for in `ps`
ORCH_MARKER = "test_host_isolation"          # this script's own name, in the orchestrator argv
H1_IP = "10.9.0.1"
H2_IP = "10.9.0.2"
PORT = 8080
LISTENER_PATH = "/tmp/iso_listener.py"

# A trivial TCP sink: accept connections and hold them open so the established
# connection stays visible in the peer's `ss` output for the duration of a check.
LISTENER_SRC = f"""\
import socket, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", {PORT}))
s.listen(32)
held = []
while True:
    try:
        conn, _ = s.accept()
        held.append(conn)
    except Exception:
        time.sleep(1)
"""

# A marker process: keeps MARKER in its argv (so it shows up in `ps`) and holds
# an established TCP connection to the peer open (so it shows up in the peer's
# `ss`). Mirrors EveLink's persistent load loops in the overload scenario.
MARKER_CMD = (
    f"nohup bash -c 'MARKER={MARKER}; "
    f"while true; do {{ sleep 3600; }} <>/dev/tcp/{H2_IP}/{PORT} 2>/dev/null; "
    f"sleep 0.3; done' >/dev/null 2>&1 &"
)


def configure(net):
    """Bring up interfaces and assign IPs on a freshly built 2-host net."""
    h1, h2 = net.get("h1"), net.get("h2")
    for host, ip in ((h1, H1_IP), (h2, H2_IP)):
        intf = f"{host.name}-eth0"
        host.cmd("ip link set lo up")
        host.cmd(f"ip addr add {ip}/24 dev {intf}")
        host.cmd(f"ip link set {intf} up")
    return h1, h2


def start_anchor(host) -> tuple[int, int]:
    """Create a private PID+mount namespace anchored by a long-lived `sleep`,
    running in this host's network namespace. Returns (outer_pid, inner_pid):
    outer is the `unshare` process (root PID ns) used for cleanup; inner is its
    forked child that actually lives in the new PID namespace and is the nsenter
    target."""
    outer = int(host.cmd(
        "unshare --pid --mount --fork --mount-proc sleep infinity "
        ">/dev/null 2>&1 & echo $!"
    ).strip().split()[-1])
    inner = outer
    for _ in range(20):
        try:
            kids = open(f"/proc/{outer}/task/{outer}/children").read().split()
        except OSError:
            kids = []
        if kids:
            inner = int(kids[0])
            break
        time.sleep(0.1)
    return outer, inner


def nsx(inner_pid: int, command: str) -> str:
    """Run a command inside a host's anchor namespace (net + mount + PID)."""
    proc = subprocess.Popen(
        ["nsenter", "--target", str(inner_pid), "--net", "--mount", "--pid",
         "--", "bash", "-c", command],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    out, _ = proc.communicate(timeout=15)
    return out.decode(errors="replace")


def exec_via_mnexec(host, command: str) -> str:
    """Current agent exec path: host.popen -> `mnexec -a` (net + mount only)."""
    proc = host.popen(command, shell=True, stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT)
    out, _ = proc.communicate(timeout=15)
    return out.decode(errors="replace")


def run_vanilla() -> dict:
    """Stock mininet: marker via host.cmd, agent view via host.popen (mnexec)."""
    net = Mininet(host=Host, link=TCLink)
    net.addHost("h1"); net.addHost("h2")
    net.addLink("h1", "h2")
    net.build()
    h1, h2 = configure(net)
    try:
        h2.cmd(f"nohup python3 {LISTENER_PATH} >/dev/null 2>&1 &")
        time.sleep(1.0)
        h1.cmd(MARKER_CMD)
        time.sleep(2.0)
        h2_ps = exec_via_mnexec(h2, "ps -e -o args=")
        return {
            "name": "vanilla",
            "h1_sees_own": MARKER in exec_via_mnexec(h1, "ps -e -o args="),
            "h2_sees_h1": MARKER in h2_ps,
            "h2_sees_orch": ORCH_MARKER in h2_ps,
            "h2_sees_conn": H1_IP in exec_via_mnexec(h2, "ss -tn"),
        }
    finally:
        h1.cmd(f"pkill -f {MARKER} 2>/dev/null; true")
        h2.cmd(f"pkill -f {LISTENER_PATH} 2>/dev/null; true")
        net.stop()


def run_isolated() -> dict:
    """Per-host anchors: marker and agent view via nsenter into private PID ns."""
    net = Mininet(host=Host, link=TCLink)
    net.addHost("h1"); net.addHost("h2")
    net.addLink("h1", "h2")
    net.build()
    h1, h2 = configure(net)
    a1_outer = a2_outer = None
    try:
        a1_outer, a1 = start_anchor(h1)
        a2_outer, a2 = start_anchor(h2)
        # Listener and marker run INSIDE their host's anchor namespace.
        nsx(a2, f"nohup python3 {LISTENER_PATH} >/dev/null 2>&1 &")
        time.sleep(1.0)
        nsx(a1, MARKER_CMD)
        time.sleep(2.0)
        h2_ps = nsx(a2, "ps -e -o args=")
        return {
            "name": "isolated",
            "h1_sees_own": MARKER in nsx(a1, "ps -e -o args="),
            "h2_sees_h1": MARKER in h2_ps,
            "h2_sees_orch": ORCH_MARKER in h2_ps,
            "h2_sees_conn": H1_IP in nsx(a2, "ss -tn"),
        }
    finally:
        for pid in (a1_outer, a2_outer):
            if pid:
                subprocess.run(["kill", "-9", str(pid)], capture_output=True)
        net.stop()


def preflight() -> None:
    if os.geteuid() != 0:
        sys.exit("This test builds a Mininet network and needs root. Re-run with sudo.")
    for tool in ("mnexec", "nsenter", "unshare"):
        if shutil.which(tool) is None:
            sys.exit(f"Required tool not found on PATH: {tool}")
    probe = subprocess.run(
        ["unshare", "--pid", "--mount", "--fork", "--mount-proc", "true"],
        capture_output=True,
    )
    if probe.returncode != 0:
        sys.exit("`unshare --pid --mount --fork --mount-proc` failed — PID-namespace "
                 f"isolation is not available here:\n{probe.stderr.decode(errors='replace')}")


def main() -> int:
    preflight()
    setLogLevel("error")
    with open(LISTENER_PATH, "w") as f:
        f.write(LISTENER_SRC)

    try:
        vanilla = run_vanilla()
        isolated = run_isolated()
    finally:
        try:
            os.remove(LISTENER_PATH)
        except OSError:
            pass

    yn = lambda b: "yes" if b else "no"
    print("\n=== Host process-isolation test ===\n")
    print(f"{'case':<10}{'h1 sees own':<13}{'h2 sees h1':<12}{'h2 sees orch':<14}{'h2 sees conn':<12}")
    for r in (vanilla, isolated):
        print(f"{r['name']:<10}{yn(r['h1_sees_own']):<13}{yn(r['h2_sees_h1']):<12}"
              f"{yn(r['h2_sees_orch']):<14}{yn(r['h2_sees_conn']):<12}")

    # The test is meaningful only if the vanilla case actually reproduces the leak.
    if not (vanilla["h2_sees_h1"] and vanilla["h2_sees_orch"]):
        print("\nINCONCLUSIVE: the vanilla case did not reproduce the process/orchestrator "
              "leak, so the test cannot confirm the fix. Check the environment.")
        return 2

    ok = (isolated["h1_sees_own"]           # host still sees its own processes
          and not isolated["h2_sees_h1"]     # neighbour can't see them
          and not isolated["h2_sees_orch"]   # neither can it see the orchestrator
          and isolated["h2_sees_conn"])      # network-level signal preserved
    print("\n" + ("PASS: isolated host hides its processes and the orchestrator from "
                  "neighbours while preserving the network-level signal." if ok else
                  "FAIL: isolation did not behave as expected (see table above)."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
