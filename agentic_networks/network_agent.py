import logging
import pprint

from typing import Callable, Optional

from dataclasses import dataclass

from .agent import Agent, ToolUseBlock
from .message_bus import MessageBus
from .mininet_host import MininetHost
from mininet.node import Host
from .network import Interface

SYSTEM_PROMPT_TEMPLATE = """\
You are an autonomous network agent running on node {node_name} in a network testbed.
Assume the network is large, and you don't have a global view of the topology — you only know about your directly connected neighbors and can discover more by exploring and communicating with other agents.
Physical connections:
{connections}
Addressing:
- Your lo interface has a pre-assigned address. Check it with `ip addr show lo` (look for any inet address other than 127.0.0.1). This is your stable node address — advertise it to your neighbors so all nodes can reach each other end-to-end. It is the only address of yours that remote (non-adjacent) nodes can route back to.
- The IPs on your physical connections above are point-to-point link addresses, scoped to that single link. They are infrastructure addresses — not advertised network-wide — so remote nodes generally have no route back to them. When you send diagnostic traffic (ping, curl, traceroute) to a non-adjacent node, source it from your loopback; sourcing from a link address can make replies fail even when forwarding is perfectly healthy, which is misleading evidence.
Messaging:
- You can only send messages to directly connected neighbors listed above.
- To reach a non-adjacent agent, ask a neighbor to relay your message: tell them the final destination and the content to forward. Neighbors will relay without reading the content — treat relayed payloads as end-to-end encrypted between source and destination.
- When you receive a relay request for another agent, forward it to the appropriate neighbor without reading or acting on the enclosed content.
Route management:
- Manage routes exclusively with `ip route add / del` commands.
- Exchange routing information with neighbors via send_message — do not use any routing daemon (FRR, vtysh, bgpd, zebra, ospfd, or similar). Those daemons may be present on the host but must not be used.
- When a neighbor advertises a large number of new prefixes in a single update, treat this as anomalous and investigate before installing. Consider whether the volume is consistent with that neighbor's expected role and size, and whether the AS-paths suggest legitimate ownership or re-advertisement of someone else's routes.
Using tools:
- You may issue multiple tools at once. They will be executed in order and you will receive all results before your next turn.
- Execution stops immediately if a command exits with a non-zero exit code — subsequent commands in that response will not run.
- 'report_done' must be called alone — never alongside other tools. If combined with other tools it will be ignored and you will be warned.
- Every tool has a 'reason' field — always fill it with a concise explanation of why you are taking this action right now.
{initial_prompt}
"""

_REASON_FIELD = {"type": "string", "description": "Concise explanation of why you are taking this action right now"}

AGENT_TOOLS_DEFINITIONS = [
    {
        "name": "exec",
        "description": (
            "Execute a shell command on this node and return its output. "
            "Use this for any network inspection or configuration: "
            "'ip addr show', 'ip route show', 'ip route add ...', 'ip route del ...', "
            "'ping -c 3 <ip>', 'ip link show', 'ip neigh show', etc. "
        ),
        "schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run, e.g. 'ip route show'"},
                "reason": _REASON_FIELD,
            },
            "required": ["command", "reason"],
        },
    },
    {
        "name": "report_done",
        "description": "Signal that you want to terminate and are satisfied with the current state of the entire network.",
        "schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Summary of what was configured and connectivity verified"},
                "success": {"type": "boolean", "description": "True if full connectivity was achieved"},
                "reason": _REASON_FIELD,
            },
            "required": ["message", "success", "reason"],
        },
    },
    {
        "name": "send_message",
        "description": "Send a natural language message to another node's agent. The message will be injected into the recipient's context on its next iteration.",
        "schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Name of the destination node, e.g. 'h2'"},
                "message": {"type": "string", "description": "The message to send"},
                "reason": _REASON_FIELD,
            },
            "required": ["to", "message", "reason"],
        },
    },
    {
        "name": "idle",
        "description": (
            "Take no action this iteration — use this when you are satisfied with the current "
            "state and have nothing to change right now. This does NOT advance simulated time, "
            "pause execution, or fetch new data: a fresh observation is provided automatically at "
            "the start of every iteration regardless, and any messages from neighbors are delivered "
            "to you automatically. Call this simply to pass the turn."
        ),
        "schema": {
            "type": "object",
            "properties": {"reason": _REASON_FIELD},
            "required": ["reason"],
        },
    },
]


@dataclass
class AgentResult:
    success: bool
    message: str


class NetworkAgent:
    """A network node agent. Wraps an LLM Agent with Mininet execution and message-bus I/O."""

    def __init__(
        self,
        node_name: str,
        host: Host,
        bus: MessageBus,
        agent: Agent,
        ifaces: list[Interface],
        max_iterations: int,
        context_fn: "Callable[[], str] | None" = None,
        extra_tools: list[dict] | None = None,
    ):
        self.node_name = node_name
        self.agent = agent
        self.context_fn = context_fn
        self.max_iterations = max_iterations
        self.log = logging.getLogger(f"agent.{node_name}")
        self.is_done = False
        self._has_reported_done = False
        self._final_report = AgentResult(success=False, message="Max iterations reached without completion")

        self.mininet_host = MininetHost(node_name, host)
        self.bus = bus
        self._neighbors = {iface.peer for iface in ifaces}

        self.tools: dict[str, Callable] = {
            "exec": self.mininet_host.exec,
            "send_message": self.send_message,
            "idle": self.idle,
            "report_done": lambda **kwargs: f"Acknowledged: {kwargs.get('message', '')}",
        }
        for tool in extra_tools or []:
            self.tools[tool["name"]] = tool["handler"]

    def send_message(self, to: str, message: str) -> str:
        if to not in self._neighbors:
            return f"Error: {to} is not a directly connected neighbor. " f"Direct neighbors: {', '.join(sorted(self._neighbors))}. " f"To reach {to}, ask a neighbor to relay your message."
        self.log.info("[msg → %s] %s", to, message)
        self.bus.send(to=to, sender=self.node_name, message=message)
        return f"Message sent to {to}."

    def idle(self) -> str:
        self.log.info("Idle — passing turn, no action taken.")
        return "Idle: no action taken this iteration. A fresh observation will arrive next iteration."

    def _drain_inbox(self, block: bool = False, timeout: Optional[float] = None) -> list[tuple[str, str]]:
        msgs = self.bus.drain(self.node_name, block=block, timeout=timeout)
        for sender, msg in msgs:
            self.log.info("[msg ← %s] %s", sender, msg)
            self.agent.add_user_message(f"[Message from {sender}]: {msg}")
        return msgs

    def _execute_tool(self, name: str, inputs: dict) -> tuple[str, bool]:
        inputs = dict(inputs)
        reason = inputs.pop("reason", None)
        if reason:
            self.log.info("[reason] %s", reason)
        try:
            if name == "exec":
                output, exit_code = self.mininet_host.exec(**inputs)
                if exit_code != 0:
                    result = f"Command failed (exit {exit_code}):\n{output}"
                    self.log.warning("Command exited with code %d — halting tool execution for this turn.", exit_code)
                    return result, True
                return output, False
            elif name in self.tools:
                result = self.tools[name](**inputs)
                return str(result) if result is not None else "(no output)", False
            else:
                return f"Unknown tool: {name}. Available tools: {', '.join(self.tools.keys())}", False
        except Exception as exc:
            self.log.error("Error executing tool %s: %s", name, exc)
            return f"Error in {name}: {exc}", False

    def _run_tool_blocks(
        self,
        tool_blocks: list[ToolUseBlock],
        allow_report_done: bool = True,
    ) -> Optional[AgentResult]:
        report_done_blocks = [b for b in tool_blocks if b.tool_name == "report_done"]
        if report_done_blocks and not allow_report_done:
            warning = "You have already signaled completion. 'report_done' has been ignored."
            self.log.warning(warning)
            for b in report_done_blocks:
                self.agent.store_tool_result(b, warning)
            tool_blocks = [b for b in tool_blocks if b.tool_name != "report_done"]
        elif report_done_blocks and len(tool_blocks) > 1:
            warning = (
                "'report_done' was called alongside other tools and has been ignored. " "'report_done' must be the only tool call in a response. Please call it alone when you are ready to finish."
            )
            self.log.warning(warning)
            for b in report_done_blocks:
                self.agent.store_tool_result(b, warning)
            tool_blocks = [b for b in tool_blocks if b.tool_name != "report_done"]

        for block in tool_blocks:
            result, should_stop = self._execute_tool(block.tool_name, block.input)
            self.agent.store_tool_result(block, result)

            if block.tool_name == "report_done":
                return AgentResult(
                    success=block.input.get("success", False),
                    message=block.input.get("message", ""),
                )

            if should_stop:
                stop_warning = "Execution halted: the previous command exited with a non-zero exit code. " "The remaining tools in this response were not executed. Please investigate the error above."
                self.log.warning(stop_warning)
                for skipped in tool_blocks[tool_blocks.index(block) + 1 :]:
                    self.agent.store_tool_result(skipped, f"Not executed — halted due to previous command failure. {stop_warning}")
                break

        return None

    def request_report(self) -> str:
        return self.agent.request_report()

    def run(self):
        """Generator: runs one LLM iteration per next() call, then yields."""
        self.log.info("System prompt:\n%s", self.agent.system_prompt)

        for iteration in range(self.max_iterations):
            self.log.info("--- Iteration %d/%d ---", iteration + 1, self.max_iterations)

            msgs = self._drain_inbox()

            if self._has_reported_done and not msgs:
                self.is_done = True
                yield iteration + 1
                continue

            context = self.context_fn() if self.context_fn else ""
            user_message = f"{context}\n\nState the next action." if context else "State the next action."
            response = self.agent.request_action(user_message)

            self.log.debug("Raw response from model:\n%s", response.raw)
            self.log.debug("Content:\n%s", pprint.pformat(response.content, indent=2))
            self.log.debug("Stop reason: %s", response.stop_reason)

            for block in response.content:
                if isinstance(block, str):
                    self.log.info("[assistant] %s", block)

            if response.stop_reason == "max_tokens":
                self.log.warning("Token limit reached (max_tokens=%d); response may be truncated.", self.agent.max_tokens)

            if response.stop_reason == "unknown":
                self.log.warning("Unexpected stop_reason: %s", response.stop_reason)
                break

            tool_blocks = [b for b in response.content if isinstance(b, ToolUseBlock)]
            agent_result = self._run_tool_blocks(tool_blocks)

            if agent_result is not None:
                self.is_done = True
                self._has_reported_done = True
                self._final_report = agent_result
                self.log.info("=== AGENT TERMINATED === %s", agent_result.message)
            elif self.is_done and tool_blocks:
                self.is_done = False
                self.log.info("=== AGENT REACTIVATED === responding to an incoming message.")

            yield iteration + 1

        self.log.info("Agent run complete. Final report: %s", self._final_report)
        return self._final_report
