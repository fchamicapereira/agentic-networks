import queue


class MessageBus:
    """Thread-safe per-node inbox. One shared instance passed to all agents."""

    def __init__(self, node_names: list[str]):
        self._queues: dict[str, queue.Queue] = {name: queue.Queue() for name in node_names}

    def send(self, to: str, sender: str, message: str):
        if to not in self._queues:
            return f"Unknown node: {to}"
        self._queues[to].put((sender, message))

    def drain(self, node: str) -> list[tuple[str, str]]:
        """Return and clear all pending messages for node as [(from, message), ...]."""
        msgs = []
        q = self._queues[node]
        while True:
            try:
                msgs.append(q.get_nowait())
            except queue.Empty:
                break
        return msgs
