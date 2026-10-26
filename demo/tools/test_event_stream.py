#!/usr/bin/env python3
"""test_event_stream.py — Does a live run's event stream match its recording?

Runs a short scripted exchange on a two-node network, with fake agents in place of the models
(no API calls, nothing to pay), writing both the live event stream (--events in the experiments)
and the usual per-node logs. Then converts the logs the way recordings are made
(demo/tools/logs_to_events.py) and checks that, node by node, both give the same events.

Expected differences, not checked: live runs alone have `routes` events. Live runs place each
`turn` after the message that woke the agent (recordings place it before), so turns are only
counted. And the logs have whole-second timestamps, so a recording can misplace a `delivered`
among events of the same second; deliveries are compared without their position.

    tools/run_in_docker.sh demo/tools/test_event_stream.py      # exits 0 if they match
"""

import json
import sys
import tempfile

from pathlib import Path

from agentic_networks import agentic_network
from agentic_networks.agent import Agent, LLMResponse, ToolUseBlock
from agentic_networks.agent_claude import MODELS as CLAUDE_MODELS
from agentic_networks.events import EventLog, load_topology as load_event_topology
from agentic_networks.experiment import setup_logging, setup_node_logs
from agentic_networks.network import Network, load_topology
from agentic_networks.paths import TOPOLOGIES_DIR

sys.path.insert(0, str(Path(__file__).resolve().parent))
from logs_to_events import convert_run  # noqa: E402

TOPOLOGY = TOPOLOGIES_DIR / "pair.csv"
STEM = "event-stream-test"


def call(tool: str, reason: str, **inputs) -> ToolUseBlock:
    return ToolUseBlock(id=f"{tool}-{reason}", tool_name=tool, input={**inputs, "reason": reason})


# Each node's replies, one per turn. Between them they cover every agent event: prose, a
# command, a failing command that halts the rest of the turn, a route change, messages both
# ways, a turn with no tool (reminded), a second one (taken as idle), and idle.
SCRIPTS = {
    "A": [
        ["Looking around first.",
         call("exec", "see the routes", command="ip route show"),
         call("exec", "a command that fails", command="exit 3"),
         call("exec", "never runs", command="echo skipped")],
        [call("exec", "add a route", command="ip route add 10.99.0.0/24 via 10.0.12.2"),
         call("send_message", "say hello", to="B", message="Hello B, can you hear me?")],
        [call("idle", "wait for B")],
        [call("idle", "nothing left")],
    ],
    "B": [
        [call("exec", "check in", command="echo hi from B"),
         call("send_message", "answer A", to="A", message="Loud and clear.")],
        ["I think we are done here."],
        ["Still nothing to do."],
    ],
}


class ScriptedAgent(Agent):
    """Plays back SCRIPTS[name] in place of a model."""

    def __init__(self, model, name, system_prompt, max_tokens, tool_defs, window_size):
        super().__init__(model, name, system_prompt, max_tokens, tool_defs, window_size)
        self.replies = list(SCRIPTS[name])

    def request_action(self, user_message: str) -> LLMResponse:
        content = self.replies.pop(0) if self.replies else [call("idle", "script over")]
        return LLMResponse(raw="", content=content, stop_reason="tool_use")

    def store_tool_result(self, block, result):
        pass

    def add_user_message(self, content):
        pass

    def query(self, user_message):
        return ""

    def request_report(self):
        return f"Report from {self.name}."


def per_node(events: list[dict]) -> tuple[dict, dict, dict]:
    """Each node's events as comparable tuples, its number of turns, and the messages delivered to it."""
    messages = {e["id"]: (e["from"], e["text"]) for e in events if e["type"] == "message"}
    fields = {"prompt": ["text"], "assistant": ["text"], "exec": ["command", "reason"],
              "exec_result": ["output", "exit"], "message": ["to", "text", "reason"], "idle": ["reason"],
              "state": ["state"], "warning": ["text"], "report": ["text"]}
    seq: dict[str, list] = {}
    turns: dict[str, int] = {}
    delivered: dict[str, list] = {}
    for e in events:
        node, kind = e.get("node"), e["type"]
        if kind == "turn":
            turns[node] = turns.get(node, 0) + 1
        elif kind == "delivered":
            delivered.setdefault(node, []).append(messages[e["id"]])
        elif kind in fields:
            seq.setdefault(node, []).append((kind, *(e.get(f) for f in fields[kind])))
    return seq, turns, {node: sorted(msgs) for node, msgs in delivered.items()}


def main() -> int:
    setup_logging("INFO")
    agentic_network.AgentClaude = ScriptedAgent  # every node on a "Claude" model gets the script
    model = next(iter(CLAUDE_MODELS))

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        network = Network(load_topology(str(TOPOLOGY)))
        network.start()
        try:
            setup_node_logs(network.hosts, tmp, STEM)
            events = EventLog(tmp / "events.jsonl")
            topology = load_event_topology(TOPOLOGY)
            # pair.csv has links only; the stream (and the converter) need the nodes too.
            topology["nodes"] = topology["nodes"] or [{"id": n, "address": ""} for n in network.hosts]
            events.run_start("test", "Event stream test", model, {n: model for n in network.hosts}, topology)
            anet = agentic_network.AgenticNetwork(
                network=network, initial_prompts="You are a test agent.", model_key=model,
                max_iterations=10, max_tokens=1024, vllm_host="", vllm_port=0, window_size=0,
                start_waiting=["B"], events=events,
            )
            anet.run(concurrent=True)
            for name, text in anet.gather_reports().items():
                (tmp / f"{STEM}-{name}-report.md").write_text(text)
            events.close()
        finally:
            network.stop()

        live = [json.loads(line) for line in (tmp / "events.jsonl").read_text().splitlines()]
        recorded, _ = convert_run(tmp, STEM, topology, "test", "Event stream test", model, model)

    failed = False

    def check(ok: bool, what: str) -> None:
        nonlocal failed
        failed |= not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {what}")

    print("\nLive stream:")
    for e in live:
        print("   ", json.dumps(e)[:150])

    print("\nChecks:")
    check(live[0]["type"] == "run_start" and live[0]["topology"] == topology, "starts with run_start and the topology")
    times = [e["t"] for e in live]
    check(times == sorted(times), "times never go backwards")
    ends = [e for e in live if e["type"] == "run_end"]
    check(len(ends) == 1 and ends[0]["reason"] == "all_dormant", "one run_end, with every agent idle")
    check(any(e["type"] == "routes" and "10.99.0.0/24" in e["table"] for e in live), "the route A added shows up")
    ids = [e["id"] for e in live if e["type"] == "message"]
    delivered = [e["id"] for e in live if e["type"] == "delivered"]
    check(sorted(ids) == sorted(delivered), "every message is delivered exactly once")

    live_seq, live_turns, live_delivered = per_node(live)
    rec_seq, rec_turns, rec_delivered = per_node(recorded)
    for node in sorted(set(live_seq) | set(rec_seq)):
        same = live_seq.get(node) == rec_seq.get(node)
        check(same, f"{node}: same {len(live_seq.get(node, []))} events as the recording")
        if not same:
            for i, (a, b) in enumerate(zip(live_seq.get(node, []) + [None] * 99, rec_seq.get(node, []) + [None] * 99)):
                if a is None and b is None:
                    break
                print(f"        {'==' if a == b else '!='} live {a}\n           rec  {b}")
        check(live_turns.get(node) == rec_turns.get(node),
              f"{node}: same number of turns ({live_turns.get(node)} live, {rec_turns.get(node)} recorded)")
        check(live_delivered.get(node) == rec_delivered.get(node),
              f"{node}: same {len(live_delivered.get(node, []))} messages delivered")

    print("\nRESULT:", "FAIL" if failed else "ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
