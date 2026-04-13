import logging
import pprint

from typing import Literal, Optional, TypeAlias

from message_bus import MessageBus
from mininet_host import MininetHost
from mininet.node import Host
from network import Interface

from dataclasses import dataclass

SYSTEM_PROMPT_TEMPLATE = """\
You are an autonomous network agent running on node {node_name} in a network testbed.
Other nodes in the network: {other_nodes}.
Physical connections:
{connections}
Using tools:
- You may issue multiple tools at once. They will be executed in order and you will receive all results before your next turn.
- Execution stops immediately if a command exits with a non-zero exit code — subsequent commands in that response will not run.
- 'report_done' must be called alone — never alongside other tools. If combined with other tools it will be ignored and you will be warned.
{initial_prompt}
"""

WAIT_DEFAULT_TIMEOUT_S = 5

StopReason: TypeAlias = Literal[
    "end_turn",
    "max_tokens",
    "stop_sequence",
    "tool_use",
    "pause_turn",
    "refusal",
    "unknown",
]


@dataclass
class ToolUseBlock:
    id: str
    tool_name: str
    input: dict


@dataclass
class LLMResponse:
    raw: str
    content: list[ToolUseBlock | str]
    stop_reason: StopReason


@dataclass
class AgentResult:
    success: bool
    message: str


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
            },
            "required": ["command"],
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
            },
            "required": ["message", "success"],
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
            },
            "required": ["to", "message"],
        },
    },
    {
        "name": "wait",
        "description": "Block until a message arrives from another node (or until timeout). Use this when you have completed your local actions and need to wait for other nodes to respond or coordinate before proceeding.",
        "schema": {
            "type": "object",
            "properties": {
                "timeout": {"type": "number", "description": f"Maximum seconds to wait for a message (default: {WAIT_DEFAULT_TIMEOUT_S})"},
            },
            "required": [],
        },
    },
]


class NodeAgent:
    def __init__(
        self,
        node_name: str,
        host: Host,
        bus: MessageBus,
        initial_prompt: str,
        model: str,
        max_iterations: int,
        max_tokens: int,
        ifaces: list[Interface],
    ):
        self.node_name = node_name
        self.mininet_host = MininetHost(node_name, host)
        self.bus = bus
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.model = model
        self.log = logging.getLogger(f"agent.{node_name}")

        connections = "\n".join(f"  - {iface.iface}: connected to {iface.peer} (your IP: {iface.ip}, peer IP: {iface.peer_ip})" for iface in ifaces)
        self.initial_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            node_name=self.node_name,
            other_nodes=", ".join(n for n in self.bus._queues if n != self.node_name),
            connections=connections,
            initial_prompt=initial_prompt,
        )

        self.tools = {
            "exec": self.mininet_host.exec,
            "send_message": self.send_message,
            "wait": self.wait,
            "report_done": lambda **kwargs: f"Acknowledged: {kwargs.get('message', '')}",
        }

    def send_message(self, to: str, message: str):
        self.log.info("[msg → %s] %s", to, message)
        self.bus.send(to=to, sender=self.node_name, message=message)

    def wait(self, timeout: float = WAIT_DEFAULT_TIMEOUT_S) -> str:
        # Non-blocking: in the cooperative scheduler other agents run between iterations,
        # so blocking here would stall the whole network. Drain whatever is already queued.
        msgs = self._drain_inbox(block=False)
        if not msgs:
            return "No messages in queue yet — will check again next iteration."
        return f"Received {len(msgs)} message(s)."

    def _drain_inbox(self, block: bool = False, timeout: Optional[float] = None) -> list[tuple[str, str]]:
        msgs = self.bus.drain(self.node_name, block=block, timeout=timeout)
        for sender, msg in msgs:
            self.log.info("[msg ← %s] %s", sender, msg)
            self.process_received_message(sender, msg)
        return msgs

    def _execute_tool(self, name: str, inputs: dict) -> tuple[str, bool]:
        """Execute a tool and return (result, should_stop).

        should_stop is True when an exec command exits with a non-zero code.
        """
        try:
            self.log.info("%s(%s)", name, inputs)
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

    def request_action_from_model(self) -> LLMResponse:
        raise NotImplementedError("Must be implemented by subclass")

    def store_tool_results(self, tool_use_block: ToolUseBlock, tool_result: str):
        raise NotImplementedError("Must be implemented by subclass")

    def process_received_message(self, sender: str, message: str):
        raise NotImplementedError("Must be implemented by subclass")

    def run(self):
        """Generator: runs one LLM iteration per next() call, then yields.

        Returns the final AgentResult via StopIteration.value when done,
        so AgenticNetwork can collect results with::

            try:
                next(gen)
            except StopIteration as e:
                result = e.value
        """
        self.log.info("System prompt:\n%s", self.initial_prompt)

        final_report = AgentResult(success=False, message="Max iterations reached without completion")

        for iteration in range(self.max_iterations):
            self.log.info("--- Iteration %d/%d ---", iteration + 1, self.max_iterations)

            response = self.request_action_from_model()

            self.log.debug("Raw response from model:\n%s", response.raw)
            self.log.debug("Content:\n%s", pprint.pformat(response.content, indent=2))
            self.log.debug("Stop reason: %s", response.stop_reason)

            for block in response.content:
                if isinstance(block, str):
                    self.log.info("[assistant] %s", block)

            if response.stop_reason == "max_tokens":
                self.log.warning("Token limit reached (max_tokens=%d); response may be truncated.", self.max_tokens)

            if response.stop_reason == "unknown":
                self.log.warning("Unexpected stop_reason: %s", response.stop_reason)
                break

            tool_blocks = [b for b in response.content if isinstance(b, ToolUseBlock)]

            # report_done is only accepted when called alone
            report_done_blocks = [b for b in tool_blocks if b.tool_name == "report_done"]
            if report_done_blocks and len(tool_blocks) > 1:
                warning = (
                    "'report_done' was called alongside other tools and has been ignored. " "'report_done' must be the only tool call in a response. Please call it alone when you are ready to finish."
                )
                self.log.warning(warning)
                for b in report_done_blocks:
                    self.store_tool_results(b, warning)
                tool_blocks = [b for b in tool_blocks if b.tool_name != "report_done"]

            done = False
            for block in tool_blocks:
                result, should_stop = self._execute_tool(block.tool_name, block.input)
                self.store_tool_results(block, result)

                if block.tool_name == "report_done":
                    done = True
                    final_report = AgentResult(
                        success=block.input.get("success", False),
                        message=block.input.get("message", ""),
                    )
                    break

                if should_stop:
                    stop_warning = (
                        "Execution halted: the previous command exited with a non-zero exit code. " "The remaining tools in this response were not executed. Please investigate the error above."
                    )
                    self.log.warning(stop_warning)
                    # Notify the model about skipped tools
                    for skipped in tool_blocks[tool_blocks.index(block) + 1 :]:
                        self.store_tool_results(skipped, f"Not executed — halted due to previous command failure. {stop_warning}")
                    break

            # Non-blocking drain at end of every iteration
            self._drain_inbox()

            if done:
                self.log.info("Done — %s", final_report.message)
                break

            yield iteration + 1  # give way; pass completed iteration count to scheduler

        self.log.info("Agent run complete. Final report: %s", final_report)
        return final_report
