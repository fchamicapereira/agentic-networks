#!/usr/bin/env python3
"""Render agentic-network experiment logs as a self-contained, interactive HTML timeline.

The N input log files are expected to come from the same experiment (one per node). Time flows
downward; iterations ("epochs") are the synchronization primitive across hosts, and within each
epoch events are ordered globally by timestamp so vertical position reflects real ordering.

Usage:
    python -m agentic_networks.visualize_logs LOG1 LOG2 ... [-o OUT.html] [--open]

Programmatic use:
    from agentic_networks.visualize_logs import render_logs, parse_logs
    html = render_logs(["a.log", "b.log"], output_path="out.html")
"""

import argparse
import json
import os
import re
import sys
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path

from .paths import ASSETS_DIR

# The HTML/CSS/JS shell lives in assets/ to keep this module readable. It is inlined into every
# rendered file, so the *output* stays fully self-contained even though the template is external.
_TEMPLATE_PATH = ASSETS_DIR / "timeline_template.html"
_DATA_PLACEHOLDER = "__DATA_JSON__"

# A log record starts with "HH:MM:SS  LEVEL  ...". Lines without this header are continuation
# lines belonging to the preceding record (multi-line assistant content, command output, etc.).
_HEADER_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\s+(\w+)\s+(.*)$")
_ITER_RE = re.compile(r"^--- Iteration (\d+)/(\d+) ---")
_MSG_RE = re.compile(r"^\[msg ([→←]) ([^\]]+)\] (.*)", re.S)
_CMD_OUT_RE = re.compile(r"^Command output \(exit (-?\d+)\):?\s*(.*)", re.S)

_REPORT_LEVELS = {"INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass
class Event:
    host: str
    ts: str  # "HH:MM:SS" for display
    ts_sec: int  # seconds since midnight (monotonic within a file) for sorting
    seq: int  # line order within the source file (tie-breaker)
    epoch: int
    kind: str  # assistant | command | msg_sent | msg_recv | idle | system | status | warning | log
    title: str = ""
    body: str = ""
    reason: str = ""
    exit_code: "int | None" = None
    peer: str = ""
    direction: str = ""  # "out" | "in" for messages
    link_id: "int | None" = None
    id: str = ""


@dataclass
class Timeline:
    label: str
    hosts: list[str]
    epochs: list[dict] = field(default_factory=list)  # {epoch, label, ts_start, ts_end, events:[Event]}
    links: list[dict] = field(default_factory=list)  # {id, send_id, recv_id, from, to}


# --------------------------------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------------------------------

def _host_label_and_prefix(files: list[Path]) -> tuple[list[str], str]:
    """Derive per-file host names and a shared experiment label.

    All files from one experiment share the run-stem prefix and differ only by the trailing host
    segment, so the longest common prefix (trimmed back to the last '-') isolates the host name.
    """
    stems = [f.stem for f in files]
    prefix = os.path.commonprefix(stems)
    if len(files) > 1 and "-" in prefix:
        prefix = prefix[: prefix.rfind("-") + 1]
    elif len(files) == 1:
        prefix = stems[0][: stems[0].rfind("-") + 1] if "-" in stems[0] else ""
    hosts = [s[len(prefix):] or s for s in stems]
    label = prefix.rstrip("-") or "experiment"
    return hosts, label


def _raw_records(text: str) -> list[tuple[str, int, str]]:
    """Split a log into (level, ts_sec, message) records, joining continuation lines."""
    records: list[tuple[str, int, list[str]]] = []
    prev_sec = -1
    day_offset = 0
    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            hh, mm, ss, level, msg = m.groups()
            sec = int(hh) * 3600 + int(mm) * 60 + int(ss)
            if sec < prev_sec:  # crossed midnight within the run
                day_offset += 86400
            prev_sec = sec
            records.append((level, sec + day_offset, [msg]))
        elif records:
            records[-1][2].append(line)
    return [(lvl, sec, "\n".join(parts)) for lvl, sec, parts in records]


def _classify(host: str, level: str, ts_sec: int, seq: int, epoch: int, msg: str) -> "Event | None":
    """Map one raw record to an Event (or None to drop it)."""
    ts = f"{ts_sec % 86400 // 3600:02d}:{ts_sec % 3600 // 60:02d}:{ts_sec % 60:02d}"

    def mk(kind: str, title: str = "", body: str = "", exit_code: "int | None" = None,
           peer: str = "", direction: str = "") -> Event:
        return Event(host=host, ts=ts, ts_sec=ts_sec, seq=seq, epoch=epoch, kind=kind,
                     title=title, body=body, exit_code=exit_code, peer=peer, direction=direction)

    if msg.startswith("[assistant] "):
        return mk("assistant", title="Reasoning", body=msg[len("[assistant] "):].strip())
    if msg.startswith("[reason] "):
        return mk("reason", body=msg[len("[reason] "):].strip())
    mm = _MSG_RE.match(msg)
    if mm:
        arrow, peer, content = mm.groups()
        out = arrow == "→"
        return mk("msg_sent" if out else "msg_recv",
                  title=f"{'→' if out else '←'} {peer}", body=content.strip(),
                  peer=peer.strip(), direction="out" if out else "in")
    if msg.startswith("Executing command:"):
        return mk("command", title=msg[len("Executing command:"):].strip())
    co = _CMD_OUT_RE.match(msg)
    if co:
        code, out = co.groups()
        body = "(empty)" if out.strip() in ("", "(empty)") else out.strip()
        return mk("command_output", body=body, exit_code=int(code))
    if msg.startswith("Idle"):
        return mk("idle", title="Idle")
    if msg.startswith("System prompt:"):
        return mk("system", title="System prompt", body=msg[len("System prompt:"):].strip())
    if "AGENT TERMINATED" in msg:
        return mk("status", title="Agent terminated", body=msg.split("===")[-1].strip())
    if "AGENT REACTIVATED" in msg:
        return mk("status", title="Agent reactivated", body=msg.split("===")[-1].strip())
    if level in ("WARNING", "ERROR", "CRITICAL"):
        return mk("warning", title=level.title(), body=msg.strip())
    return mk("log", body=msg.strip())


def _parse_file(path: Path, host: str) -> list[Event]:
    text = path.read_text(errors="replace")
    events: list[Event] = []
    epoch = 0
    for seq, (level, ts_sec, msg) in enumerate(_raw_records(text)):
        if level not in _REPORT_LEVELS:
            continue  # drop DEBUG so debug-mode logs render cleanly
        it = _ITER_RE.match(msg)
        if it:
            epoch = int(it.group(1))
            continue  # iteration markers become epoch bands, not cards
        ev = _classify(host, level, ts_sec, seq, epoch, msg)
        if ev is not None:
            events.append(ev)
    return _group(events)


def _group(events: list[Event]) -> list[Event]:
    """Fold each [reason] into the action it precedes, and each command output into its command."""
    out: list[Event] = []
    pending_reason = ""
    i = 0
    while i < len(events):
        e = events[i]
        if e.kind == "reason":
            pending_reason = e.body
            i += 1
            continue
        if e.kind == "command":
            e.reason = pending_reason
            pending_reason = ""
            if i + 1 < len(events) and events[i + 1].kind == "command_output":
                nxt = events[i + 1]
                e.body = nxt.body
                e.exit_code = nxt.exit_code
                i += 1
            out.append(e)
        elif e.kind == "command_output":  # output with no preceding command (rare) — keep standalone
            e.kind = "log"
            out.append(e)
        else:
            if e.kind in ("msg_sent", "idle", "status"):
                e.reason = pending_reason
                pending_reason = ""
            out.append(e)
        i += 1
    return out


def _correlate(events: list[Event]) -> list[dict]:
    """Match each sent message to its received counterpart by (sender, recipient, content)."""
    links: list[dict] = []
    recvs = [e for e in events if e.kind == "msg_recv"]
    used: set[str] = set()
    for snd in sorted((e for e in events if e.kind == "msg_sent"), key=lambda e: (e.ts_sec, e.seq)):
        for rcv in recvs:
            if rcv.id in used:
                continue
            if (rcv.peer == snd.host and rcv.host == snd.peer
                    and rcv.body.strip() == snd.body.strip() and rcv.ts_sec >= snd.ts_sec):
                lid = len(links)
                snd.link_id = lid
                rcv.link_id = lid
                used.add(rcv.id)
                links.append({"id": lid, "send_id": snd.id, "recv_id": rcv.id, "from": snd.host, "to": rcv.host})
                break
    return links


def parse_logs(files: list) -> Timeline:
    """Parse N experiment log files into a correlated Timeline. Exported for programmatic use."""
    paths = [Path(f) for f in files]
    if not paths:
        raise ValueError("no log files provided")
    hosts, label = _host_label_and_prefix(paths)
    host_index = {h: i for i, h in enumerate(hosts)}

    all_events: list[Event] = []
    for path, host in zip(paths, hosts):
        for ev in _parse_file(path, host):
            ev.id = f"{host}__{ev.seq}"
            all_events.append(ev)

    links = _correlate(all_events)

    epochs_map: dict[int, list[Event]] = {}
    for ev in all_events:
        epochs_map.setdefault(ev.epoch, []).append(ev)

    epochs: list[dict] = []
    for epoch in sorted(epochs_map):
        evs = sorted(epochs_map[epoch], key=lambda e: (e.ts_sec, host_index.get(e.host, 0), e.seq))
        epochs.append({
            "epoch": epoch,
            "label": "Setup" if epoch == 0 else f"Iteration {epoch}",
            "ts_start": evs[0].ts if evs else "",
            "ts_end": evs[-1].ts if evs else "",
            "events": evs,
        })
    return Timeline(label=label, hosts=hosts, epochs=epochs, links=links)


# --------------------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------------------

def _timeline_to_data(tl: Timeline) -> dict:
    host_index = {h: i for i, h in enumerate(tl.hosts)}
    epochs = []
    for ep in tl.epochs:
        # Events in the same second are treated as concurrent: they share a row so they line up
        # horizontally across host columns (sub-second ordering is ignored). Multiple events on
        # the same host within one second stack inside that single cell.
        row_of = {s: i for i, s in enumerate(sorted({e.ts_sec for e in ep["events"]}))}
        rows = []
        for e in ep["events"]:
            rows.append({
                "id": e.id, "host": e.host, "col": host_index[e.host], "row": row_of[e.ts_sec],
                "ts": e.ts, "kind": e.kind, "title": e.title, "body": e.body,
                "reason": e.reason, "exit": e.exit_code, "peer": e.peer,
                "dir": e.direction, "link": e.link_id,
            })
        epochs.append({"epoch": ep["epoch"], "label": ep["label"],
                       "ts_start": ep["ts_start"], "ts_end": ep["ts_end"], "events": rows})
    return {"label": tl.label, "hosts": tl.hosts, "epochs": epochs, "links": tl.links}


def render_logs(files: list, output_path=None) -> str:
    """Render the given log files to a self-contained HTML string.

    This is the core entry point: it parses, correlates, and produces standalone HTML. If
    `output_path` is given, the HTML is also written to disk. Returns the HTML string.
    """
    tl = parse_logs(files)
    data = _timeline_to_data(tl)
    template = _TEMPLATE_PATH.read_text()
    html = template.replace(_DATA_PLACEHOLDER, json.dumps(data))
    if output_path is not None:
        Path(output_path).write_text(html)
    return html


# --------------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Render experiment logs as an interactive HTML timeline.")
    parser.add_argument("logs", nargs="+", metavar="LOG", help="Log files from the same experiment (one per node)")
    parser.add_argument("-o", "--output", metavar="FILE", help="Output HTML path (default: <experiment>.html next to the logs)")
    parser.add_argument("--open", action="store_true", help="Open the rendered HTML in a browser")
    args = parser.parse_args()

    files = [Path(f) for f in args.logs]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        sys.exit("Log file(s) not found: " + ", ".join(missing))

    tl = parse_logs(files)
    out = Path(args.output) if args.output else files[0].resolve().parent / f"{tl.label}.html"

    render_logs(files, output_path=out)
    print(f"Wrote {out}  ({len(tl.hosts)} hosts, {len(tl.epochs)} epochs, {len(tl.links)} messages)")
    if args.open:
        webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
