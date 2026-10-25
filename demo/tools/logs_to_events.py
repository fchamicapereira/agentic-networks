#!/usr/bin/env python3
"""logs_to_events.py — Convert experiment logs into demo event recordings.

`convert_run` turns one run (a directory of per-agent text logs) into the event stream
described in demo/EVENTS.md. `write_recordings` does that for every run listed in the frozen
paper snapshot (paper-data/runs.json: 5 scenarios x 4 models), and writes one JSONL file per run
plus an index.json for the replay picker. Each run is read from logs/, where it may since have
been rerun; a run whose files still match the snapshot is marked as the paper's run.

Standard library only (like tools/build_website.py), so the Pages build can run it.

    python3 demo/tools/logs_to_events.py -o _site/demo/recordings
"""

import argparse
import csv
import json
import sys

from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from agentic_networks.visualize_logs import _CMD_OUT_RE, _ITER_RE, _MSG_RE, _REPORT_LEVELS, _raw_records  # noqa: E402

FORMAT_VERSION = 1
PAPER_DATA = REPO_ROOT / "paper-data"


def load_topology(path: Path) -> dict:
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


def parse_node(path: Path, node: str) -> list[dict]:
    """One node log -> agent events with integer-second `ts` (absolute) and per-node order.

    Message sends get a provisional id; receives carry `_recv` for correlation later.

    The harness logs an iteration marker for every agent every step, but a dormant (waiting) agent only
    calls the model when that step delivers it a message. A dormant agent's marker therefore
    becomes a `turn` only if a receive follows it; otherwise the node would look busy.
    """
    events: list[dict] = []
    pending_reason = ""
    dormant = False
    held_turn: "dict | None" = None
    last_exec: "dict | None" = None
    n = 0

    def emit(ts: int, type_: str, **fields) -> dict:
        ev = {"ts": ts, "type": type_, "node": node, **fields}
        events.append(ev)
        return ev

    for level, ts, msg in _raw_records(path.read_text(errors="replace")):
        if level not in _REPORT_LEVELS:
            continue
        if msg.startswith("System prompt:"):
            emit(ts, "prompt", text=msg[len("System prompt:"):].strip())
        elif m := _ITER_RE.match(msg):
            turn = {"ts": ts, "type": "turn", "node": node, "iter": int(m.group(1)), "of": int(m.group(2))}
            if dormant:
                held_turn = turn
            else:
                events.append(turn)
        elif msg.startswith("[assistant] "):
            emit(ts, "assistant", text=msg[len("[assistant] "):].strip())
        elif msg.startswith("[reason] "):
            pending_reason = msg[len("[reason] "):].strip()
        elif msg.startswith("Executing command:"):
            n += 1
            last_exec = emit(ts, "exec", id=f"{node}-x{n}", command=msg[len("Executing command:"):].strip(),
                             reason=pending_reason)
            pending_reason = ""
        elif (m := _CMD_OUT_RE.match(msg)) and last_exec is not None:
            out = m.group(2).strip()
            emit(ts, "exec_result", id=last_exec["id"], output="" if out == "(empty)" else out, exit=int(m.group(1)))
            last_exec = None
        elif m := _MSG_RE.match(msg):
            arrow, peer, text = m.group(1), m.group(2).strip(), m.group(3).strip()
            if arrow == "→":
                emit(ts, "message", **{"from": node, "to": peer, "text": text, "reason": pending_reason})
                pending_reason = ""
            else:
                if held_turn is not None:
                    events.append(held_turn)
                    held_turn = None
                emit(ts, "_recv", **{"from": peer, "text": text})
        elif msg.startswith("Idle"):
            emit(ts, "idle", reason=pending_reason)
            pending_reason = ""
        elif "AGENT TERMINATED" in msg:  # report_done, in runs before it was removed
            emit(ts, "state", state="dormant", summary=msg.split("===")[-1].strip(), reason=pending_reason)
            pending_reason = ""
            dormant = True
        elif "AGENT WAITING" in msg:  # idle: asleep until a message arrives
            emit(ts, "state", state="dormant")
            dormant = True
        elif "AGENT REACTIVATED" in msg or "AGENT WOKEN" in msg:
            emit(ts, "state", state="active")
            dormant = False
        elif msg.startswith("Command timed out") and last_exec is not None:
            emit(ts, "exec_result", id=last_exec["id"], output=msg.strip(), exit=124)
            last_exec = None
        elif level in ("WARNING", "ERROR", "CRITICAL"):
            emit(ts, "warning", text=msg.strip())
    return events


def spread_within_seconds(events: list[dict]) -> None:
    """Give same-(node, second) events evenly spaced fractional times, preserving order."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for ev in events:
        groups[(ev["node"], ev["ts"])].append(ev)
    for (_, ts), evs in groups.items():
        for i, ev in enumerate(evs):
            ev["t"] = ts + i / len(evs)


def correlate_messages(events: list[dict]) -> None:
    """Pair each receive with the earliest unmatched identical send; turn it into `delivered`.

    Matching compares whole seconds: spreading within a second is per node, so a receive
    logged in the same second as its send may have a smaller fractional time. Such a
    delivery is nudged to just after its send (the recipient logs the receive right after
    its iteration marker, and its next action is an LLM round-trip away).

    A receive with no matching send (the owner's complaint, injected by the harness as
    sender "human") becomes a synthetic `message` from that sender just before delivery.
    A message to a party with no log of its own (the owner) is delivered on sending.
    """
    sends = [e for e in events if e["type"] == "message"]
    for i, ev in enumerate(sorted(sends, key=lambda e: e["t"])):
        ev["id"] = f"m{i + 1}"
    used: set[str] = set()
    synthetic = 0
    extra: list[dict] = []
    for rcv in sorted((e for e in events if e["type"] == "_recv"), key=lambda e: e["t"]):
        match = next((s for s in sorted(sends, key=lambda e: e["t"])
                      if s["id"] not in used and s["from"] == rcv["from"] and s["to"] == rcv["node"]
                      and s["text"] == rcv["text"] and s["ts"] <= rcv["ts"]), None)
        if match is None:
            synthetic += 1
            match = {"t": max(rcv["t"] - 0.5, 0), "ts": rcv["ts"], "type": "message", "node": rcv["from"],
                     "id": f"h{synthetic}", "from": rcv["from"], "to": rcv["node"], "text": rcv["text"], "reason": ""}
            extra.append(match)
        used.add(match["id"])
        rcv["t"] = max(rcv["t"], match["t"] + 0.001)
        rcv["type"] = "delivered"
        rcv["id"] = match["id"]
        del rcv["from"], rcv["text"]
    events.extend(extra)
    logged = {e["node"] for e in events if e["type"] == "prompt"}  # every agent logs its prompt
    events.extend({"t": s["t"] + 0.001, "ts": s["ts"], "type": "delivered", "node": s["to"], "id": s["id"]}
                  for s in sends if s["to"] not in logged)


def billing_metrics(data_path: Path, turns: list[float]) -> list[dict]:
    """Map billing samples (simulated days) onto wall time via the ISP's iteration starts.

    Iteration k (1-based) starts at simulated hour (k - 1) * step_hours; samples in between are
    placed by linear interpolation. Approximate, but faithful to the order of events.
    """
    data = json.loads(data_path.read_text())
    step_h = data["params"]["step_hours"]
    out = []
    for s in data["samples"]:
        k = s["elapsed_days"] * 24 / step_h
        i = min(int(k), len(turns) - 2)
        t = turns[i] + (k - i) * (turns[i + 1] - turns[i]) if len(turns) > 1 else turns[0]
        for prefix, values in s["mbps"].items():
            out.append({"t": t, "type": "metric", "name": "throughput_mbps", "prefix": prefix,
                        "sim_days": s["elapsed_days"], "values": values})
    return out


def convert_run(run_dir: Path, stem: str, topology: dict, scenario: str, title: str,
                model: str, model_label: str) -> "tuple[list[dict], dict] | None":
    """One run's per-agent logs (<run_dir>/<stem>-<Node>.log) -> (events, index summary)."""
    node_ids = [n["id"] for n in topology["nodes"]]
    logs = {node: run_dir / f"{stem}-{node}.log" for node in node_ids}
    missing = [str(p) for p in logs.values() if not p.exists()]
    if missing:
        print(f"skip {scenario} {model}: missing {', '.join(missing)}", file=sys.stderr)
        return None

    events = [ev for node, path in logs.items() for ev in parse_node(path, node)]
    t0 = min(ev["ts"] for ev in events)
    for ev in events:
        ev["ts"] -= t0
    spread_within_seconds(events)
    correlate_messages(events)

    data = run_dir / f"{stem}-data.json"  # billing: traffic samples
    turns = sorted(e["t"] for e in events if e["type"] == "turn" and e["node"] == "ISP")
    if data.exists() and turns:
        events += billing_metrics(data, turns)

    events.sort(key=lambda e: e["t"])
    t_end = events[-1]["t"] if events else 0.0
    dormant_at_end = {e["node"]: e["state"] == "dormant" for e in events if e["type"] == "state"}
    reason = "all_dormant" if all(dormant_at_end.get(n) for n in node_ids) else "max_iterations"

    tail = [{"t": t_end, "type": "run_end", "reason": reason}]
    for node in node_ids:
        report = run_dir / f"{stem}-{node}-report.md"
        if report.exists():
            tail.append({"t": t_end, "type": "report", "node": node, "text": report.read_text()})
    final = run_dir / f"{stem}-final-report.md"
    if final.exists():
        tail.append({"t": t_end, "type": "report", "text": final.read_text()})

    head = {"t": 0, "type": "run_start", "v": FORMAT_VERSION, "source": "recording",
            "scenario": scenario, "title": title, "model": model,
            "models": {n: model for n in node_ids}, "topology": topology}
    out = [head] + [{k: v for k, v in ev.items() if k != "ts"} for ev in events] + tail
    for ev in out:
        ev["t"] = round(ev["t"], 3)

    summary = {"scenario": scenario, "title": title, "model": model,
               "model_label": model_label, "duration_s": round(t_end), "end_reason": reason,
               "messages": sum(e["type"] == "message" for e in out),
               "commands": sum(e["type"] == "exec" for e in out)}
    return out, summary


def _is_paper_run(run: dict, logs_root: Path, paper_dir: Path) -> bool:
    """True if every file the snapshot holds for this run is unchanged under `logs_root`."""
    for rel in run["files"]:
        current = logs_root / rel
        if not current.exists() or current.read_bytes() != (paper_dir / rel).read_bytes():
            return False
    return True


def write_recordings(output: Path, paper_dir: Path = PAPER_DATA, logs_root: Path = REPO_ROOT,
                     verbose: bool = False) -> int:
    """Write every run listed in the paper snapshot plus index.json into `output`; return the count.

    Runs are read from `logs_root` (the repository, so logs/...), falling back to the snapshot
    when a run's logs are missing there. Index entries carry `paper` (the paper section) only for
    runs identical to the snapshot; any other run is a rerun with the current harness.
    """
    meta = json.loads((paper_dir / "runs.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    index = []
    for sc in meta["scenarios"]:
        topology = load_topology(paper_dir / "inputs" / "topologies" / f"{sc['topology']}.csv")
        for run in sc["runs"]:
            run_dir = logs_root / sc["logs_dir"]
            if not (run_dir / f"{run['stem']}-{sc['nodes'][0]}.log").exists():
                run_dir = paper_dir / sc["logs_dir"]
            paper = run_dir.is_relative_to(paper_dir) or _is_paper_run(run, logs_root, paper_dir)
            result = convert_run(run_dir, run["stem"], topology, sc["id"], sc["title"],
                                 run["model"], run["model_label"])
            if result is None:
                continue
            events, summary = result
            name = f"{sc['id']}__{run['model']}.jsonl"
            with open(output / name, "w") as f:
                for ev in events:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            index.append({**summary, "paper": sc["paper"] if paper else None, "paper_section": sc["paper"],
                          "file": name})
            if verbose:
                print(f"{name:<55} {summary['duration_s']:>5}s  {summary['messages']:>3} msgs  "
                      f"{summary['commands']:>4} cmds  {summary['end_reason']:<14} {'paper' if paper else 'rerun'}")
    (output / "index.json").write_text(json.dumps({"v": FORMAT_VERSION, "runs": index}, indent=2) + "\n")
    return len(index)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--output", type=Path, required=True, metavar="DIR")
    parser.add_argument("--paper-dir", type=Path, default=PAPER_DATA, metavar="DIR")
    parser.add_argument("--logs-root", type=Path, default=REPO_ROOT, metavar="DIR",
                        help="directory holding logs/ (default: the repository)")
    args = parser.parse_args()
    write_recordings(args.output, args.paper_dir, args.logs_root, verbose=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
