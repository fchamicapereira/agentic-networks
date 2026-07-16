import logging
import os
import signal
import subprocess

from .network import NetworkHost

# Hard cap on how long a single agent command may run. Routing/diagnostic commands in these
# experiments finish in seconds; a longer-running command is almost always pathological —
# an infinite loop, a flood, or a backgrounded process that keeps the stdout pipe open and
# would otherwise block communicate() forever (common in chaotic/malicious scenarios).
_EXEC_TIMEOUT_SECONDS = 60.0


class MininetHost:
    """A wrapper around a Mininet host that allows an LLM to interact with it via tools and messaging."""

    def __init__(self, node_name: str, host: "NetworkHost"):
        self.node_name = node_name
        self.host = host
        self.log = logging.getLogger(f"agent.{node_name}")

    def _terminate(self, proc: subprocess.Popen) -> None:
        """Kill the command and, best-effort, its whole process group — a bare proc.kill()
        leaves backgrounded/disowned children alive, and they keep the stdout pipe open."""
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass

    def exec(self, command: str, timeout: float = _EXEC_TIMEOUT_SECONDS) -> tuple[str, int]:
        self.log.info("Executing command: %s", command)
        # start_new_session so the command (and any children it backgrounds) gets its own
        # process group, letting _terminate kill the whole tree on timeout.
        if self.host.anchor_pid is not None:
            # Host isolation is enabled: run inside the host's private PID+mount
            # namespace via nsenter so `ps`/`/proc` show only this host's processes
            # (mnexec's -a cannot enter a PID namespace). ns_popen builds the argv.
            proc = self.host.ns_popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        else:
            proc = self.host.popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        try:
            stdout, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._terminate(proc)
            # Reap the (now-killed) shell; cap the wait in case a backgrounded child still
            # holds the pipe open so we never re-block here.
            try:
                stdout, _ = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                stdout = b""
            partial = (stdout.decode(errors="replace") if isinstance(stdout, bytes) else stdout or "").strip()
            self.log.warning("Command timed out after %.0fs and was killed: %s", timeout, command)
            msg = (
                f"Command timed out after {timeout:.0f}s and was killed. It likely ran forever or "
                "spawned a long-running/backgrounded process. Avoid infinite loops, floods, and "
                "unbounded commands; use bounded forms (e.g. ping -c, timeout <N> <cmd>)."
            )
            return (f"{partial}\n{msg}" if partial else msg), 124
        output = (stdout.decode(errors="replace") if isinstance(stdout, bytes) else stdout).strip()
        exit_code = proc.returncode
        if output:
            self.log.info("Command output (exit %d):\n%s", exit_code, output)
        else:
            self.log.info("Command output (exit %d): (empty)", exit_code)
        return output or "(no output)", exit_code
