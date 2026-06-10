import logging
import time
from pathlib import Path

from .network import Network


logger = logging.getLogger("Traffic Generator")

_SCRIPTS_DIR = Path(__file__).parent

# UDP port used by the sink and source scripts
_UDP_PORT = 9999


class TrafficGenerator:
    """Manages background UDP flows for billing experiments.

    Uses a simple Python-based UDP source/sink instead of iperf3 to avoid
    iperf3's control-channel handshake issues in high-latency Mininet setups.

    Starts a UDP sink on every node and a single long-running UDP source
    from `source` to `dest_ip`. Supports spike/restore to simulate traffic bursts.
    """

    def __init__(
        self,
        network: Network,
        source: str,
        dest_ip: str,
        baseline_mbps: float,
        spike_mbps: float,
    ):
        self.network = network
        self.source = source
        self.dest_ip = dest_ip
        self.baseline_mbps = baseline_mbps
        self.spike_mbps = spike_mbps
        self._current_mbps: float = baseline_mbps

    def start_servers(self) -> None:
        """Start UDP sinks on all nodes.

        Kill existing sink processes once up front — pkill in Mininet's shared
        PID namespace kills across all hosts, so per-iteration kills would
        cascade-kill each sink we just started.
        """
        sink = str(_SCRIPTS_DIR / "udp_sink.py")
        first_host = next(iter(self.network.hosts.values()))
        first_host.cmd("pkill -f 'udp_sink.py' 2>/dev/null; true")
        for name, host in self.network.hosts.items():
            host.cmd(f"python3 {sink} {_UDP_PORT} > /tmp/udp-sink-{name}.log 2>&1 &")
            logger.debug("UDP sink started on %s", name)
        logger.info("UDP sinks started on all nodes (port %d)", _UDP_PORT)

    def start_flow(self) -> None:
        """Start background UDP flow at baseline rate."""
        self._launch(self.baseline_mbps)

    def spike(self) -> None:
        """Increase flow to spike_mbps."""
        logger.info("Traffic spike: %.0f → %.0f Mbps", self._current_mbps, self.spike_mbps)
        self._launch(self.spike_mbps)
        time.sleep(1)

    def restore(self) -> None:
        """Restore flow to baseline_mbps."""
        logger.info("Traffic restore: %.0f → %.0f Mbps", self._current_mbps, self.baseline_mbps)
        self._launch(self.baseline_mbps)
        time.sleep(1)

    def _launch(self, mbps: float) -> None:
        self._current_mbps = mbps
        source = str(_SCRIPTS_DIR / "udp_source.py")
        src = self.network.hosts[self.source]
        src.cmd("pkill -f 'udp_source.py' 2>/dev/null; true")
        src.cmd(
            f"python3 {source} {self.dest_ip} {_UDP_PORT} {mbps:.0f}"
            f" > /tmp/udp-source.log 2>&1 &"
        )
        logger.info("UDP flow: %s → %s at %.0f Mbps", self.source, self.dest_ip, mbps)

    @property
    def current_mbps(self) -> float:
        return self._current_mbps

    def stop(self) -> None:
        """Kill all UDP sink/source processes on all nodes."""
        first_host = next(iter(self.network.hosts.values()))
        first_host.cmd("pkill -f 'udp_sink.py' 2>/dev/null; true")
        first_host.cmd("pkill -f 'udp_source.py' 2>/dev/null; true")
        logger.info("All UDP traffic processes stopped")
