import csv
import ipaddress

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple
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


class RoutingRule(NamedTuple):
    source_host: str
    destination_host: str
    next_hop: str


@dataclass
class Network:
    net: Mininet
    hosts: dict[str, Host]
    ifaces_per_host: dict[str, list[Interface]]
    links: list[Link]

    def get_routing_rules(self, route_tables: dict[str, str]) -> list[RoutingRule]:
        """Parse pre-collected routing tables and correlate with topology info.

        Returns one RoutingRule(source_host, destination_host, next_hop) per
        reachable (src, dst) pair, where next_hop is the immediate neighbour
        src uses to reach dst.
        """
        ip_to_node: dict[str, str] = {}
        node_subnets: dict[str, set[str]] = {name: set() for name in self.hosts}

        for node_name, ifaces in self.ifaces_per_host.items():
            for iface in ifaces:
                ip_to_node[iface.ip.split("/")[0]] = node_name
                node_subnets[node_name].add(str(ipaddress.ip_interface(iface.ip).network))

        rules: list[RoutingRule] = []

        for src_name in self.hosts:
            raw = route_tables.get(src_name, "").strip()
            if not raw:
                continue

            subnet_to_next_hop: dict[str, str] = {}
            for line in raw.splitlines():
                parts = line.split()
                if not parts:
                    continue
                try:
                    subnet = str(ipaddress.ip_network(parts[0], strict=False))
                except ValueError:
                    continue

                next_hop_node = None
                if "via" in parts:
                    next_hop_node = ip_to_node.get(parts[parts.index("via") + 1])
                elif "dev" in parts:
                    dev = parts[parts.index("dev") + 1]
                    for iface in self.ifaces_per_host[src_name]:
                        if iface.iface == dev:
                            next_hop_node = ip_to_node.get(iface.peer_ip.split("/")[0])
                            break

                if next_hop_node:
                    subnet_to_next_hop[subnet] = next_hop_node

            for dst_name in self.hosts:
                if dst_name == src_name:
                    continue
                for subnet in node_subnets[dst_name]:
                    if subnet in subnet_to_next_hop:
                        rules.append(RoutingRule(src_name, dst_name, subnet_to_next_hop[subnet]))
                        break

        return rules

    def test_all_connectivity(self) -> str:
        # For each destination host, try to reach it via any of its IPs
        dst_hosts = sorted(self.hosts.keys())

        table = PrettyTable()
        table.field_names = ["src \\ dst"] + dst_hosts

        for src_hostname, src_host in sorted(self.hosts.items()):
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


def build_network(links: list[Link]) -> Network:
    nodes = set(link.node1 for link in links) | set(link.node2 for link in links)

    net: Mininet = Mininet(link=TCLink)
    hosts: dict[str, Host] = {name: net.addHost(name, ip=None) for name in nodes}
    ifaces_per_host: dict[str, list[Interface]] = {name: [] for name in nodes}

    for link in links:
        net.addLink(hosts[link.node1], hosts[link.node2], delay=f"{link.delay_ms}ms")

        eth1 = f"{link.node1}-eth{len(ifaces_per_host[link.node1])}"
        eth2 = f"{link.node2}-eth{len(ifaces_per_host[link.node2])}"

        ifaces_per_host[link.node1].append(
            Interface(
                iface=eth1,
                ip=link.node1_ip,
                peer=link.node2,
                peer_ip=link.node2_ip,
            )
        )
        ifaces_per_host[link.node2].append(
            Interface(
                iface=eth2,
                ip=link.node2_ip,
                peer=link.node1,
                peer_ip=link.node1_ip,
            )
        )

    net.start()

    for node, ifaces in ifaces_per_host.items():
        host = hosts[node]

        host.cmd("ip link set lo up")

        for iface in ifaces:
            host.cmd(f"ip addr add {iface.ip} dev {iface.iface}")
            host.cmd(f"ip link set {iface.iface} up")

        # Remove all routes from the main table; agents must rebuild from scratch
        host.cmd("ip route flush table main")

    return Network(net=net, hosts=hosts, ifaces_per_host=ifaces_per_host, links=links)
