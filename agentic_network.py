import logging

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
            mininet_host_cmd=host.cmd,
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
            mininet_host_cmd=host.cmd,
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
    """Cooperative scheduler for a Mininet network.

    Creates one agent per host and drives them round-robin: each agent runs
    one LLM iteration at a time, yielding between iterations so others get
    a turn. Only one LLM request is in-flight at any moment.
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

    def run(self) -> dict[str, AgentResult]:
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
                    bar.n = bar.n + 1  # final iteration ran but didn't yield
                    bar.set_description(f"✓ {agent.node_name}")
                    bar.refresh()
                    agent.mininet_host.get_network_info()
                    self._logger.info("Agent %s finished.", agent.node_name)
            active = still_active

        tqdm.write("")  # newline after all bars
        return results
