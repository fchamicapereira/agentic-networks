import csv
import shutil
import subprocess
import tempfile
import time

from collections import deque
from dataclasses import dataclass
from typing import cast
from pathlib import Path
from prettytable import PrettyTable

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import Host


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
    # Mininet Host extended with FRR daemon control.

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        # Kill any lingering FRR processes and remove stale pid/socket files
        # from a previous run that may not have shut down cleanly.
        self.cmd(f"pkill -f 'bgpd.*-N {self.name}'  2>/dev/null; true")
        self.cmd(f"pkill -f 'zebra.*-N {self.name}' 2>/dev/null; true")
        self.cmd(f"rm -rf /var/run/frr/{self.name}")
        self.cmd(f"mkdir -p /var/run/frr/{self.name}")
        self.cmd(f"chown frr:frr /var/run/frr/{self.name}")
        # Populated by start_isolation(); when set, this host runs its commands in
        # a private PID+mount namespace (see below).
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
    #
    # mnexec's `-a` cannot re-enter a PID namespace, so isolated execution goes
    # through `nsenter` rather than host.popen. This is opt-in (Network.start
    # isolate_hosts=True); experiments that rely on FRR unix sockets keep the
    # default shared-namespace behaviour.

    def start_isolation(self) -> None:
        # A long-lived `sleep` is the namespace's init; killing it later tears the
        # namespace down along with everything running in it. --fork makes the
        # sleep (not unshare) the process placed in the new PID namespace.
        outer = int(self.cmd(
            "unshare --pid --mount --fork --mount-proc sleep infinity "
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
        return ["nsenter", "--target", str(self.anchor_pid),
                "--net", "--mount", "--pid", "--", "bash", "-c", command]

    def ns_cmd(self, command: str) -> str:
        # Blocking command inside the host's isolation namespace (like host.cmd,
        # but in the private PID+mount namespace). Used to launch a host's own
        # inspectable workload (services, fault loads) so its agent can see them.
        result = subprocess.run(self._nsenter_argv(command), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        return result.stdout

    def ns_popen(self, command: str, **kwargs) -> subprocess.Popen:
        # Popen-compatible entry point for agent command execution inside the
        # isolation namespace (see MininetHost.exec).
        return subprocess.Popen(self._nsenter_argv(command), **kwargs)

    def zebra(self, config_file: Path) -> str:
        return self.cmd(f"/usr/lib/frr/zebra -d -N {self.name} -f {config_file} 2>&1")

    def bgpd(self, config_file: Path) -> None:
        log_file = config_file.parent / "bgpd.out"
        self.cmd(f"nohup /usr/lib/frr/bgpd -N {self.name} -f {config_file} > {log_file} 2>&1 &")

    def bgp_summary(self) -> str:
        return self.cmd(f"vtysh -N {self.name} -c 'show bgp summary'")

    def stop_frr(self) -> None:
        self.cmd(f"pkill -f 'bgpd.*-N {self.name}'  2>/dev/null; true")
        self.cmd(f"pkill -f 'zebra.*-N {self.name}' 2>/dev/null; true")
        self.cmd(f"rm -rf /var/run/frr/{self.name}")


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
        self._bgp_dirs: dict[str, Path] = {}

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

    def start(self, isolate_hosts: bool = False) -> None:
        # Start a live Mininet emulation for this network topology.
        #
        # Populates self.net and self.hosts with real Mininet objects.
        # Call self.stop() when done.
        #
        # isolate_hosts=True gives each host a private PID+mount namespace so an
        # agent's `ps`/`/proc` sees only its own host's processes, not other
        # hosts' or the orchestrator's (see NetworkHost.start_isolation). Opt-in
        # because it routes agent execution through nsenter and gives each host a
        # private mount namespace, which experiments relying on FRR unix sockets
        # do not need.
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

        if isolate_hosts:
            # After interfaces/routes exist, anchor each host's private PID+mount
            # namespace (it inherits the fully-configured network namespace).
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

    def start_bgp(self, policies: dict[str, str] | None = None) -> dict[str, int]:
        # Start FRR eBGP on all nodes. Each node gets its own private ASN.
        #
        # policies: optional per-node FRR config snippets {node_name: frr_text}.
        # Returns the ASN map {node_name: asn}.
        asn_map = {node: 65000 + i for i, node in enumerate(sorted(self.hosts.keys()), 1)}

        for node, host in self.hosts.items():
            host.cmd("sysctl -w net.ipv4.ip_forward=1")
            host.cmd(f"ip addr add {self.loopback_per_host[node]} dev lo 2>/dev/null || true")

        for node, host in self.hosts.items():
            asn = asn_map[node]
            ifaces = self.ifaces_per_host[node]
            router_id = ifaces[0].ip.split("/")[0]

            config_dir = Path(tempfile.mkdtemp(prefix=f"frr-{node}-"))
            config_dir.chmod(0o755)
            self._bgp_dirs[node] = config_dir

            lines = [
                "frr version 8.0",
                "frr defaults traditional",
                f"hostname {node}",
                "log syslog informational",
                "no ipv6 forwarding",
                "!",
                f"router bgp {asn}",
                f" bgp router-id {router_id}",
                " bgp log-neighbor-changes",
                " no bgp ebgp-requires-policy",
            ]
            for iface in ifaces:
                peer_ip = iface.peer_ip.split("/")[0]
                peer_asn = asn_map[iface.peer]
                lines += [
                    f" neighbor {peer_ip} remote-as {peer_asn}",
                    f" neighbor {peer_ip} timers 1 3",
                ]
            loopback_ip = self.loopback_per_host[node]
            lines += [
                " !",
                " address-family ipv4 unicast",
                f"  network {loopback_ip}",
                " exit-address-family",
                "!",
            ]
            node_policy = policies.get(node) if policies else None
            if node_policy:
                lines.append(self._render_policy(node_policy, node, asn))

            (config_dir / "frr.conf").write_text("\n".join(lines) + "\n")

            out = host.zebra(config_dir / "frr.conf")
            if out.strip():
                print(f"  [{node}] zebra: {out.strip()}")
            if "exiting" in out or "failed to start" in out:
                raise RuntimeError(f"zebra failed to start on node {node}")

        # Let all zebra instances initialise before bgpd tries to connect to them.
        time.sleep(1)

        for node, host in self.hosts.items():
            host.bgpd(self._bgp_dirs[node] / "frr.conf")

        self._wait_bgp_convergence()
        return asn_map

    def _render_policy(self, policy: str, node: str, asn: int) -> str:
        # Substitute template variables in a policy snippet for a specific node.
        ifaces = self.ifaces_per_host[node]
        router_id = ifaces[0].ip.split("/")[0]

        weight_lines: list[str] = []
        for iface in ifaces:
            peer_ip = iface.peer_ip.split("/")[0]
            for link in self.links:
                if {link.node1, link.node2} == {node, iface.peer}:
                    weight = max(1, round(1000 / link.delay_ms))
                    weight_lines.append(f" neighbor {peer_ip} weight {weight}")
                    break

        return policy.replace("__ASN__", str(asn)).replace("__NODE__", node).replace("__ROUTER_ID__", router_id).replace("__NEIGHBOR_WEIGHTS__", "\n".join(weight_lines))

    def _wait_bgp_convergence(self, timeout: int = 60) -> None:
        # Phase 1: wait for all BGP sessions to reach Established.
        # "BGP router identifier" only appears in real bgpd output; bad_tokens
        # cover every non-Established session state.
        bad_tokens = {"never", "Active", "Idle", "Connect", "OpenSent", "OpenConfirm"}
        last_summaries: dict[str, str] = {}
        deadline = time.time() + timeout
        sessions_up = False
        while time.time() < deadline:
            all_up = True
            for node, host in self.hosts.items():
                out = host.bgp_summary()
                last_summaries[node] = out
                if "BGP router identifier" not in out or any(token in out for token in bad_tokens):
                    all_up = False
                    break
            if all_up:
                sessions_up = True
                break
            time.sleep(1)

        if not sessions_up:
            self._convergence_failure(last_summaries, timeout)

        # Phase 2: wait for route counts to stabilise.  BGP sessions being
        # Established does not mean all UPDATE messages have been processed —
        # high-latency inter-cluster links deliver updates later.  Poll until
        # every node's route count is the same for two consecutive checks.
        prev_counts: dict[str, int] = {}
        stable_rounds = 0
        while time.time() < deadline:
            counts: dict[str, int] = {}
            for node, host in self.hosts.items():
                routes = host.cmd("ip route show proto bgp")
                counts[node] = len(routes.strip().splitlines()) if routes.strip() else 0
            if counts == prev_counts:
                stable_rounds += 1
                if stable_rounds >= 3:
                    return
            else:
                stable_rounds = 0
            prev_counts = counts
            time.sleep(1)

        # Timed out waiting for route stability — return anyway (sessions are up).
        return

    def _convergence_failure(self, last_summaries: dict[str, str], timeout: int) -> None:
        first_host = next(iter(self.hosts.values()))
        ps_out = first_host.cmd("ps aux | grep bgpd | grep -v grep")
        syslog_out = first_host.cmd("grep -i 'bgpd\\|frr\\|zebra' /var/log/syslog 2>/dev/null | tail -40")
        print("\n=== BGP convergence diagnostics ===")
        print(f"\n-- bgpd processes --\n{ps_out or '(none)'}")
        print(f"\n-- syslog (frr/bgpd/zebra, last 40 lines) --\n{syslog_out or '(nothing in syslog)'}")
        for node, summary in sorted(last_summaries.items()):
            print(f"\n-- [{node}] show bgp summary --\n{summary or '(no output)'}")
            run_dir = f"/var/run/frr/{node}"
            run_ls = first_host.cmd(f"ls -la {run_dir} 2>&1")
            print(f"\n-- [{node}] {run_dir} --\n{run_ls}")
        raise TimeoutError(f"BGP sessions did not reach Established within {timeout}s")

    def stop_bgp(self) -> None:
        # Stop FRR daemons and clean up per-node config dirs.
        for node, host in self.hosts.items():
            host.stop_frr()
            if node in self._bgp_dirs:
                shutil.rmtree(self._bgp_dirs[node], ignore_errors=True)
        self._bgp_dirs.clear()

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
