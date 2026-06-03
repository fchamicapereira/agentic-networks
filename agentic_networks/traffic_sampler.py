import logging
import subprocess
import time

from .billing_clock import BillingClock
from .network import Network


logger = logging.getLogger(__name__)


class TrafficSampler:
    """Samples per-provider throughput on a billing node using /proc/net/dev.

    Each call to sample() takes a fixed 1-second real-time measurement:
    reads byte counters, waits 1 second, reads again, and computes the rate
    over that window.  This gives a true point-in-time rate snapshot
    independent of when the previous sample was taken or how long LLM
    iterations take.

    The caller supplies an elapsed_days label so samples can be spaced at
    any desired virtual interval (e.g. every 15 simulated minutes).
    """

    MEASUREMENT_WINDOW_SECONDS = 0.2

    def __init__(
        self,
        network: Network,
        billing_node: str,
        monitored_prefixes: list[str],
        provider_ifaces: dict[str, str],
        billing_clock: BillingClock,

    ):
        """
        provider_ifaces: maps provider name to the output interface name on billing_node,
                         e.g. {"Expensive": "ISP-eth1", "Cheap": "ISP-eth2"}.
        monitored_prefixes: kept for output-format compatibility; all interface TX
                            bytes are attributed to the first (and typically only) prefix.
        """
        self.network = network
        self.billing_node = billing_node
        self.monitored_prefixes = monitored_prefixes
        self.provider_ifaces = provider_ifaces
        self.clock = billing_clock

        self._samples: list[dict] = []

    # ------------------------------------------------------------------
    # Counter reading via /proc/net/dev
    # ------------------------------------------------------------------

    def _cmd(self, command: str) -> str:
        host = self.network.hosts[self.billing_node]
        proc = host.popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stderr:
            out_err = stderr.decode(errors="replace") if isinstance(stderr, bytes) else (stderr or "")
            logger.debug("_cmd stderr: %s", out_err.strip())
        if not stdout:
            return ""
        return stdout.decode(errors="replace") if isinstance(stdout, bytes) else stdout

    def _read_tx_bytes(self) -> dict[str, int]:
        """Return {iface: cumulative_tx_bytes} from /proc/net/dev on the billing node."""
        out = self._cmd("cat /proc/net/dev")
        result: dict[str, int] = {}
        for line in out.splitlines():
            if ":" not in line:
                continue
            iface, rest = line.split(":", 1)
            iface = iface.strip()
            fields = rest.split()
            # /proc/net/dev columns after the colon:
            # RX: bytes(0) packets(1) errs(2) drop(3) fifo(4) frame(5) compressed(6) multicast(7)
            # TX: bytes(8) packets(9) errs(10) drop(11) fifo(12) colls(13) carrier(14) compressed(15)
            if len(fields) >= 9:
                try:
                    result[iface] = int(fields[8])
                except ValueError:
                    pass
        return result

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def sample(self, elapsed_override: float | None = None) -> None:
        """Take a 1-second rate measurement and append it to the internal list.

        Reads byte counters, waits MEASUREMENT_WINDOW_SECONDS, reads again,
        and computes Mbps over that window.

        elapsed_override: virtual elapsed_days label for this sample.
        """
        t_start = time.monotonic()
        before = self._read_tx_bytes()
        time.sleep(self.MEASUREMENT_WINDOW_SECONDS)
        after = self._read_tx_bytes()
        dt = time.monotonic() - t_start

        if not before or not after:
            logger.warning("TrafficSampler: /proc/net/dev returned no data")
            return

        elapsed = elapsed_override if elapsed_override is not None else self.clock.elapsed_days
        prefix = self.monitored_prefixes[0] if self.monitored_prefixes else "total"
        mbps_row: dict[str, float] = {}
        for provider, iface in self.provider_ifaces.items():
            delta = max(0, after.get(iface, 0) - before.get(iface, 0))
            mbps_row[f"via_{provider}"] = round((delta * 8) / (dt * 1_000_000), 3)

        self._samples.append({
            "elapsed_days": round(elapsed, 3),
            "mbps": {prefix: mbps_row},
        })
        logger.debug("TrafficSampler sample at day %.3f: %s", elapsed, mbps_row)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def measure_now(self) -> str:
        """Take a live instantaneous measurement and return it as JSON.

        Called by agents via the get_traffic_sample tool to get the current
        traffic rate at the moment of calling, independent of stored history.
        """
        import json
        t_start = time.monotonic()
        before = self._read_tx_bytes()
        time.sleep(self.MEASUREMENT_WINDOW_SECONDS)
        after = self._read_tx_bytes()
        dt = time.monotonic() - t_start

        if not before or not after:
            return json.dumps({"elapsed_days": round(self.clock.elapsed_days, 3), "mbps": {}})

        prefix = self.monitored_prefixes[0] if self.monitored_prefixes else "total"
        mbps_row: dict[str, float] = {}
        for provider, iface in self.provider_ifaces.items():
            delta = max(0, after.get(iface, 0) - before.get(iface, 0))
            mbps_row[f"via_{provider}"] = round((delta * 8) / (dt * 1_000_000), 3)

        return json.dumps({
            "elapsed_days": round(self.clock.elapsed_days, 3),
            "mbps": {prefix: mbps_row},
        }, indent=2)

    def start(self) -> None:
        """Initialise the sampler."""
        logger.info("TrafficSampler started (node=%s)", self.billing_node)

    def stop(self) -> None:
        logger.info("TrafficSampler stopped (%d samples collected)", len(self._samples))

    @property
    def samples(self) -> list[dict]:
        return list(self._samples)
