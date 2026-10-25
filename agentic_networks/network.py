import csv
import subprocess
import sys
import time

from collections import deque
from dataclasses import dataclass
from typing import cast
from pathlib import Path
from prettytable import PrettyTable

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import Host

from . import paths

# The orchestrator's own files: the repository checkout and, when running from a virtualenv,
# the directory holding it (in the Docker image, /app: a copy of the repository plus the
# environment). Isolated hosts stand for other organisations' machines, so these are hidden
# from them: an agent must not find the experiment's code, prompts or results on its disk.
_HIDDEN_FROM_HOSTS = sorted(
    {str(paths.PROJECT_ROOT)}
    | ({str(Path(sys.prefix).parent)} if sys.prefix != sys.base_prefix and Path(sys.prefix).parent != Path("/") else set())
)

# The environment of every process run on a host: agents' commands and the services and loads
# started there. Hosts must not inherit the orchestrator's environment, which holds the model
# providers' API keys and the experiment's own command line (SUDO_COMMAND); an agent reads it
# with `env` or from /proc/<pid>/environ.
HOST_ENV = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "TERM": "dumb",
}


@dataclass
class Link:
    node1: str
    node2: str
    delay_ms: int
    node1_ip: str
    node2_ip: str
    relationship: str = "peer/peer"  # "customer/provider", "provider/customer", or "peer/peer"


@dataclass
class Interface:
    iface: str
    ip: str
    peer: str
    peer_ip: str


@dataclass
class Topology:
    # Parsed topology: the point-to-point links plus an optional per-node loopback map
    # {node: "x.x.x.x/32"} from the file's `node` rows. Nodes absent from `loopbacks`
    # fall back to an auto-assigned 10.255.x.x/32 address in Network.
    links: list["Link"]
    loopbacks: dict[str, str]


class NetworkHost(Host):
    # Mininet Host whose processes run in a private PID and mount namespace (see below).

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        # Set by start_isolation(), which Network.start() calls for every host.
        self.anchor_pid: int | None = None
        self._anchor_outer: int | None = None

    def cmd(self, *args, **kwargs) -> str:
        result = super().cmd(*args, **kwargs)
        assert isinstance(result, str)
        return result

    # --- Per-host PID/mount-namespace isolation --------------------------------
    # Vanilla mininet hosts share the PID (and procfs) namespace, so any host's
    # `ps`/`/proc` sees every other host's processes and the experiment
    # orchestrator's command line. start_isolation() anchors a private PID+mount
    # namespace per host (sharing the host's network namespace); ns_cmd/ns_popen
    # then run commands inside it. Per-host anchors are siblings, so a host sees
    # only its own processes, while the network-level view (`ss`) is unchanged.
    # Each host also gets a private /tmp, so hosts cannot read each other's scratch
    # files (pid files and the like, which would e.g. name every node in the network),
    # and the orchestrator's files are hidden (see _HIDDEN_FROM_HOSTS). Commands start in /.
    #
    # mnexec's `-a` cannot re-enter a PID namespace, so execution on a host goes
    # through `nsenter` rather than host.popen.

    def start_isolation(self) -> None:
        # A long-lived `sleep` is the namespace's init; killing it later tears the
        # namespace down along with everything running in it. --fork makes the
        # sleep (not unshare) the process placed in the new PID namespace.
        hide = "".join(f" && mount -t tmpfs -o mode=755 tmpfs {d}" for d in _HIDDEN_FROM_HOSTS)
        # The init is PID 1 inside the namespace, so its environment is readable there
        # (/proc/1/environ): start it with HOST_ENV, not the Mininet shell's own environment.
        env = " ".join(f"{k}={v}" for k, v in HOST_ENV.items())
        outer = int(self.cmd(
            f"env -i {env} unshare --pid --mount --fork --mount-proc "
            f"sh -c 'mount -t tmpfs -o mode=1777 tmpfs /tmp{hide} && exec sleep infinity' "
            ">/dev/null 2>&1 & echo $!"
        ).strip().split()[-1])
        inner = outer
        for _ in range(100):
            try:
                children = open(f"/proc/{outer}/task/{outer}/children").read().split()
            except OSError:
                children = []
            if children:
                inner = int(children[0])
                break
            time.sleep(0.05)
        # The init execs sleep only once the private mounts are in place; wait for it, so
        # nothing runs in the namespace before /tmp is private and the hidden paths are hidden.
        for _ in range(100):
            try:
                if open(f"/proc/{inner}/comm").read().strip() == "sleep":
                    break
            except OSError:
                pass
            time.sleep(0.05)
        else:
            raise RuntimeError(f"{self.name}: isolation namespace did not come up (private mounts)")
        self._anchor_outer = outer
        self.anchor_pid = inner

    def stop_isolation(self) -> None:
        # Killing the namespace's init (inner) makes the kernel reap everything in
        # it; the outer unshare wrapper is cleaned up too.
        for pid in (self.anchor_pid, self._anchor_outer):
            if pid:
                subprocess.run(["kill", "-9", str(pid)], capture_output=True)
        self.anchor_pid = None
        self._anchor_outer = None

    def _nsenter_argv(self, command: str) -> list[str]:
        assert self.anchor_pid is not None
        return ["env", "-i", *(f"{k}={v}" for k, v in HOST_ENV.items()),
                "nsenter", "--target", str(self.anchor_pid),
                "--net", "--mount", "--pid", "--wd=/", "--", "bash", "-c", command]

    def ns_cmd(self, command: str) -> str:
        # Blocking command inside the host's isolation namespace (like host.cmd,
        # but in the private PID+mount namespace). Used to launch a host's own
        # inspectable workload (services, fault loads) so its agent can see them.
        result = subprocess.run(self._nsenter_argv(command), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        return result.stdout

    def ns_write(self, path: str, data: str | bytes, mode: int = 0o644) -> None:
        # Write a file as seen from inside the host's isolation namespace, e.g. into its
        # private /tmp or a private mount, where a write from outside would not land.
        if isinstance(data, str):
            data = data.encode()
        subprocess.run(self._nsenter_argv(f'mkdir -p "$(dirname {path})" && cat > {path} && chmod {mode:o} {path}'),
                       input=data, check=True)

    def ns_popen(self, command: str, **kwargs) -> subprocess.Popen:
        # Popen-compatible entry point for agent command execution inside the
        # isolation namespace (see MininetHost.exec).
        return subprocess.Popen(self._nsenter_argv(command), **kwargs)


class Network:
    # Network topology and (optionally) a live Mininet emulation.
    #
    # Constructing a Network builds the topology data from links — interface names,
    # IP assignments, peer relationships — without starting any emulation.
    # Call start_network() to get a Network backed by a live Mininet instance.

    def __init__(self, topology: "Topology | list[Link]"):
        # Accept either a parsed Topology (with explicit loopbacks) or a bare list of links
        # (loopbacks auto-assigned), so callers that only have links keep working.
        if isinstance(topology, Topology):
            links = topology.links
            explicit_loopbacks = topology.loopbacks
        else:
            links = topology
            explicit_loopbacks = {}

        self.links = links
        self.net: Mininet | None = None
        self.hosts: dict[str, NetworkHost] = {}
        self.ifaces_per_host: dict[str, list[Interface]] = {}

        counters: dict[str, int] = {}
        for link in links:
            for node, ip, peer, peer_ip in [
                (link.node1, link.node1_ip, link.node2, link.node2_ip),
                (link.node2, link.node2_ip, link.node1, link.node1_ip),
            ]:
                if node not in self.ifaces_per_host:
                    self.ifaces_per_host[node] = []
                    counters[node] = 0
                self.ifaces_per_host[node].append(
                    Interface(
                        iface=f"{node}-eth{counters[node]}",
                        ip=ip,
                        peer=peer,
                        peer_ip=peer_ip,
                    )
                )
                counters[node] += 1

        # Use the loopback declared in the topology when present, else auto-assign a private one.
        self.loopback_per_host: dict[str, str] = {
            node: explicit_loopbacks.get(node, f"10.255.{i}.1/32")
            for i, node in enumerate(sorted(self.ifaces_per_host.keys()), 1)
        }

    def _discover_loopbacks(self) -> dict[str, str]:
        # Return {node: ip} for each host's last non-127 address on lo.
        #
        # The last address is used so that when an agent adds a semantic loopback
        # (e.g. 45.32.0.1/32) after the pre-configured infrastructure address
        # (10.255.X.1/32), the semantic address is returned — which is what the
        # agent actually advertises to peers and what peers route to.
        # For routing.txt experiments where only one loopback is configured,
        # first == last, so there is no regression.
        result = {}
        for name, host in self.hosts.items():
            out = host.cmd("ip -4 addr show lo")
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("inet ") and not line.startswith("inet 127."):
                    result[name] = line.split()[1].split("/")[0]
        return result

    def test_all_connectivity(self, label: str = "Final Connectivity Matrix") -> str:
        loopbacks = self._discover_loopbacks()
        self.loopback_per_host = {name: f"{ip}/32" for name, ip in loopbacks.items()}

        dst_hosts = sorted(self.hosts.keys())
        table = PrettyTable()
        table.field_names = ["src \\ dst"] + dst_hosts

        for src_hostname, src_host in sorted(self.hosts.items()):
            row = [src_hostname]
            src_ip = loopbacks.get(src_hostname)
            for dst_hostname in dst_hosts:
                if src_hostname == dst_hostname:
                    row.append("--")
                elif src_ip is None or dst_hostname not in loopbacks:
                    row.append("N/A")
                else:
                    dst_ip = loopbacks[dst_hostname]
                    out = src_host.cmd(f"ping -c 1 -W 1 -I {src_ip} {dst_ip}")
                    assert isinstance(out, str), f"Expected string output, got {type(out)}"
                    reachable = "1 received" in out or "1 packets received" in out
                    row.append("OK" if reachable else "FAIL")
            table.add_row(row)

        print(f"\n=== {label} ===")
        print(table)
        print()

        return table.get_string()

    def start(self) -> None:
        # Start a live Mininet emulation for this network topology.
        #
        # Populates self.net and self.hosts with real Mininet objects.
        # Call self.stop() when done.
        #
        # Every host gets a private PID+mount namespace, so an agent's `ps`/`/proc`
        # sees only its own host's processes, not other hosts' or the orchestrator's
        # (see NetworkHost.start_isolation).
        self.net = Mininet(link=TCLink, host=NetworkHost)
        self.hosts = {name: cast(NetworkHost, self.net.addHost(name, ip=None)) for name in self.ifaces_per_host}

        for link in self.links:
            # netem's default queue limit is 1000 packets; at high rates on high-delay
            # links this causes drops. Size it to hold ~2x the in-flight packets at 1 Gbps.
            queue_size = max(1000, link.delay_ms * 200)
            self.net.addLink(self.hosts[link.node1], self.hosts[link.node2], delay=f"{link.delay_ms}ms", max_queue_size=queue_size)

        self.net.start()

        for node, ifaces in self.ifaces_per_host.items():
            host = self.hosts[node]
            host.cmd("ip link set lo up")
            host.cmd(f"ip addr add {self.loopback_per_host[node]} dev lo 2>/dev/null || true")
            for iface in ifaces:
                host.cmd(f"ip addr add {iface.ip} dev {iface.iface}")
                host.cmd(f"ip link set {iface.iface} up")

        # After interfaces exist, anchor each host's private PID+mount namespace
        # (it inherits the fully-configured network namespace).
        for host in self.hosts.values():
            host.start_isolation()

    def clear_routing_tables(self, keep_connected: bool = True) -> None:
        # Flush routes on every node so agents must establish reachability themselves.
        #
        # By default only `scope global` routes (remote/gateway routes and any default) are
        # removed, leaving the kernel's `scope link` directly-connected /30 routes intact — those
        # are L2 plumbing trivially derivable from each interface's own address, not a routing
        # decision, so wiping them only tests `ip route` fluency rather than routing policy. Set
        # keep_connected=False to flush the entire main table (full network bring-up).
        scope = "scope global " if keep_connected else ""
        for host in self.hosts.values():
            host.cmd(f"ip route flush table main {scope}".rstrip())

    def seed_stable_routes(self) -> None:
        # Install an arbitrary but stable routing solution so every node can reach every other
        # node's loopback from the start, giving agents a converged baseline instead of a clean
        # slate. Routes follow a single spanning tree and deliberately ignore link delays — the
        # result is fully connected but NOT optimal, leaving room for agents to improve it.
        nodes = sorted(self.ifaces_per_host.keys())

        # Intermediate nodes must forward transit traffic.
        for node in nodes:
            self.hosts[node].cmd("sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1")

        adj: dict[str, list[str]] = {n: [] for n in nodes}
        for link in self.links:
            adj[link.node1].append(link.node2)
            adj[link.node2].append(link.node1)

        # One spanning tree (BFS from the first node), ignoring delays.
        root = nodes[0]
        tree: dict[str, list[str]] = {n: [] for n in nodes}
        seen = {root}
        queue = deque([root])
        while queue:
            u = queue.popleft()
            for v in sorted(adj[u]):
                if v not in seen:
                    seen.add(v)
                    tree[u].append(v)
                    tree[v].append(u)
                    queue.append(v)

        # For each destination, a node's next hop is its tree-neighbour toward that destination
        # (its parent in the destination-rooted tree). Install a /32 route to the loopback via that
        # neighbour's directly-connected interface IP.
        for dst in nodes:
            next_hop: dict[str, str] = {}
            seen2 = {dst}
            queue = deque([dst])
            while queue:
                u = queue.popleft()
                for v in tree[u]:
                    if v not in seen2:
                        seen2.add(v)
                        next_hop[v] = u
                        queue.append(v)
            dst_loopback = self.loopback_per_host[dst]
            for node in nodes:
                if node == dst:
                    continue
                hop = next_hop[node]
                iface = next(i for i in self.ifaces_per_host[node] if i.peer == hop)
                via = iface.peer_ip.split("/")[0]
                self.hosts[node].cmd(f"ip route add {dst_loopback} via {via} dev {iface.iface} 2>/dev/null || true")

    def stop(self) -> None:
        # Stop the live Mininet emulation.
        assert self.net is not None, "stop() called on a network that was never started"
        # Tear down per-host isolation namespaces first; killing each anchor reaps
        # everything running inside it (services, fault loads).
        for host in self.hosts.values():
            if host.anchor_pid is not None:
                host.stop_isolation()
        self.net.stop()

    def print(self):
        nodes = set(link.node1 for link in self.links) | set(link.node2 for link in self.links)

        print("\n=== Network Topology ===")
        print(f"Nodes : {', '.join(nodes)}")
        print("Links (full mesh, both directions):")
        for link in self.links:
            print(f"  {link.node1} {link.node1_ip:<16}  <──[{link.delay_ms:>2}ms]──>  {link.node2} {link.node2_ip:<16}")
        print()


def load_topology(path: str | Path) -> Topology:
    # Two kinds of rows:
    #   node,<name>,<loopback>            — per-node loopback address (advertised node identity)
    #   <h1>,<h2>,<delay_ms>,<ip1>,<ip2>[,<relationship>]  — a point-to-point link
    # `node` rows are optional; nodes without one get an auto-assigned loopback in Network.
    links: list[Link] = []
    loopbacks: dict[str, str] = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].lstrip().startswith("#"):
                continue
            cols = [c.strip() for c in row]
            if cols[0] == "node":
                name, loopback = cols[1], cols[2]
                if "/" not in loopback:
                    loopback += "/32"
                loopbacks[name] = loopback
                continue
            host1, host2, delay_ms, host1_ip, host2_ip = cols[:5]
            relationship = cols[5] if len(cols) > 5 else "peer/peer"
            links.append(Link(host1, host2, int(delay_ms), host1_ip, host2_ip, relationship))
    return Topology(links=links, loopbacks=loopbacks)
