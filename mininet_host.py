from typing import Optional

import logging


class MininetHost:
    """A wrapper around a Mininet host that allows an LLM to interact with it via tools and messaging."""

    def __init__(
        self,
        node_name: str,
        mininet_host_cmd,
    ):
        self.node_name = node_name
        self.mininet_host_cmd = mininet_host_cmd
        self.log = logging.getLogger(f"agent.{node_name}")

    def execute_command(self, cmd: str) -> str:
        self.log.info("Executing command: %s", cmd)
        result = self.mininet_host_cmd(cmd).strip()
        if result:
            self.log.info("Command output:\n%s", result)
        return result

    def get_network_info(self) -> str:
        addrs = self.execute_command("ip addr show")
        routes = self.execute_command("ip route show")
        routes = routes if routes else "(empty)"
        return f"=== Interfaces ===\n{addrs}\n\n=== Routes ===\n{routes}"

    def add_route(self, destination: str, dev: str, via: Optional[str] = None) -> str:
        if via:
            cmd = f"ip route add {destination} via {via} dev {dev}"
        else:
            cmd = f"ip route add {destination} dev {dev} scope link"
        result = self.execute_command(cmd)
        return result if result else f"Route added: {destination}"

    def delete_route(self, destination: str) -> str:
        result = self.execute_command(f"ip route del {destination}")
        return result if result else f"Route deleted: {destination}"

    def ping(self, target_ip: str, count: int = 3) -> str:
        return self.execute_command(f"ping -c {count} -W 2 {target_ip}")
