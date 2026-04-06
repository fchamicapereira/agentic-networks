import logging
import threading

from tqdm import tqdm
from mininet.node import Host

from agent import AgentResult, NodeAgent
from message_bus import MessageBus
from network import Network
from agent_claude import AgentClaude
from agent_claude import MODELS as CLAUDE_MODELS
from agent_openai import AgentOpenAI
from agent_openai import MODELS as OPENAI_MODELS

MODELS = {**CLAUDE_MODELS, **OPENAI_MODELS}



def _create_agent(
    node_name: str,
    host: Host,
    bus: MessageBus,
    initial_prompt: str,
    model_key: str,
    max_iterations: int,
    max_tokens: int,
    openai_base_url: str,
    ifaces: list,
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
        )
    else:
        return AgentOpenAI(
            node_name=node_name,
            host=host,
            bus=bus,
            initial_prompt=initial_prompt,
            model=model,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
            base_url=openai_base_url,
            api_key="none",
            ifaces=ifaces,
        )


class AgenticNetwork:
    """Scheduler for a Mininet network.

    Creates one agent per host and drives them either sequentially round-robin
    (one LLM request in-flight at a time) or concurrently (each agent runs in
    its own thread).
    """

    def __init__(
        self,
        network: Network,
        initial_prompt: str,
        model_key: str,
        max_iterations: int,
        max_tokens: int,
        openai_base_url: str,
    ):
        self._logger = logging.getLogger("main")
        bus = MessageBus(list(network.hosts.keys()))
        self.agents: list[NodeAgent] = [
            _create_agent(
                node_name=name,
                host=host,
                bus=bus,
                initial_prompt=initial_prompt,
                model_key=model_key,
                max_iterations=max_iterations,
                max_tokens=max_tokens,
                openai_base_url=openai_base_url,
                ifaces=network.ifaces_per_host[name],
            )
            for name, host in network.hosts.items()
        ]

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
                desc=f"  {agent.node_name}",
                position=i,
                leave=True,
                bar_format="{desc}: {bar} {n}/{total}",
                ncols=60,
            )
            for i, agent in enumerate(self.agents)
        }

        while active:
            still_active = []
            for agent, gen in active:
                bar = bars[agent.node_name]
                bar.set_description(f"> {agent.node_name}")
                bar.refresh()
                try:
                    iteration = next(gen)

                    bar.n = iteration
                    bar.set_description(f"  {agent.node_name}")
                    bar.refresh()

                    still_active.append((agent, gen))
                except StopIteration as e:
                    results[agent.node_name] = e.value

                    bar.n = min(bar.n + 1, bar.total)  # account for final iteration if it didn't yield
                    bar.set_description(f"✓ {agent.node_name}")
                    bar.refresh()

                    self._logger.info("Agent %s finished.", agent.node_name)
            active = still_active

        tqdm.write("")  # newline after all bars
        return results

    def _run_concurrent(self) -> dict[str, AgentResult]:
        results: dict[str, AgentResult] = {}
        lock = threading.Lock()

        bars = {
            agent.node_name: tqdm(
                total=agent.max_iterations,
                desc=f"  {agent.node_name}",
                position=i,
                leave=True,
                bar_format="{desc}: {bar} {n}/{total}",
                ncols=60,
            )
            for i, agent in enumerate(self.agents)
        }

        def run_agent(agent: NodeAgent) -> None:
            bar = bars[agent.node_name]
            gen = agent.run()
            try:
                while True:
                    iteration = next(gen)
                    bar.n = iteration
                    bar.refresh()
            except StopIteration as e:
                with lock:
                    results[agent.node_name] = e.value
                bar.n = min(bar.n + 1, agent.max_iterations)
                bar.set_description(f"✓ {agent.node_name}")
                bar.refresh()
                self._logger.info("Agent %s finished.", agent.node_name)

        threads = [threading.Thread(target=run_agent, args=(agent,), daemon=True) for agent in self.agents]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        tqdm.write("")  # newline after all bars
        return results
