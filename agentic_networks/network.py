import csv
import shutil
import tempfile
import time

from dataclasses import dataclass
from pathlib import Path
from prettytable import PrettyTable

from typing import cast

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


@dataclass
class Interface:
    iface: str
    ip: str
    peer: str
    peer_ip: str


class NetworkHost(Host):
    """Mininet Host extended with FRR daemon control."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        # Kill any lingering FRR processes and remove stale pid/socket files
        # from a previous run that may not have shut down cleanly.
        self.cmd(f"pkill -f 'bgpd.*-N {self.name}'  2>/dev/null; true")
        self.cmd(f"pkill -f 'zebra.*-N {self.name}' 2>/dev/null; true")
        self.cmd(f"rm -rf /var/run/frr/{self.name}")
        self.cmd(f"mkdir -p /var/run/frr/{self.name}")
        self.cmd(f"chown frr:frr /var/run/frr/{self.name}")

    def cmd(self, *args, **kwargs) -> str:
        result = super().cmd(*args, **kwargs)
        assert isinstance(result, str)
        return result

    def zebra(self, config_file: Path) -> str:
        return self.cmd(
            f"/usr/lib/frr/zebra -d -N {self.name} -f {config_file} 2>&1"
        )

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
    """Network topology and (optionally) a live Mininet emulation.

    Constructing a Network builds the topology data from links — interface names,
    IP assignments, peer relationships — without starting any emulation.
    Call start_network() to get a Network backed by a live Mininet instance.
    """

    def __init__(self, links: list[Link]):
        self.links = links
        self.net: Mininet | None = None
        self.hosts: dict[str, NetworkHost | None] = {}
        self.ifaces_per_host: dict[str, list[Interface]] = {}
        self._bgp_dirs: dict[str, Path] = {}

        counters: dict[str, int] = {}
        for link in links:
            for node, ip, peer, peer_ip in [
                (link.node1, link.node1_ip, link.node2, link.node2_ip),
                (link.node2, link.node2_ip, link.node1, link.node1_ip),
            ]:
                if node not in self.hosts:
                    self.hosts[node] = None
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

    def test_all_connectivity(self) -> str:
        # For each destination host, try to reach it via any of its IPs
        dst_hosts = sorted(self.hosts.keys())

        table = PrettyTable()
        table.field_names = ["src \\ dst"] + dst_hosts

        for src_hostname, src_host in sorted(self.hosts.items()):
            assert src_host is not None, "test_all_connectivity requires a live Mininet network"
            row = [src_hostname]
            for dst_hostname in dst_hosts:
                if src_hostname == dst_hostname:
                    row.append("--")
                else:
                    reachable = False
                    for iface in self.ifaces_per_host[dst_hostname]:
                        ip = iface.ip.split("/")[0]
                        out = src_host.cmd(f"ping -c 1 -W 1 {ip}")
                        assert isinstance(out, str), f"Expected string output, got {type(out)}"
                        if "1 received" in out or "1 packets received" in out:
                            reachable = True
                            break
                    row.append("OK" if reachable else "FAIL")
            table.add_row(row)

        print("\n=== Final Connectivity Matrix ===")
        print(table)
        print()

        return table.get_string()

    def start(self) -> None:
        """Start a live Mininet emulation for this network topology.

        Populates self.net and self.hosts with real Mininet objects.
        Call self.net.stop() when done.
        """
        net: Mininet = Mininet(link=TCLink, host=NetworkHost)
        hosts: dict[str, NetworkHost | None] = {
            name: cast(NetworkHost, net.addHost(name, ip=None)) for name in self.hosts
        }

        for link in self.links:
            net.addLink(hosts[link.node1], hosts[link.node2], delay=f"{link.delay_ms}ms")

        net.start()

        for node, ifaces in self.ifaces_per_host.items():
            host = hosts[node]
            assert host is not None
            host.cmd("ip link set lo up")
            for iface in ifaces:
                host.cmd(f"ip addr add {iface.ip} dev {iface.iface}")
                host.cmd(f"ip link set {iface.iface} up")

        self.net = net
        self.hosts = hosts

    def clear_routing_tables(self) -> None:
        """Flush the main routing table on every node."""
        for host in self.hosts.values():
            assert host is not None
            host.cmd("ip route flush table main")

    def start_bgp(self, policy: str | None = None) -> dict[str, int]:
        """Start FRR eBGP on all nodes. Each node gets its own private ASN.

        Returns the ASN map {node_name: asn}.
        """
        asn_map = {node: 65000 + i for i, node in enumerate(sorted(self.hosts.keys()), 1)}

        for node, host in self.hosts.items():
            assert host is not None
            host.cmd("sysctl -w net.ipv4.ip_forward=1")

        for node, host in self.hosts.items():
            assert host is not None
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
            lines += [
                " !",
                " address-family ipv4 unicast",
                "  redistribute connected",
                " exit-address-family",
                "!",
            ]
            if policy:
                lines.append(self._render_policy(policy, node, asn))

            (config_dir / "frr.conf").write_text("\n".join(lines) + "\n")

            out = host.zebra(config_dir / "frr.conf")
            if out.strip():
                print(f"  [{node}] zebra: {out.strip()}")
            if "exiting" in out or "failed to start" in out:
                raise RuntimeError(f"zebra failed to start on node {node}")

        # Let all zebra instances initialise before bgpd tries to connect to them.
        time.sleep(1)

        for node, host in self.hosts.items():
            assert host is not None
            host.bgpd(self._bgp_dirs[node] / "frr.conf")

        self._wait_bgp_convergence()
        return asn_map

    def _render_policy(self, policy: str, node: str, asn: int) -> str:
        """Substitute template variables in a policy snippet for a specific node."""
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

        return (
            policy
            .replace("__ASN__", str(asn))
            .replace("__NODE__", node)
            .replace("__ROUTER_ID__", router_id)
            .replace("__NEIGHBOR_WEIGHTS__", "\n".join(weight_lines))
        )

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
                assert host is not None
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
                assert host is not None
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

        self._convergence_failure(last_summaries, timeout)

    def _convergence_failure(self, last_summaries: dict[str, str], timeout: int) -> None:
        first_host = next(iter(self.hosts.values()))
        assert first_host is not None
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
        """Stop FRR daemons and clean up per-node config dirs."""
        for node, host in self.hosts.items():
            assert host is not None
            host.stop_frr()
            if node in self._bgp_dirs:
                shutil.rmtree(self._bgp_dirs[node], ignore_errors=True)
        self._bgp_dirs.clear()

    def stop(self) -> None:
        """Stop the live Mininet emulation."""
        assert self.net is not None, "stop() called on a network that was never started"
        self.net.stop()

    def print(self):
        nodes = set(link.node1 for link in self.links) | set(link.node2 for link in self.links)

        print("\n=== Network Topology ===")
        print(f"Nodes : {', '.join(nodes)}")
        print("Links (full mesh, both directions):")
        for link in self.links:
            print(f"  {link.node1} {link.node1_ip:<16}  <──[{link.delay_ms:>2}ms]──>  {link.node2} {link.node2_ip:<16}")
        print()


def load_topology(path: str | Path) -> list[Link]:
    links: list[Link] = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].lstrip().startswith("#"):
                continue
            host1, host2, delay_ms, host1_ip, host2_ip = [c.strip() for c in row]
            links.append(Link(host1, host2, int(delay_ms), host1_ip, host2_ip))
    return links
