// Run model and playback clock for the demo viewer.
//
// The viewer is a function of the event stream alone (demo/EVENTS.md). `parseRun` indexes a
// recording once; `World` is the network's state at a point in time, built by applying events
// in order; `Clock` maps playback time to run time, optionally compressing long pauses.

export function parseJsonl(text) {
  return text.split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
}

export function parseRun(events) {
  const start = events[0];
  if (!start || start.type !== "run_start") throw new Error("recording does not begin with run_start");
  const topo = start.topology;
  const nodes = topo.nodes.map((n) => n.id);

  // Senders outside the topology (the laptop owner in the KP scenarios) are drawn as
  // pseudo-nodes attached to whoever they talk to.
  const pseudo = new Map();
  for (const e of events) {
    if (e.type === "message" && !nodes.includes(e.from) && !pseudo.has(e.from)) pseudo.set(e.from, e.to);
  }

  const deliveredAt = new Map();
  for (const e of events) if (e.type === "delivered") deliveredAt.set(e.id, e.t);

  const end = events.find((e) => e.type === "run_end");
  return {
    start,
    events,
    topo,
    nodes,
    pseudo,
    deliveredAt,
    duration: end ? end.t : events[events.length - 1].t,
    endReason: end ? end.reason : "unknown",
    messages: events.filter((e) => e.type === "message"),
    metrics: events.filter((e) => e.type === "metric"),
    reports: events.filter((e) => e.type === "report"),
    models: start.models || {},
  };
}

// Node states shown on the graph. "acting" decays to "waiting" once the node has been quiet
// for a moment, since the log does not say when an agent's turn ends.
const ACTING_DECAY_S = 2;

export class World {
  constructor(run) {
    this.run = run;
    this.reset();
  }

  reset() {
    this.i = 0; // index of the next event to apply
    this.now = 0;
    this.node = {};
    for (const id of [...this.run.nodes, ...this.run.pseudo.keys()]) {
      this.node[id] = { state: "waiting", iter: 0, of: 0, lastT: -Infinity, cmd: null, cmdT: -Infinity, summary: "" };
    }
  }

  // Apply every event with t <= time. Seeking backwards replays from the start, which is
  // cheap at these sizes (a few thousand events).
  advanceTo(time) {
    if (time < this.now) this.reset();
    const ev = this.run.events;
    const applied = [];
    while (this.i < ev.length && ev[this.i].t <= time) {
      this.apply(ev[this.i]);
      applied.push(ev[this.i]);
      this.i++;
    }
    this.now = time;
    return applied;
  }

  apply(e) {
    const n = this.node[e.node];
    if (!n) return;
    n.lastT = e.t;
    switch (e.type) {
      case "turn":
        n.state = "thinking";
        n.iter = e.iter;
        n.of = e.of;
        break;
      case "exec":
        n.state = "exec";
        n.cmd = e.command;
        n.cmdT = e.t;
        break;
      case "state":
        n.state = e.state === "dormant" ? "dormant" : "acting";
        if (e.state === "dormant") n.summary = e.summary || "";
        break;
      case "assistant":
      case "thinking":
      case "exec_result":
      case "message":
      case "idle":
        if (n.state !== "dormant") n.state = "acting";
        break;
    }
  }

  stateOf(id) {
    const n = this.node[id];
    if (n.state === "acting" && this.now - n.lastT > ACTING_DECAY_S) return "waiting";
    return n.state;
  }

  // Messages sent but not yet taken from the recipient's inbox.
  inFlight() {
    const out = [];
    for (const m of this.run.messages) {
      if (m.t > this.now) break;
      const d = this.run.deliveredAt.get(m.id);
      if (d === undefined || d > this.now) out.push(m);
    }
    return out;
  }
}

// Playback time <-> run time. With a cap, every gap between consecutive events longer than
// `cap` seconds is squeezed linearly into `cap` seconds, so long LLM waits pass quickly but
// still show (a node keeps "thinking" through the squeezed gap).
export class Clock {
  constructor(run, cap = Infinity) {
    const ts = [...new Set(run.events.map((e) => e.t))].sort((a, b) => a - b);
    if (ts[0] !== 0) ts.unshift(0);
    this.T = ts;
    this.P = [0];
    for (let k = 1; k < ts.length; k++) this.P.push(this.P[k - 1] + Math.min(ts[k] - ts[k - 1], cap));
    this.length = this.P[this.P.length - 1];
  }

  static _seg(arr, x) {
    let lo = 0, hi = arr.length - 1;
    if (x <= arr[0]) return 1;
    if (x >= arr[hi]) return hi;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (arr[mid] <= x) lo = mid; else hi = mid;
    }
    return hi;
  }

  toRun(p) {
    if (this.T.length < 2) return 0;
    const k = Clock._seg(this.P, p);
    const dp = this.P[k] - this.P[k - 1];
    const f = dp > 0 ? Math.min(Math.max((p - this.P[k - 1]) / dp, 0), 1) : 1;
    return this.T[k - 1] + f * (this.T[k] - this.T[k - 1]);
  }

  toPlay(t) {
    if (this.T.length < 2) return 0;
    const k = Clock._seg(this.T, t);
    const dt = this.T[k] - this.T[k - 1];
    const f = dt > 0 ? Math.min(Math.max((t - this.T[k - 1]) / dt, 0), 1) : 1;
    return this.P[k - 1] + f * (this.P[k] - this.P[k - 1]);
  }
}

// Last line of defense against showing a credential on screen: agents run shell commands
// that could print one, so anything shaped like a provider API key is masked before display.
const KEY_RE = /\b(sk-ant-[A-Za-z0-9_-]{8,}|sk-(?:proj-)?[A-Za-z0-9_-]{16,}|tgp_v1_[A-Za-z0-9_-]{8,})/g;
export function redact(text) {
  return text ? String(text).replace(KEY_RE, "[redacted key]") : "";
}

// Agent text is untrusted and often Markdown: render it, then sanitize the HTML before it reaches
// the page. Without the vendored libraries it falls back to plain text.
export function setMarkdown(el, text) {
  const t = redact(text);
  if (window.marked && window.DOMPurify) {
    el.innerHTML = window.DOMPurify.sanitize(window.marked.parse(t, { breaks: true }));
    el.classList.add("md");
  } else {
    el.textContent = t;
  }
}

export function fmtTime(s) {
  s = Math.max(0, Math.floor(s));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const mm = String(m).padStart(h ? 2 : 1, "0"), ss = String(sec).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}
