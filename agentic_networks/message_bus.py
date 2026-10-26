import queue
from typing import Optional

from .events import EventLog, NO_EVENTS


class MessageBus:
    """Thread-safe per-node inbox. One shared instance passed to all agents."""

    def __init__(self, node_names: list[str], external: "list[str] | tuple[str, ...]" = (), events: EventLog = NO_EVENTS):
        # External inboxes belong to parties outside the network (e.g. the laptop's owner in the
        # KP scenarios). Nobody drains them, so they never count as messages in flight.
        self._queues: dict[str, queue.Queue] = {name: queue.Queue() for name in [*node_names, *external]}
        self._external = set(external)
        self.events = events

    def send(self, to: str, sender: str, message: str, reason: str = ""):
        if to not in self._queues:
            return f"Unknown node: {to}"
        msg_id = self.events.next_id("m")
        self.events.emit("message", sender, id=msg_id, **{"from": sender, "to": to, "text": message, "reason": reason})
        self._queues[to].put((sender, message, msg_id))
        if to in self._external:  # nobody takes it from the inbox: it reaches its reader at once
            self.events.emit("delivered", to, id=msg_id)

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
        for _, _, msg_id in msgs:
            self.events.emit("delivered", node, id=msg_id)
        return [(sender, message) for sender, message, _ in msgs]

    def in_flight(self) -> bool:
        """True if any message has been sent but not yet taken from its recipient's inbox."""
        return any(not q.empty() for name, q in self._queues.items() if name not in self._external)
