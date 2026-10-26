"""The run as the demo event stream (demo/EVENTS.md), written as it happens.

An experiment given an events file writes one JSON event per line to it, flushed at once, so
the demo server can follow a live run by reading the file as it grows. Without one, NO_EVENTS
stands in and every call does nothing, so runs behave exactly as before.

Standard library only: demo/tools/logs_to_events.py shares load_topology with the Pages build.
"""

import csv
import itertools
import json
import logging
import threading
import time

from pathlib import Path

FORMAT_VERSION = 1


def load_topology(path: "str | Path") -> dict:
    """A topology CSV as run_start's `topology`: nodes with addresses, links with relationships."""
    nodes, links = [], []
    with open(path) as f:
        for row in csv.reader(line for line in f if line.strip() and not line.startswith("#")):
            if row[0] == "node":
                nodes.append({"id": row[1], "address": row[2]})
            elif row[0] in ("prefix", "address"):
                continue
            else:
                links.append({"a": row[0], "b": row[1], "rel": row[5], "delay_ms": int(row[2])})
    return {"nodes": nodes, "links": links}


class EventLog:
    """Writes events to `path` (or nowhere, when it is None). Safe to call from agent threads."""

    def __init__(self, path: "str | Path | None" = None):
        self._file = open(path, "w", encoding="utf-8") if path else None
        self._t0 = time.monotonic()
        self._lock = threading.Lock()
        self._ids: dict[str, itertools.count] = {}
        self._ended = False

    @property
    def enabled(self) -> bool:
        return self._file is not None

    def emit(self, type_: str, node: "str | None" = None, **fields) -> None:
        if self._file is None:
            return
        with self._lock:
            event = {"t": round(time.monotonic() - self._t0, 3), "type": type_}
            if node is not None:
                event["node"] = node
            event.update(fields)
            self._file.write(json.dumps(event, ensure_ascii=False) + "\n")
            self._file.flush()

    def next_id(self, prefix: str) -> str:
        """A run-unique id: prefix1, prefix2, ..."""
        with self._lock:
            counter = self._ids.setdefault(prefix, itertools.count(1))
            return f"{prefix}{next(counter)}"

    def run_start(self, scenario: str, title: str, model: str, models: dict[str, str], topology: dict,
                  outsiders: "dict[str, str] | None" = None) -> None:
        """`outsiders`: parties outside the network, each with the agent it talks to ({"human": "User"})."""
        fields = {"outsiders": outsiders} if outsiders else {}
        self.emit("run_start", v=FORMAT_VERSION, source="live", scenario=scenario, title=title,
                  model=model, models=models, topology=topology, **fields)

    def run_end(self, reason: str) -> None:
        """The first call wins: a crash after the agents finished must not end the run twice."""
        with self._lock:
            if self._ended:
                return
            self._ended = True
        self.emit("run_end", reason=reason)

    def watch_warnings(self, node: str) -> None:
        """Emit the node's logged warnings and errors as `warning` events, as recordings do."""
        if self._file is not None:
            logging.getLogger(f"agent.{node}").addHandler(_WarningHandler(self, node))

    def close(self) -> None:
        if self._file is not None:
            with self._lock:
                self._file.close()
                self._file = None


class _WarningHandler(logging.Handler):
    def __init__(self, events: EventLog, node: str):
        super().__init__(logging.WARNING)
        self.events = events
        self.node = node

    def emit(self, record: logging.LogRecord) -> None:
        text = record.getMessage().strip()
        # A timed-out command already shows up as its exec_result (exit 124).
        if not text.startswith("Command timed out"):
            self.events.emit("warning", self.node, text=text)


NO_EVENTS = EventLog()
