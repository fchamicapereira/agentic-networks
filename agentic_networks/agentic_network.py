import logging
import threading
import time

from tqdm import tqdm
from typing import Callable, Iterable
from mininet.node import Host

from .network_agent import AGENT_TOOLS_DEFINITIONS, IDLE_DESCRIPTION_OBSERVING, AgentResult, NetworkAgent, SYSTEM_PROMPT_TEMPLATE
from .events import EventLog, NO_EVENTS, load_topology as load_event_topology
from .message_bus import MessageBus
from .network import Network
from .agent_claude import AgentClaude
from .agent_claude import MODELS as CLAUDE_MODELS
from .agent_openai import AgentOpenAI
from .agent_openai import MODELS as GPT_MODELS
from .agent_vllm import AgentVLLM
from .agent_vllm import MODELS as VLLM_MODELS
from .agent_together import AgentTogether
from .agent_together import MODELS as TOGETHER_MODELS

MODELS = {**CLAUDE_MODELS, **VLLM_MODELS, **GPT_MODELS, **TOGETHER_MODELS}

Reactor = Callable[["AgenticNetwork", int], None]

# Upper bound on how long a single concurrent step may run before we treat an agent as
# wedged. A step can legitimately take minutes (several internal completions + retries),
# so this is generous; it exists only to stop one stalled agent from freezing the whole
# experiment indefinitely. Should comfortably exceed the per-request timeout in agent_vllm.
_STEP_STALL_TIMEOUT_SECONDS = 1800.0

# Upper bound on a single agent's post-run report generation. Reports are best-effort and
# happen after the experiment's real work, so a wedged one is recorded as unavailable rather
# than allowed to hang the process. Generous for a normal report, but deliberately shorter
# than the client's full retry budget (agent_vllm) — we'd rather abandon a stuck report than
# wait out every retry, since the run's real results are already in hand.
_REPORT_STALL_TIMEOUT_SECONDS = 600.0


def _inject_reason(schema: dict) -> dict:
    schema = {**schema}
    props = {
        **schema.get("properties", {}),
        "reason": {
            "type": "string",
            "description": "Concise explanation of why you are taking this action right now",
        },
    }
    req = list(schema.get("required", []))
    if "reason" not in req:
        req.append("reason")
    return {**schema, "properties": props, "required": req}


def system_prompt_for(node_name: str, ifaces: list, initial_prompt: str) -> str:
    """A node's system prompt: the harness template, with its connections and its scenario prompt."""
    connections = "\n".join(f"  - {iface.iface}: connected to {iface.peer} (your IP: {iface.ip}, peer IP: {iface.peer_ip})" for iface in ifaces)
    return SYSTEM_PROMPT_TEMPLATE.format(
        node_name=node_name,
        connections=connections,
        initial_prompt=initial_prompt,
    )


def describe_run(
    path: str,
    scenario: str,
    title: str,
    network: Network,
    topology_file: str,
    initial_prompts: str | dict[str, str],
    start_waiting: Iterable[str] = (),
    external_contacts: "dict[str, list[str]] | None" = None,
) -> None:
    """Write what a run would start with, as the demo's event stream (demo/EVENTS.md), and nothing else.

    run_start, each agent's system prompt (as AgenticNetwork builds it), and which agents start
    idle; the network is not started and no model is called. Experiments' --describe uses this so
    the demo can show a scenario before running it. `network` only needs to be constructed.
    """
    events = EventLog(path)
    events.run_start(scenario, title, "", {}, load_event_topology(topology_file),
                     outsiders={c: agent for agent, cs in (external_contacts or {}).items() for c in cs})
    start_waiting = set(start_waiting)
    for name, ifaces in network.ifaces_per_host.items():
        prompt = initial_prompts[name] if isinstance(initial_prompts, dict) else initial_prompts
        events.emit("prompt", name, text=system_prompt_for(name, ifaces, prompt).strip())
        if name in start_waiting:
            events.emit("state", name, state="dormant")
    events.close()


def _create_network_agent(
    node_name: str,
    host: Host,
    bus: MessageBus,
    initial_prompt: str,
    model_key: str,
    max_iterations: int,
    max_tokens: int,
    vllm_host: str,
    vllm_port: int,
    ifaces: list,
    window_size: int,
    extra_tools: list[dict] | None = None,
    context_fn: "Callable[[], str] | None" = None,
    events: EventLog = NO_EVENTS,
) -> NetworkAgent:
    model = MODELS[model_key]
    system_prompt = system_prompt_for(node_name, ifaces, initial_prompt)

    extra_defs = [
        {
            "name": t["name"],
            "description": t["description"],
            "schema": _inject_reason(t["schema"]),
        }
        for t in (extra_tools or [])
    ]

    base_defs = AGENT_TOOLS_DEFINITIONS
    if context_fn:
        base_defs = [{**d, "description": IDLE_DESCRIPTION_OBSERVING} if d["name"] == "idle" else d for d in base_defs]
    tool_defs = base_defs + extra_defs

    if model_key in CLAUDE_MODELS:
        llm_agent = AgentClaude(model, node_name, system_prompt, max_tokens, tool_defs, window_size)
    elif model_key in GPT_MODELS:
        llm_agent = AgentOpenAI(model, node_name, system_prompt, max_tokens, tool_defs, window_size)
    elif model_key in TOGETHER_MODELS:
        llm_agent = AgentTogether(model, node_name, system_prompt, max_tokens, tool_defs, window_size)
    elif model_key in VLLM_MODELS:
        llm_agent = AgentVLLM(model, node_name, vllm_host, vllm_port, system_prompt, max_tokens, tool_defs, window_size)
    else:
        raise ValueError(f"Unknown model key: {model_key!r}")

    return NetworkAgent(
        node_name=node_name,
        host=host,
        bus=bus,
        agent=llm_agent,
        ifaces=ifaces,
        max_iterations=max_iterations,
        context_fn=context_fn,
        extra_tools=extra_tools,
        events=events,
    )


class AgenticNetwork:
    """Scheduler for a Mininet network.

    Creates one NetworkAgent per host and drives them either sequentially
    round-robin or concurrently (each agent in its own thread).

    ``reactors`` is an optional list of callables with signature
    ``(net: AgenticNetwork, iteration: int) -> None``.  They are called on
    every scheduler tick and can inspect or mutate network state.

    ``initial_prompts`` may be a single string (shared by all agents) or a
    dict mapping node names to individual prompt strings.

    ``agent_models`` optionally runs some nodes on a model other than
    ``model_key`` ({node: model_key}), e.g. a fixed attacker across runs.

    ``events`` receives the run as the demo event stream (demo/EVENTS.md); the
    caller emits run_start before creating the network.
    """

    REACTOR_POLL_INTERVAL_S = 0.5

    def __init__(
        self,
        network: Network,
        initial_prompts: str | dict[str, str],
        model_key: str,
        max_iterations: int,
        max_tokens: int,
        vllm_host: str,
        vllm_port: int,
        window_size: int,
        reactors: list[Reactor] = [],
        post_reactors: list[Reactor] = [],
        extra_tools: list[dict] | None = None,
        context_fns: "dict[str, Callable[[], str]] | None" = None,
        start_waiting: Iterable[str] = (),
        external_contacts: "dict[str, list[str]] | None" = None,
        agent_models: "dict[str, str] | None" = None,
        events: EventLog = NO_EVENTS,
    ):
        self.logger = logging.getLogger("main")
        self.network = network
        self.events = events
        # external_contacts maps an agent to parties outside the network it may message
        # (e.g. {"User": ["human"]}: only the laptop agent can talk to its owner).
        external_contacts = external_contacts or {}
        self.message_bus = MessageBus(
            list(network.hosts.keys()), external=sorted({c for cs in external_contacts.values() for c in cs}), events=events
        )
        agent_models = agent_models or {}
        unknown = set(agent_models) - set(network.hosts)
        if unknown:
            raise ValueError(f"agent_models names unknown nodes: {sorted(unknown)}")
        self.reactors: list[Reactor] = reactors
        self.post_reactors: list[Reactor] = post_reactors
        self.agents: list[NetworkAgent] = [
            _create_network_agent(
                node_name=name,
                host=host,
                bus=self.message_bus,
                initial_prompt=(initial_prompts[name] if isinstance(initial_prompts, dict) else initial_prompts),
                model_key=agent_models.get(name, model_key),
                max_iterations=max_iterations,
                max_tokens=max_tokens,
                vllm_host=vllm_host,
                vllm_port=vllm_port,
                ifaces=network.ifaces_per_host[name],
                window_size=window_size,
                extra_tools=extra_tools,
                context_fn=context_fns.get(name) if context_fns else None,
                events=events,
            )
            for name, host in network.hosts.items()
        ]

        for agent in self.agents:
            agent.add_contacts(external_contacts.get(agent.node_name, []))

        # Agents that start idle: they take no turn until a message reaches them.
        start_waiting = set(start_waiting)
        for agent in self.agents:
            agent.waiting = agent.node_name in start_waiting

        for agent in self.agents:
            events.emit("prompt", agent.node_name, text=agent.agent.system_prompt.strip())
            if agent.waiting:
                events.emit("state", agent.node_name, state="dormant")
            events.watch_warnings(agent.node_name)
        self._routes: dict[str, str] = {}
        self._emit_route_changes()

        self._stopped: set[str] = set()

    def send_message(self, to: str, sender: str, message: str) -> None:
        valid = {agent.node_name for agent in self.agents}
        if to not in valid:
            raise ValueError(f"Unknown agent '{to}'. Valid agents: {sorted(valid)}")
        self.message_bus.send(to, sender, message)

    def _emit_route_changes(self) -> None:
        """Emit a `routes` event for every node whose routing table changed since the last call."""
        if not self.events.enabled:
            return
        for name, host in self.network.hosts.items():
            table = host.cmd("ip route show").replace("\r", "").strip()
            if table != self._routes.get(name):
                self._routes[name] = table
                self.events.emit("routes", name, table=table)

    def stop_agent(self, node_name: str) -> None:
        self._stopped.add(node_name)

    def gather_reports(self) -> dict[str, str]:
        reports: dict[str, str] = {}
        lock = threading.Lock()

        def fetch(agent: NetworkAgent) -> None:
            try:
                text = agent.request_report()
            except Exception as exc:
                self.logger.error("Failed to get report from %s: %s", agent.node_name, exc)
                text = f"(report unavailable: {exc})"
            with lock:
                reports[agent.node_name] = text
            self.events.emit("report", agent.node_name, text=text)

        # daemon=True so a wedged report request can't block interpreter exit. Reports are
        # best-effort and run *after* the experiment's real work is done, so a stalled one
        # must never freeze the whole process — we bound the wait and salvage what's ready.
        threads = {
            agent.node_name: threading.Thread(target=fetch, args=(agent,), daemon=True)
            for agent in self.agents
            if agent.node_name not in self._stopped
        }

        for t in threads.values():
            t.start()

        deadline = time.monotonic() + _REPORT_STALL_TIMEOUT_SECONDS
        for t in threads.values():
            t.join(timeout=max(0.0, deadline - time.monotonic()))

        for name, t in threads.items():
            if t.is_alive():
                self.logger.error(
                    "Report from %s did not complete within %.0fs; recording it as unavailable.",
                    name, _REPORT_STALL_TIMEOUT_SECONDS,
                )
                with lock:
                    reports.setdefault(name, "(report unavailable: timed out)")

        return reports

    def run(self, concurrent: bool = True, end_run: bool = True) -> dict[str, AgentResult]:
        """Run the agents. `end_run=False` leaves the event stream's run_end to the caller (with
        `self.end_reason`), for an experiment that still measures something afterwards."""
        # Set to "all_dormant" by the runner when it stops the run because nothing is left to do.
        self._end_reason = "max_iterations"
        try:
            results = self._run_concurrent() if concurrent else self._run_sequential_round_robin()
        except KeyboardInterrupt:  # stopped from outside, e.g. the demo server's Stop run
            self.events.run_end("stopped")
            raise
        except BaseException:
            self.events.run_end("error")
            raise
        if end_run:
            self.events.run_end(self._end_reason)
        return results

    @property
    def end_reason(self) -> str:
        return self._end_reason

    def _run_sequential_round_robin(self) -> dict[str, AgentResult]:
        active = [(agent, agent.run()) for agent in self.agents]
        results: dict[str, AgentResult] = {}

        bars = {
            agent.node_name: tqdm(
                total=agent.max_iterations,
                desc=f"  {agent.node_name}: ",
                position=i,
                leave=True,
                bar_format="{desc}{bar} {n}/{total}",
                # See _run_concurrent: dynamic width clears full lines, avoiding log-tail artifacts.
                dynamic_ncols=True,
            )
            for i, agent in enumerate(self.agents)
        }

        global_iter = 0
        while active:
            for reactor in self.reactors:
                reactor(self, global_iter)

            for agent, gen in active:
                if agent.node_name in self._stopped:
                    results[agent.node_name] = AgentResult(success=False, message="Node stopped by reactor")
                    bars[agent.node_name].set_description(f"✗ {agent.node_name}")
                    bars[agent.node_name].refresh()
                    self.logger.info("Agent %s stopped.", agent.node_name)

            still_active = []
            for agent, gen in active:
                if agent.node_name in self._stopped:
                    continue
                bar = bars[agent.node_name]
                bar.set_description(f"> {agent.node_name}")
                bar.refresh()
                try:
                    iteration = next(gen)
                    bar.n = iteration
                    bar.set_description(f"✓ {agent.node_name}" if agent.waiting else f"  {agent.node_name}")
                    bar.refresh()
                    still_active.append((agent, gen))
                except StopIteration as e:
                    results[agent.node_name] = e.value
                    bar.n = min(bar.n + 1, bar.total)
                    bar.set_description(f"✓ {agent.node_name}")
                    bar.refresh()
                    self.logger.info("Agent %s finished.", agent.node_name)
            active = still_active

            for reactor in self.post_reactors:
                reactor(self, global_iter)
            self._emit_route_changes()

            if active and all(agent.waiting for agent, _ in active) and not self.message_bus.in_flight():
                self.logger.info("All agents are idle and no messages are in flight. Stopping experiment.")
                self._end_reason = "all_dormant"
                for agent, gen in active:
                    results[agent.node_name] = agent.result()
                    bars[agent.node_name].set_description(f"✓ {agent.node_name}")
                    bars[agent.node_name].refresh()
                    gen.close()
                active = []

            global_iter += 1

        tqdm.write("")
        return results

    def _run_concurrent(self) -> dict[str, AgentResult]:
        results: dict[str, AgentResult] = {}
        active = [(agent, agent.run()) for agent in self.agents]

        bars = {
            agent.node_name: tqdm(
                total=agent.max_iterations,
                desc=f"  {agent.node_name}: ",
                position=i,
                leave=True,
                bar_format="{desc}{bar} {n}/{total}",
                # dynamic_ncols (vs a fixed ncols) lets each refresh clear the full terminal
                # width, so a redraw never leaves a tail of a longer log line beneath the bar.
                dynamic_ncols=True,
            )
            for i, agent in enumerate(self.agents)
        }

        step = 0
        while active:
            for reactor in self.reactors:
                reactor(self, step)

            for agent, gen in active:
                if agent.node_name in self._stopped:
                    results[agent.node_name] = AgentResult(success=False, message="Node stopped by reactor")
                    bars[agent.node_name].set_description(f"✗ {agent.node_name}")
                    bars[agent.node_name].refresh()
                    self.logger.info("Agent %s stopped.", agent.node_name)
            active = [(agent, gen) for agent, gen in active if agent.node_name not in self._stopped]
            if not active:
                break

            step_results: dict[str, tuple] = {}
            step_lock = threading.Lock()

            # Worker threads never touch the bars: concurrent set_description/refresh from
            # multiple threads (racing with tqdm.write from log records) corrupts the display.
            # They only record their result; the main thread owns all bar updates. Logging via
            # the TqdmHandler is fine here — tqdm.write is internally lock-guarded.
            def run_step(agent: NetworkAgent, gen) -> None:
                try:
                    iteration = next(gen)
                    with step_lock:
                        step_results[agent.node_name] = ("continue", iteration, None)
                except StopIteration as e:
                    with step_lock:
                        step_results[agent.node_name] = ("done", None, e.value)
                except Exception as exc:
                    self.logger.error("Agent %s crashed: %s", agent.node_name, exc, exc_info=True)
                    with step_lock:
                        step_results[agent.node_name] = ("error", None, exc)

            for agent, gen in active:
                bars[agent.node_name].set_description(f"> {agent.node_name}")
                bars[agent.node_name].refresh()

            # daemon=True so a wedged thread (stalled LLM request) cannot block interpreter
            # exit once we decide to abort the run below.
            threads = {
                agent.node_name: threading.Thread(target=run_step, args=(agent, gen), daemon=True)
                for agent, gen in active
            }

            for t in threads.values():
                t.start()

            deadline = time.monotonic() + _STEP_STALL_TIMEOUT_SECONDS
            for t in threads.values():
                t.join(timeout=max(0.0, deadline - time.monotonic()))

            stalled = [name for name, t in threads.items() if t.is_alive()]
            if stalled:
                for name in stalled:
                    bars[name].set_description(f"✗ {name}")
                    bars[name].refresh()
                    results[name] = AgentResult(success=False, message="Agent stalled (step exceeded timeout)")
                self.logger.error(
                    "Step %d exceeded %.0fs; agent(s) %s appear wedged (likely a stalled LLM request). Aborting run.",
                    step, _STEP_STALL_TIMEOUT_SECONDS, ", ".join(stalled),
                )
                raise RuntimeError(f"Agent(s) stalled and did not complete a step: {', '.join(stalled)}")

            still_active = []
            errors = []
            for agent, gen in active:
                bar = bars[agent.node_name]
                status, iteration, value = step_results[agent.node_name]
                if status == "continue":
                    bar.n = iteration
                    bar.set_description(f"✓ {agent.node_name}" if agent.waiting else f"  {agent.node_name}")
                    bar.refresh()
                    still_active.append((agent, gen))
                elif status == "done":
                    bar.n = min(bar.n + 1, agent.max_iterations)
                    bar.set_description(f"✓ {agent.node_name}")
                    bar.refresh()
                    results[agent.node_name] = value
                    self.logger.info("Agent %s finished.", agent.node_name)
                elif status == "error":
                    bar.set_description(f"✗ {agent.node_name}")
                    bar.refresh()
                    results[agent.node_name] = AgentResult(success=False, message=f"Agent crashed: {value}")
                    errors.append(value)

            if errors:
                raise RuntimeError("An agent crashed — see logs above for details.")

            for reactor in self.post_reactors:
                reactor(self, step)
            self._emit_route_changes()

            active = still_active

            if active and all(agent.waiting for agent, _ in active) and not self.message_bus.in_flight():
                self.logger.info("All agents are idle and no messages are in flight. Stopping experiment.")
                self._end_reason = "all_dormant"
                for agent, gen in active:
                    results[agent.node_name] = agent.result()
                    bars[agent.node_name].set_description(f"✓ {agent.node_name}")
                    bars[agent.node_name].refresh()
                    gen.close()
                active = []

            step += 1

        tqdm.write("")
        return results
