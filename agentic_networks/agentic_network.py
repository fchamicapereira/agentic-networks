import logging
import threading

from tqdm import tqdm
from typing import Callable
from mininet.node import Host

from .agent import AgentResult, NodeAgent
from .message_bus import MessageBus
from .network import Network
from .agent_claude import AgentClaude
from .agent_claude import MODELS as CLAUDE_MODELS
from .agent_vllm import AgentVLLM
from .agent_vllm import MODELS as VLLM_MODELS
from .agent_openai import AgentOpenAI
from .agent_openai import MODELS as GPT_MODELS

MODELS = {**CLAUDE_MODELS, **VLLM_MODELS, **GPT_MODELS}

Reactor = Callable[["AgenticNetwork", int], None]


def _create_agent(
    node_name: str,
    host: Host,
    bus: MessageBus,
    initial_prompt: str,
    model_key: str,
    max_iterations: int,
    max_tokens: int,
    vllm_base_url: str,
    ifaces: list,
    window_size: int,
    extra_tools: list[dict] | None = None,
    context_fn: "Callable[[], str] | None" = None,
) -> NodeAgent:
    model = MODELS[model_key]
    if model_key in CLAUDE_MODELS:
        return AgentClaude(
            node_name=node_name,
            host=host,
            bus=bus,
            initial_prompt=initial_prompt,
            model=model,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
            ifaces=ifaces,
            window_size=window_size,
            extra_tools=extra_tools,
            context_fn=context_fn,
        )
    elif model_key in GPT_MODELS:
        return AgentOpenAI(
            node_name=node_name,
            host=host,
            bus=bus,
            initial_prompt=initial_prompt,
            model=model,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
            ifaces=ifaces,
            window_size=window_size,
            extra_tools=extra_tools,
            context_fn=context_fn,
        )
    else:
        return AgentVLLM(
            node_name=node_name,
            host=host,
            bus=bus,
            initial_prompt=initial_prompt,
            model=model,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
            base_url=vllm_base_url,
            api_key="none",
            ifaces=ifaces,
            window_size=window_size,
            extra_tools=extra_tools,
            context_fn=context_fn,
        )


class AgenticNetwork:
    """Scheduler for a Mininet network.

    Creates one agent per host and drives them either sequentially round-robin
    (one LLM request in-flight at a time) or concurrently (each agent runs in
    its own thread).

    ``reactors`` is an optional list of callables with signature
    ``(net: AgenticNetwork, iteration: int) -> None``.  They are called on
    every scheduler tick (after each round in sequential mode; every
    REACTOR_POLL_INTERVAL_S seconds in concurrent mode) and can inspect or
    mutate network state — e.g. crash a node, inject messages, etc.

    ``initial_prompts`` may be a single string (shared by all agents) or a
    dict mapping node names to individual prompt strings.
    """

    REACTOR_POLL_INTERVAL_S = 0.5

    def __init__(
        self,
        network: Network,
        initial_prompts: str | dict[str, str],
        model_key: str,
        max_iterations: int,
        max_tokens: int,
        vllm_base_url: str,
        window_size: int,
        reactors: list[Reactor] = [],
        post_reactors: list[Reactor] = [],
        extra_tools: list[dict] | None = None,
        context_fns: "dict[str, Callable[[], str]] | None" = None,
    ):
        self.logger = logging.getLogger("main")
        self.network = network
        self.bus = MessageBus(list(network.hosts.keys()))
        self.reactors: list[Reactor] = reactors
        self.post_reactors: list[Reactor] = post_reactors
        self._stopped: set[str] = set()
        self.agents: list[NodeAgent] = [
            _create_agent(
                node_name=name,
                host=host,
                bus=self.bus,
                initial_prompt=(initial_prompts[name] if isinstance(initial_prompts, dict) else initial_prompts),
                model_key=model_key,
                max_iterations=max_iterations,
                max_tokens=max_tokens,
                vllm_base_url=vllm_base_url,
                ifaces=network.ifaces_per_host[name],
                window_size=window_size,
                extra_tools=extra_tools,
                context_fn=context_fns.get(name) if context_fns else None,
            )
            for name, host in network.hosts.items()
        ]

    def stop_agent(self, node_name: str) -> None:
        """Mark an agent as stopped; it will be excluded from all future steps."""
        self._stopped.add(node_name)

    def gather_reports(self) -> dict[str, str]:
        """Ask each non-stopped agent to write a report. Returns {node_name: report_text}."""
        reports: dict[str, str] = {}
        lock = threading.Lock()

        def fetch(agent: NodeAgent) -> None:
            try:
                text = agent.request_report()
            except Exception as exc:
                self.logger.error("Failed to get report from %s: %s", agent.node_name, exc)
                text = f"(report unavailable: {exc})"
            with lock:
                reports[agent.node_name] = text

        threads = [threading.Thread(target=fetch, args=(agent,)) for agent in self.agents if agent.node_name not in self._stopped]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return reports

    def run(self, concurrent: bool = True) -> dict[str, AgentResult]:
        if concurrent:
            return self._run_concurrent()
        return self._run_sequential_round_robin()

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
                ncols=60,
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
                    bar.set_description(f"✓ {agent.node_name}" if agent.is_done else f"  {agent.node_name}")
                    bar.refresh()

                    still_active.append((agent, gen))
                except StopIteration as e:
                    results[agent.node_name] = e.value

                    bar.n = min(bar.n + 1, bar.total)  # account for final iteration if it didn't yield
                    bar.set_description(f"✓ {agent.node_name}")
                    bar.refresh()

                    self.logger.info("Agent %s finished.", agent.node_name)
            active = still_active

            for reactor in self.post_reactors:
                reactor(self, global_iter)

            if active and all(agent.is_done for agent, _ in active):
                self.logger.info("All agents have terminated. Stopping experiment early.")
                for agent, gen in active:
                    results[agent.node_name] = agent._final_report
                    bars[agent.node_name].set_description(f"✓ {agent.node_name}")
                    bars[agent.node_name].refresh()
                    gen.close()
                active = []

            global_iter += 1

        tqdm.write("")  # newline after all bars
        return results

    def _run_concurrent(self) -> dict[str, AgentResult]:
        """Step-based concurrent execution.

        On every step all active agents run exactly one iteration in parallel.
        Once all threads for that step have joined, reactors are called, then
        the next step begins.  This keeps reactor invocations fully synchronous
        and deterministic with respect to agent progress.
        """
        results: dict[str, AgentResult] = {}
        active = [(agent, agent.run()) for agent in self.agents]

        bars = {
            agent.node_name: tqdm(
                total=agent.max_iterations,
                desc=f"  {agent.node_name}: ",
                position=i,
                leave=True,
                bar_format="{desc}{bar} {n}/{total}",
                ncols=60,
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

            def run_step(agent: NodeAgent, gen) -> None:
                bar = bars[agent.node_name]
                bar.set_description(f"> {agent.node_name}")
                bar.refresh()
                try:
                    iteration = next(gen)
                    bar.n = iteration
                    bar.set_description(f"  {agent.node_name}")
                    bar.refresh()
                    with step_lock:
                        step_results[agent.node_name] = ("continue", iteration, None)
                except StopIteration as e:
                    bar.n = min(bar.n + 1, agent.max_iterations)
                    bar.set_description(f"✓ {agent.node_name}")
                    bar.refresh()
                    with step_lock:
                        step_results[agent.node_name] = ("done", None, e.value)
                except Exception as exc:
                    bar.set_description(f"✗ {agent.node_name}")
                    bar.refresh()
                    self.logger.error("Agent %s crashed: %s", agent.node_name, exc, exc_info=True)
                    with step_lock:
                        step_results[agent.node_name] = ("error", None, exc)

            threads = [threading.Thread(target=run_step, args=(agent, gen)) for agent, gen in active]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            still_active = []
            errors = []
            for agent, gen in active:
                status, iteration, value = step_results[agent.node_name]
                if status == "continue":
                    bars[agent.node_name].set_description(f"✓ {agent.node_name}" if agent.is_done else f"  {agent.node_name}")
                    bars[agent.node_name].refresh()
                    still_active.append((agent, gen))
                elif status == "done":
                    results[agent.node_name] = value
                    self.logger.info("Agent %s finished.", agent.node_name)
                elif status == "error":
                    results[agent.node_name] = AgentResult(success=False, message=f"Agent crashed: {value}")
                    errors.append(value)

            if errors:
                raise RuntimeError("An agent crashed — see logs above for details.")

            for reactor in self.post_reactors:
                reactor(self, step)

            active = still_active

            if active and all(agent.is_done for agent, _ in active):
                self.logger.info("All agents have terminated. Stopping experiment early.")
                for agent, gen in active:
                    results[agent.node_name] = agent._final_report
                    bars[agent.node_name].set_description(f"✓ {agent.node_name}")
                    bars[agent.node_name].refresh()
                    gen.close()
                active = []

            step += 1

        tqdm.write("")  # newline after all bars
        return results
