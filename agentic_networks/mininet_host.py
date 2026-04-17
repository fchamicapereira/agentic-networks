import logging
import subprocess

from mininet.node import Host


class MininetHost:
    """A wrapper around a Mininet host that allows an LLM to interact with it via tools and messaging."""

    def __init__(self, node_name: str, host: Host):
        self.node_name = node_name
        self.host = host
        self.log = logging.getLogger(f"agent.{node_name}")

    def exec(self, command: str) -> tuple[str, int]:
        self.log.info("Executing command: %s", command)
        proc = self.host.popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, _ = proc.communicate()
        output = (stdout.decode(errors="replace") if isinstance(stdout, bytes) else stdout).strip()
        exit_code = proc.returncode
        if output:
            self.log.info("Command output (exit %d):\n%s", exit_code, output)
        else:
            self.log.info("Command output (exit %d): (empty)", exit_code)
        return output or "(no output)", exit_code
