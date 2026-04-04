import logging
import pprint

from typing import Literal, Optional, TypeAlias

from message_bus import MessageBus
from mininet_host import MininetHost

from dataclasses import dataclass

SYSTEM_PROMPT_TEMPLATE = """\
You are an autonomous network agent running on node {node_name} in a network testbed.
Other nodes in the network: {other_nodes}.
{initial_prompt}
"""

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
        "name": "get_network_info",
        "description": (
            "Show current network interface addresses (ip addr show) " "and routing table (ip route show). Use this to understand " "your current configuration before and after making changes."
        ),
        "schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_route",
        "description": "Add a route to the routing table.",
        "schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "Destination network in CIDR notation, e.g. '10.0.12.0/30'"},
                "dev": {"type": "string", "description": "Output interface name, e.g. 'h1-eth0'"},
                "via": {"type": "string", "description": "Optional gateway IP address for indirect routes"},
            },
            "required": ["destination", "dev"],
        },
    },
    {
        "name": "delete_route",
        "description": "Delete a route from the routing table.",
        "schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "Destination network in CIDR notation, e.g. '10.0.12.0/30'"},
            },
            "required": ["destination"],
        },
    },
    {
        "name": "ping",
        "description": "Send ICMP echo requests to test reachability of an IP address.",
        "schema": {
            "type": "object",
            "properties": {
                "target_ip": {"type": "string", "description": "Target IP address"},
                "count": {"type": "integer", "description": "Number of packets to send (default 3)"},
            },
            "required": ["target_ip"],
        },
    },
    {
        "name": "report_done",
        "description": ("Signal that you want to terminate and are satisfied with the current state of the entire network."),
        "schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Summary of routes added and connectivity verified"},
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
]


class NodeAgent:
    def __init__(
        self,
        node_name: str,
        mininet_host_cmd,
        bus: MessageBus,
        initial_prompt: str,
        model: str,
        max_iterations: int,
        max_tokens: int,
    ):
        self.node_name = node_name
        self.mininet_host = MininetHost(node_name, mininet_host_cmd)
        self.bus = bus
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.model = model
        self.log = logging.getLogger(f"agent.{node_name}")

        self.initial_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            node_name=self.node_name,
            other_nodes=", ".join(n for n in self.bus._queues if n != self.node_name),
            initial_prompt=initial_prompt,
        )

        self.tools = {
            "get_network_info": self.mininet_host.get_network_info,
            "add_route": self.mininet_host.add_route,
            "delete_route": self.mininet_host.delete_route,
            "ping": self.mininet_host.ping,
            "send_message": self.send_message,
            "report_done": lambda **kwargs: f"Acknowledged: {kwargs.get('message', '')}",
            "unknown": lambda **kargs: f"Unknown tool: {kargs.get('name', 'unknown')}. Available tools: {', '.join(self.tools.keys())}",
        }

    def send_message(self, to: str, message: str):
        self.log.info("[msg → %s] %s", to, message)
        self.bus.send(to=to, sender=self.node_name, message=message)

    def _execute_tool(self, name: str, inputs: dict) -> Optional[str]:
        try:
            self.log.info("Executing tool: %s with inputs: %s", name, inputs)
            results = self.tools.get(name, "unknown")(**inputs)

            if results is not None:
                self.log.info(results)

            return results
        except Exception as exc:
            return f"Error in {name}: {exc}"

    def request_action_from_model(self) -> LLMResponse:
        raise NotImplementedError("Must be implemented by subclass")

    def store_tool_results(self, tool_use_block: ToolUseBlock, tool_result: str):
        raise NotImplementedError("Must be implemented by subclass")

    def process_received_message(self, sender: str, message: str):
        raise NotImplementedError("Must be implemented by subclass")

    def run(self) -> AgentResult:
        self.log.info("System prompt:\n%s", self.initial_prompt)

        final_report = AgentResult(success=False, message="Max iterations reached without completion")

        for iteration in range(self.max_iterations):
            self.log.info("--- Iteration %d/%d ---", iteration + 1, self.max_iterations)

            response = self.request_action_from_model()
            self.log.debug(pprint.pformat(response, indent=2))

            for block in response.content:
                if isinstance(block, str):
                    self.log.info("[assistant] %s", block)

            if response.stop_reason == "max_tokens":
                self.log.warning("Token limit reached (max_tokens=%d); response may be truncated.", self.max_tokens)

            if response.stop_reason == "unknown":
                self.log.warning("Unexpected stop_reason: %s", response.stop_reason)
                break

            done = False
            for block in response.content:
                if not isinstance(block, ToolUseBlock):
                    continue

                results = self._execute_tool(block.tool_name, block.input)
                if results is not None:
                    self.store_tool_results(block, results)

                if block.tool_name == "report_done":
                    done = True
                    final_report = AgentResult(
                        success=block.input.get("success", False),
                        message=block.input.get("message", ""),
                    )

            # Inject any messages that arrived from other agents since last iteration
            inbox = self.bus.drain(self.node_name)
            for sender, msg in inbox:
                self.log.info("[msg ← %s] %s", sender, msg)
                self.process_received_message(sender, msg)

            if done:
                self.log.info("Done — %s", final_report.message)
                break

        if not final_report.success:
            self.log.warning("Agent did not report success within max iterations. Final report: %s", final_report.message)

        return final_report
