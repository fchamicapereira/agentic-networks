import queue
from typing import Optional


class MessageBus:
    """Thread-safe per-node inbox. One shared instance passed to all agents."""

    def __init__(self, node_names: list[str]):
        self._queues: dict[str, queue.Queue] = {name: queue.Queue() for name in node_names}

    def send(self, to: str, sender: str, message: str):
        if to not in self._queues:
            return f"Unknown node: {to}"
        self._queues[to].put((sender, message))

    def drain(self, node: str, block: bool = False, timeout: Optional[float] = None) -> list[tuple[str, str]]:
        """Return all pending messages for node as [(sender, message), ...], in FIFO order.

        If block=True, wait up to timeout seconds for the first message to arrive; any further
        messages already queued are then collected without blocking.
        """
        msgs = []
        q = self._queues[node]
        try:
            msgs.append(q.get(block=block, timeout=timeout))
        except queue.Empty:
            return msgs
        while True:
            try:
                msgs.append(q.get_nowait())
            except queue.Empty:
                break
        return msgs
