#!/usr/bin/env python3
"""test_system_prompts.py — Do agents get exactly the system prompt the demo shows and sends?

The demo shows each agent's whole system prompt, lets attendees edit it, and passes the edited
text to the run (--system-prompts), which must use it exactly as given. For text-tool models
(vLLM, Together) the harness normally adds a tool guide after the prompt, so the demo shows the
guide too (a preview's prompt plus its tool_guide). This builds agents for a two-node network,
without calling any model, and checks for a native-tools model (Claude) and a text-tool one
(Qwen, on vLLM):
  1. an agent given a system prompt gets exactly that text;
  2. an agent not given one gets the template, plus the tool guide for Qwen;
  3. a preview (describe_run) shows what an agent not given one gets.

    tools/run_in_docker.sh demo/tools/test_system_prompts.py      # exits 0 if all hold
"""

import json
import os
import sys
import tempfile

from pathlib import Path

from agentic_networks import agent_vllm, agentic_network
from agentic_networks.agentic_network import _create_network_agent, describe_run, system_prompt_for
from agentic_networks.agent_vllm import with_tool_guide
from agentic_networks.message_bus import MessageBus
from agentic_networks.network import Network, load_topology
from agentic_networks.paths import TOPOLOGIES_DIR

TOPOLOGY = TOPOLOGIES_DIR / "pair.csv"
EXTRA_TOOLS = [{"name": "probe", "description": "A tool only this test has.",
                "schema": {"type": "object", "properties": {}, "required": []}, "handler": lambda: "ok"}]
EDITED = "An attendee's prompt.\nNothing else: no template, no tool guide.\n"


def main() -> int:
    # Build agents without reaching anything: no vLLM server, no API calls.
    agent_vllm.check_server = lambda base_url: True
    agent_vllm.fetch_context_limit = lambda client, model, default=0: 32768
    os.environ.setdefault("ANTHROPIC_API_KEY", "not-used-by-this-test")

    network = Network(load_topology(str(TOPOLOGY)))  # constructed, never started
    bus = MessageBus(list(network.ifaces_per_host))
    claude = next(k for k in agentic_network.MODELS if k in agentic_network.CLAUDE_MODELS)
    qwen = next(k for k in agentic_network.MODELS if k in agentic_network.VLLM_MODELS)

    def agent(model, observing, system_prompt=None):
        return _create_network_agent(
            node_name="A", host=None, bus=bus, initial_prompt="Scenario prompt for A.", model_key=model,
            max_iterations=1, max_tokens=1024, vllm_host="localhost", vllm_port=8000,
            ifaces=network.ifaces_per_host["A"], window_size=0, extra_tools=EXTRA_TOOLS,
            context_fn=(lambda: "") if observing else None, system_prompt=system_prompt,
        ).agent.system_prompt

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "describe.jsonl"
        describe_run(str(path), "test", "test", network, str(TOPOLOGY), "Scenario prompt for A.",
                     extra_tools=EXTRA_TOOLS, observing=["A"])
        preview = next(e for e in map(json.loads, path.read_text().splitlines()) if e.get("node") == "A")

    base = system_prompt_for("A", network.ifaces_per_host["A"], "Scenario prompt for A.")
    checks = [
        ("Claude, given a prompt: exactly it", agent(claude, True, EDITED) == EDITED),
        ("Qwen, given a prompt: exactly it (no tool guide added)", agent(qwen, True, EDITED) == EDITED),
        ("Claude, no prompt given: the template", agent(claude, True) == base),
        ("Qwen, no prompt given: the template and the tool guide", agent(qwen, True) == with_tool_guide(base, agentic_network.agent_tool_defs(EXTRA_TOOLS, True))),
        ("preview: what Claude gets", preview["text"] == agent(claude, True).strip()),
        ("preview + tool_guide: what Qwen gets", preview["text"] + "\n\n" + preview["tool_guide"] == agent(qwen, True).strip()),
        ("the guide lists the experiment's own tool", "probe(" in preview["tool_guide"]),
        ("observing agents' guide differs (idle passes the turn)", agent(qwen, True) != agent(qwen, False)),
    ]
    for what, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'}  {what}")
    failed = not all(ok for _, ok in checks)
    print("RESULT:", "FAIL" if failed else "ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
