#!/usr/bin/env python3
"""server.py — Run experiments live for the demo viewer.

The demo page (website/demo/, also on the project's public website) connects to this server
at http://localhost:<port> when switched to Live. The server starts one experiment at a time,
with the paper's settings for the chosen scenario (paper_experiments.toml) and the chosen model,
through tools/run_in_docker.sh, so the models are reached through the per-run LLM proxy and the
keys never enter the container. The run writes its event stream (demo/EVENTS.md) to
demo/logs/<run>/events.jsonl, and the server streams that file to every connected page.

    python3 demo/server.py                           # http://127.0.0.1:8800
    python3 demo/server.py --port 9000 --vllm-host 10.15.0.30
    python3 demo/server.py --fake --fake-speed 10    # replays recordings instead: no Docker, no models

Needs Docker access, and the provider keys in the environment (ANTHROPIC_API_KEY,
OPENAI_API_KEY, TOGETHER_API_KEY), as for any run. Standard library only.

API (JSON unless noted):
    GET  /api/status          the server, the models' availability, and the current run
    GET  /api/scenarios       each scenario as a run would start: topology and every agent's prompt
    GET  /api/events          the current run's events as Server-Sent Events, from its start
    POST /api/runs            start a run: {"scenario", "model"}, and optionally the attendee's edits:
                              "prompts" {agent: whole system prompt}, "opening" (KP: the owner's complaint)
    POST /api/runs/stop       stop the current run
    POST /api/runs/clear      forget the current run and delete its folder (stopping it first)
    POST /api/models/check    test every model again (a tiny real request to each)

It listens on 127.0.0.1 only, and answers only pages from the project website or localhost.
POSTs must be JSON, so a page from any other site can't start runs from the browser.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LOGS = REPO / "demo" / "logs"
LOGS = DEFAULT_LOGS  # --logs-dir; must be inside the repository, which the container sees
RUNNER = REPO / "tools" / "run_in_docker.sh"
RECORDINGS = REPO / "_site" / "demo" / "recordings"

# The paper's scenarios (paper_experiments.toml names) and models.
SCENARIOS = ["kp_university_firewall", "kp_dns_stale", "kp_server_overload", "celer_bridge", "optimizing_billing_policy"]
MODELS = {
    "opus-4-7": "Claude Opus 4.7",
    "gpt-5.5": "GPT 5.5",
    "glm-5.2": "GLM 5.2 (FP4)",
    "qwen2.5-72b-awq": "Qwen 2.5 72B (AWQ)",
}
# Models called with tools described in the system prompt (vLLM, Together): the harness adds a tool
# guide after their prompt, which the page shows (each preview prompt's tool_guide).
TOOL_GUIDE_MODELS = {"glm-5.2", "qwen2.5-72b-awq"}
# Attendees' edits: whole system prompts, and the message a run opens with.
MAX_PROMPT_CHARS = 12_000
MAX_OPENING_CHARS = 2_000
# paper_experiments.toml fields that don't become flags: the server sets the model, logs and reports.
NOT_FLAGS = {"name", "script", "report_model", "log_dir"}

PUBLIC_ORIGIN = "https://fchamicapereira.github.io"
LOCAL_ORIGIN = re.compile(r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?")
STOP_GRACE_S = 60  # how long a stopped run gets to wind down before it is killed
MODEL_CHECK_PREFIX = "MODEL_CHECK_RESULTS "  # tools/test_model_connection.py --json


def load_experiments(path: Path) -> dict[str, dict[str, "str | list[str]"]]:
    """The [[experiment]] blocks of an experiments TOML file, by name. Only `key = "string"` and
    `key = ["string", ...]` lines occur there, which is all this reads."""
    experiments, current = {}, None
    for n, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "[[experiment]]":
            current = {}
            continue
        m = re.fullmatch(r'(\w+)\s*=\s*(?:"([^"]*)"|\[((?:\s*"[^"]*"\s*,?)*)\])', line)
        if current is None or not m:
            sys.exit(f"{path}:{n}: unexpected line (the server reads only [[experiment]] blocks of "
                     'key = "value" and key = ["value", ...])')
        key = m.group(1)
        current[key] = m.group(2) if m.group(2) is not None else re.findall(r'"([^"]*)"', m.group(3))
        if key == "name":
            experiments[current[key]] = current
    return experiments


def preview_from_recording(scenario: str, fixed_models: dict[str, str]) -> list[dict]:
    """--fake: a scenario's preview from its recordings, standing in for its --describe. The tool
    guide is what an agent's Qwen prompt has after its Opus one."""
    def read(model):
        return [json.loads(l) for l in (RECORDINGS / f"{scenario}__{model}.jsonl").read_text().splitlines() if l.strip()]
    events, text_tools = read("opus-4-7"), read("qwen2.5-72b-awq")
    start = dict(events[0], source="live", model="", models={})
    nodes = {n["id"] for n in start["topology"]["nodes"]}
    human = next((e for e in events if e["type"] == "message" and e["from"] not in nodes), None)
    if human:
        start["outsiders"] = {human["from"]: human["to"]}
        start["opening"] = {"from": human["from"], "to": human["to"], "text": human["text"]}
    guided = {e["node"]: e["text"] for e in text_tools if e["type"] == "prompt"}
    out = [start]
    for e in (e for e in events if e["type"] == "prompt"):
        g = guided.get(e["node"], "")
        guide = g[len(e["text"]) + 2:] if g.startswith(e["text"] + "\n\n") else ""
        fixed = {"model": fixed_models[e["node"]]} if e["node"] in fixed_models else {}
        out.append({"t": 0, "type": "prompt", "node": e["node"], "text": e["text"], "tool_guide": guide, **fixed})
    for node in (n["id"] for n in start["topology"]["nodes"]):
        first = next((e for e in events if e.get("node") == node and e["type"] not in ("prompt", "usage")), None)
        if first and first["type"] == "state" and first["state"] == "dormant":
            out.append({"t": 0, "type": "state", "node": node, "state": "dormant"})
    return out


class Run:
    """One experiment run: its process, and its folder under demo/logs/."""

    def __init__(self, scenario: str, model: str, folder: Path, command: list[str], container: str | None,
                 edited: list[str] = ()):
        self.id = folder.name
        self.scenario, self.model = scenario, model
        self.edited = list(edited)  # agents whose prompt the attendee edited, and "opening"
        self.folder = folder
        self.events = folder / "events.jsonl"
        self.container = container
        self.started = time.time()
        self.ended: float | None = None
        self.stopping = False
        self.exit_code: int | None = None
        with open(folder / "run.out", "w") as out:
            # Its own process group, so Stop reaches the runner, Docker and the proxy at once.
            self.proc = subprocess.Popen(command, cwd=REPO, stdout=out, stderr=subprocess.STDOUT,
                                         stdin=subprocess.DEVNULL, start_new_session=True)
        threading.Thread(target=self._wait, daemon=True).start()

    def _wait(self) -> None:
        self.exit_code = self.proc.wait()
        self.ended = time.time()

    def stop(self) -> None:
        """Interrupt the run as Ctrl-C would; kill it if it hasn't ended after STOP_GRACE_S."""
        if self.ended or self.stopping:
            return
        self.stopping = True
        try:
            os.killpg(self.proc.pid, signal.SIGINT)
        except ProcessLookupError:
            return

        def force() -> None:
            deadline = time.monotonic() + STOP_GRACE_S
            while self.ended is None and time.monotonic() < deadline:
                time.sleep(0.5)
            if self.ended is None:
                if self.container:
                    subprocess.run(["docker", "rm", "-f", self.container], capture_output=True)
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        threading.Thread(target=force, daemon=True).start()

    def end_reason(self) -> str | None:
        """How the run ended: its run_end event, or else how the process went."""
        if self.ended is None:
            return None
        try:
            with open(self.events, encoding="utf-8") as f:
                for line in f:
                    if '"run_end"' in line:
                        return json.loads(line).get("reason", "unknown")
        except (OSError, ValueError):
            pass
        return "stopped" if self.stopping else "error"

    def status(self) -> dict:
        return {"id": self.id, "scenario": self.scenario, "model": self.model, "edited": self.edited,
                "state": "ended" if self.ended else ("stopping" if self.stopping else "running"),
                "started": self.started, "elapsed": round((self.ended or time.time()) - self.started, 1),
                "end_reason": self.end_reason()}


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, args):
        super().__init__(addr, Handler)
        self.args = args
        self.experiments = load_experiments(REPO / "paper_experiments.toml")
        missing = [s for s in SCENARIOS if s not in self.experiments]
        if missing:
            sys.exit(f"paper_experiments.toml has no experiment named {', '.join(missing)}")
        self.origins = {PUBLIC_ORIGIN, *args.allow_origin}
        self.lock = threading.Lock()
        self.run: Run | None = None
        self.models = {key: {"ok": None, "error": None} for key in MODELS}
        self.checking = False
        self.checked_at: float | None = None
        self.clearing = False
        # Each scenario as a run would start (the experiment's --describe), for the page to draw
        # before any run: {scenario: [events]}, filled in the background at startup.
        self.previews: dict[str, list] = {}

    # --- runs ---------------------------------------------------------------------------

    def command(self, scenario: str, model: str, folder: Path, container: str | None,
                edits: list[str] = ()) -> list[str]:
        if self.args.fake:
            recording = RECORDINGS / f"{scenario}__{model}.jsonl"
            return [sys.executable, str(REPO / "demo" / "tools" / "fake_run.py"), str(recording),
                    str(folder / "events.jsonl"), "--speed", str(self.args.fake_speed)]
        rel = folder.relative_to(REPO)  # as the container sees it, from the repository root
        exp = self.experiments[scenario]
        edit_flags = []
        if any(e != "opening" for e in edits):
            edit_flags += ["--system-prompts", str(rel / "prompts")]
        if "opening" in edits:
            edit_flags += ["--human-message-file", str(rel / "opening.txt")]
        return [str(RUNNER), "--container-name", container, exp["script"], *self.flags(scenario),
                "--model", model, "--vllm-host", self.args.vllm_host,
                "--log-dir", str(rel), "--events", str(rel / "events.jsonl"), "--no-reports", *edit_flags]

    def flags(self, scenario: str) -> list[str]:
        """The scenario's paper settings (paper_experiments.toml) as the experiment's flags; a list
        repeats its flag (as run_experiments.py does)."""
        out = []
        for key, value in self.experiments[scenario].items():
            if key not in NOT_FLAGS:
                for item in value if isinstance(value, list) else [value]:
                    out += ["--" + key.replace("_", "-"), item]
        return out

    def fixed_models(self, scenario: str) -> dict[str, str]:
        """Agents that run on a set model whatever the run's model (agent_model = ["NODE=MODEL"])."""
        return dict(spec.split("=", 1) for spec in self.experiments[scenario].get("agent_model", []))

    def describe_scenarios(self) -> None:
        """Fill self.previews in the background: each experiment's --describe, through Docker."""
        def describe() -> None:
            for scenario in SCENARIOS:
                if self.args.fake:
                    events = preview_from_recording(scenario, self.fixed_models(scenario))
                else:
                    out = LOGS / f".describe-{scenario}.jsonl"  # dotfiles survive clearing old runs
                    exp = self.experiments[scenario]
                    proc = subprocess.run([str(RUNNER), exp["script"], *self.flags(scenario), "--describe", str(out.relative_to(REPO))],
                                          cwd=REPO, capture_output=True, text=True, stdin=subprocess.DEVNULL)
                    try:
                        events = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
                    except (OSError, ValueError):
                        print(f"{time.strftime('%H:%M:%S')} could not describe {scenario}: "
                              + " / ".join((proc.stdout + proc.stderr).strip().splitlines()[-3:]), flush=True)
                        continue
                    finally:
                        out.unlink(missing_ok=True)
                with self.lock:
                    self.previews[scenario] = events
            print(f"{time.strftime('%H:%M:%S')} scenarios ready: {len(self.previews)}/{len(SCENARIOS)}", flush=True)

        LOGS.mkdir(parents=True, exist_ok=True)
        threading.Thread(target=describe, daemon=True).start()

    def check_edits(self, scenario: str, prompts, opening) -> "str | None":
        """Why the attendee's edits can't be used, or None. Agents come from the scenario's preview."""
        preview = self.previews.get(scenario)
        if (prompts or opening is not None) and preview is None:
            return "the scenario is still being prepared; try again in a moment"
        if not isinstance(prompts, dict):
            return "prompts must be {agent: text}"
        agents = {e["node"] for e in preview or [] if e["type"] == "prompt"}
        for agent, text in prompts.items():
            if agent not in agents:
                return f"no agent {agent!r} in this scenario"
            if not isinstance(text, str) or not text.strip():
                return f"{agent}'s prompt is empty"
            if len(text) > MAX_PROMPT_CHARS:
                return f"{agent}'s prompt is longer than {MAX_PROMPT_CHARS} characters"
        if opening is not None:
            if not preview[0].get("opening"):
                return "this scenario does not start with a message"
            if not isinstance(opening, str) or not opening.strip() or len(opening) > MAX_OPENING_CHARS:
                return f"the opening message must have 1 to {MAX_OPENING_CHARS} characters"
        return None

    def start_run(self, scenario: str, model: str, prompts=None, opening=None) -> tuple[int, dict]:
        if scenario not in SCENARIOS:
            return 400, {"error": f"unknown scenario {scenario!r}"}
        if model not in MODELS:
            return 400, {"error": f"unknown model {model!r}"}
        prompts = prompts or {}
        problem = self.check_edits(scenario, prompts, opening)
        if problem:
            return 400, {"error": problem}
        for needed in {model, *self.fixed_models(scenario).values()}:
            if self.models.get(needed, {}).get("ok") is False:
                return 409, {"error": f"{MODELS[needed]} is not available: {self.models[needed]['error']}"}
        with self.lock:
            if self.run and not self.run.ended:
                return 409, {"error": "a run is already going; stop it first"}
            # Finished runs are cleared when the next one starts.
            LOGS.mkdir(parents=True, exist_ok=True)
            for old in LOGS.iterdir():
                if old.name.startswith("."):
                    continue
                shutil.rmtree(old, ignore_errors=True) if old.is_dir() else old.unlink(missing_ok=True)
            run_id = time.strftime("%Y%m%d-%H%M%S") + f"-{scenario}-{model}"
            folder = LOGS / run_id
            folder.mkdir()
            # The attendee's edits, as files in the run's folder; prompts/<scenario>/ is never touched.
            if prompts:
                (folder / "prompts").mkdir()
                for agent, text in prompts.items():
                    (folder / "prompts" / f"{agent}.txt").write_text(text)
            if opening is not None:
                (folder / "opening.txt").write_text(opening)
            edits = sorted(prompts) + (["opening"] if opening is not None else [])
            container = None if self.args.fake else f"demo-{run_id}"
            self.run = Run(scenario, model, folder, self.command(scenario, model, folder, container, edits), container, edits)
            print(f"{time.strftime('%H:%M:%S')} run {run_id} started", flush=True)
            return 200, self.status()

    def stop_run(self) -> tuple[int, dict]:
        with self.lock:
            if not self.run or self.run.ended:
                return 409, {"error": "no run is going"}
            self.run.stop()
            print(f"{time.strftime('%H:%M:%S')} run {self.run.id} stopping", flush=True)
            return 200, self.status()

    def clear_run(self) -> tuple[int, dict]:
        """Forget the current run and delete its folder; a run still going is stopped first."""
        with self.lock:
            run = self.run
            if run is None:
                return 409, {"error": "no run to clear"}
            if self.clearing:
                return 409, {"error": "already clearing"}
            self.clearing = True
            run.stop()
            print(f"{time.strftime('%H:%M:%S')} run {run.id} clearing", flush=True)

        def clear() -> None:
            deadline = time.monotonic() + STOP_GRACE_S + 15
            while run.ended is None and time.monotonic() < deadline:
                time.sleep(0.2)
            with self.lock:
                if self.run is run:
                    self.run = None
                self.clearing = False
            shutil.rmtree(run.folder, ignore_errors=True)

        threading.Thread(target=clear, daemon=True).start()
        return 200, self.status()

    # --- models -------------------------------------------------------------------------

    def check_models(self) -> None:
        """Test every model in the background, the way runs reach them (Docker and the proxy)."""
        with self.lock:
            if self.checking:
                return
            self.checking = True

        def check() -> None:
            results: dict[str, str | None] = {}
            if self.args.fake:
                results = {m: None if any(RECORDINGS.glob(f"*__{m}.jsonl")) else "no recording" for m in MODELS}
            else:
                proc = subprocess.run(
                    [str(RUNNER), "tools/test_model_connection.py", "-m", *MODELS, "--json",
                     "--vllm-host", self.args.vllm_host],
                    cwd=REPO, capture_output=True, text=True, stdin=subprocess.DEVNULL)
                lines = [l for l in proc.stdout.splitlines() if l.startswith(MODEL_CHECK_PREFIX)]
                if lines:
                    results = json.loads(lines[-1][len(MODEL_CHECK_PREFIX):])
                else:
                    tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
                    results = {m: "the check did not run: " + " / ".join(tail) for m in MODELS}
            with self.lock:
                for key in MODELS:
                    error = results.get(key, "not checked")
                    self.models[key] = {"ok": error is None, "error": error}
                self.checking = False
                self.checked_at = time.time()
            ok = [MODELS[k] for k in MODELS if self.models[k]["ok"]]
            print(f"{time.strftime('%H:%M:%S')} models available: {', '.join(ok) or 'none'}", flush=True)

        threading.Thread(target=check, daemon=True).start()

    def status(self) -> dict:
        return {
            "server": "agentic-networks-demo", "v": 1, "fake": self.args.fake,
            "scenarios": SCENARIOS,
            "models": [{"key": k, "label": MODELS[k], "tool_guide": k in TOOL_GUIDE_MODELS, **self.models[k]} for k in MODELS],
            "checking": self.checking, "checked_at": self.checked_at,
            "previews": sorted(self.previews), "clearing": self.clearing,
            "run": self.run.status() if self.run else None,
        }


class Handler(BaseHTTPRequestHandler):
    server_version = "agentic-networks-demo"

    def log_message(self, fmt, *args):  # the server prints its own one-line notes instead
        pass

    # --- origins ------------------------------------------------------------------------

    def origin(self) -> "str | None | bool":
        """The request's Origin if allowed, None without one (not a browser), False if refused."""
        origin = self.headers.get("Origin")
        if origin is None:
            return None
        return origin if origin in self.server.origins or LOCAL_ORIGIN.fullmatch(origin) else False

    def cors(self, origin) -> None:
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def reply(self, status: int, body: dict, origin=None) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.cors(origin)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        origin = self.origin()
        if not origin:
            return self.reply(403, {"error": "origin not allowed"})
        self.send_response(204)
        self.cors(origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if self.headers.get("Access-Control-Request-Private-Network"):
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    # --- requests -----------------------------------------------------------------------

    def do_GET(self):
        origin = self.origin()
        if origin is False:
            return self.reply(403, {"error": "origin not allowed"})
        path = urlparse(self.path).path
        if path == "/api/status":
            return self.reply(200, self.server.status(), origin)
        if path == "/api/events":
            return self.stream(origin)
        if path == "/api/scenarios":
            with self.server.lock:
                return self.reply(200, dict(self.server.previews), origin)
        if path == "/":
            return self.reply(200, {"server": "agentic-networks-demo",
                                    "note": "Open the demo page, switch to Live, and connect to this port."}, origin)
        self.reply(404, {"error": "not found"}, origin)

    def do_POST(self):
        origin = self.origin()
        if origin is False:
            return self.reply(403, {"error": "origin not allowed"})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.reply(415, {"error": "send JSON"}, origin)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            return self.reply(400, {"error": "invalid JSON"}, origin)
        path = urlparse(self.path).path
        if path == "/api/runs":
            return self.reply(*self.server.start_run(body.get("scenario", ""), body.get("model", ""),
                                                     body.get("prompts"), body.get("opening")), origin)
        if path == "/api/runs/stop":
            return self.reply(*self.server.stop_run(), origin)
        if path == "/api/runs/clear":
            return self.reply(*self.server.clear_run(), origin)
        if path == "/api/models/check":
            self.server.check_models()
            return self.reply(200, self.server.status(), origin)
        self.reply(404, {"error": "not found"}, origin)

    def stream(self, origin) -> None:
        """The current run's events, from the start (or from Last-Event-ID), as they are written.

        Each event is an SSE message whose id is its line number. A run that ended without a
        run_end (killed) gets one. Ends with an `end` message; a page that is still connected
        when the next run starts gets `replaced` and reconnects to it.
        """
        run = self.server.run
        if run is None:
            return self.reply(404, {"error": "no run yet"}, origin)
        self.send_response(200)
        self.cors(origin)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            skip = int(self.headers.get("Last-Event-ID") or 0)
        except ValueError:
            skip = 0
        n, seen_end, buf, f = 0, False, "", None
        last_write = time.monotonic()
        try:
            self.wfile.write(f"retry: 2000\nevent: run\ndata: {json.dumps(run.status())}\n\n".encode())
            while True:
                if self.server.run is not run:
                    self.wfile.write(b"event: replaced\ndata: {}\n\n")
                    return
                ended = run.ended is not None  # read before the file, so no line written before the end is missed
                if f is None and run.events.exists():
                    f = open(run.events, encoding="utf-8")
                chunk = f.read() if f else ""
                buf += chunk
                *lines, buf = buf.split("\n")
                out = []
                for line in lines:
                    if not line.strip():
                        continue
                    n += 1
                    seen_end |= '"run_end"' in line
                    if n > skip:
                        out.append(f"id: {n}\ndata: {line}\n\n")
                if not chunk and ended:
                    if not seen_end:
                        n += 1
                        end = {"t": round(run.ended - run.started, 3), "type": "run_end", "reason": run.end_reason()}
                        out.append(f"id: {n}\ndata: {json.dumps(end)}\n\n")
                    out.append("event: end\ndata: {}\n\n")
                    self.wfile.write("".join(out).encode())
                    return
                if out:
                    self.wfile.write("".join(out).encode())
                    last_write = time.monotonic()
                elif time.monotonic() - last_write > 15:
                    self.wfile.write(b": still running\n\n")  # keeps proxies and the browser from timing out
                    last_write = time.monotonic()
                self.wfile.flush()
                time.sleep(0.25)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            if f:
                f.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", "-p", type=int, default=8800, help="port to listen on (default: 8800)")
    parser.add_argument("--vllm-host", default="localhost", metavar="HOST", help="the vLLM server for local models (e.g. Qwen)")
    parser.add_argument("--allow-origin", action="append", default=[], metavar="ORIGIN",
                        help=f"another website allowed to use the server (always: {PUBLIC_ORIGIN} and localhost)")
    parser.add_argument("--logs-dir", type=Path, default=DEFAULT_LOGS, metavar="DIR",
                        help=f"where runs are written; the previous run is deleted when the next starts (default: {DEFAULT_LOGS.relative_to(REPO)})")
    parser.add_argument("--fake", action="store_true", help=f"replay recordings from {RECORDINGS.relative_to(REPO)} instead of running experiments")
    parser.add_argument("--fake-speed", type=float, default=1.0, metavar="X", help="with --fake: how many times faster than the recording")
    args = parser.parse_args()
    global LOGS
    LOGS = args.logs_dir.resolve()
    if not args.fake and not LOGS.is_relative_to(REPO):
        sys.exit(f"--logs-dir must be inside {REPO}: the experiment container only sees the repository")
    if args.fake and not RECORDINGS.is_dir():
        sys.exit(f"--fake needs the recordings in {RECORDINGS}: run tools/build_website.py first")
    if not args.fake:
        # Every run and model check goes through Docker: say so now, rather than fail them all.
        docker = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True)
        if docker.returncode != 0:
            detail = (docker.stderr.strip().splitlines() or ["(no output)"])[-1]
            hint = ("\nYour user can't use Docker in this shell. If you were just added to the docker group, "
                    "log in again, or start the server with: sg docker -c \"python3 demo/server.py ...\""
                    if "permission denied" in detail else "")
            sys.exit(f"Docker is not usable: {detail}{hint}")
    # Started in the background by a script, a program ignores Ctrl-C (SIGINT), and so would the
    # runs it starts, which is how Stop run reaches them. Handle it, whatever we inherited.
    signal.signal(signal.SIGINT, signal.default_int_handler)

    server = DemoServer(("127.0.0.1", args.port), args)
    print(f"Demo server on http://127.0.0.1:{args.port}{'  (fake runs)' if args.fake else ''}")
    print(f"Open the demo page, switch to Live, and connect to port {args.port}.", flush=True)
    server.check_models()
    server.describe_scenarios()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server.run and not server.run.ended:
            print("Stopping the current run...", flush=True)
            server.run.stop()
            server.run.proc.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
