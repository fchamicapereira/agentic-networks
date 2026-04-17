import csv

from dataclasses import dataclass
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


@dataclass
class Interface:
    iface: str
    ip: str
    peer: str
    peer_ip: str


class Network:
    """Network topology and (optionally) a live Mininet emulation.

    Constructing a Network builds the topology data from links — interface names,
    IP assignments, peer relationships — without starting any emulation.
    Call start_network() to get a Network backed by a live Mininet instance.
    """

    def __init__(self, links: list[Link]):
        self.links = links
        self.net: Mininet | None = None
        self.hosts: dict[str, Host | None] = {}
        self.ifaces_per_host: dict[str, list[Interface]] = {}

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
                self.ifaces_per_host[node].append(Interface(
                    iface=f"{node}-eth{counters[node]}",
                    ip=ip,
                    peer=peer,
                    peer_ip=peer_ip,
                ))
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
        net: Mininet = Mininet(link=TCLink)
        hosts: dict[str, Host | None] = {name: net.addHost(name, ip=None) for name in self.hosts}

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
            # Remove all routes from the main table; agents must rebuild from scratch
            host.cmd("ip route flush table main")

        self.net = net
        self.hosts = hosts

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
