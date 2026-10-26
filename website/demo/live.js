// Live mode: the connection to a demo server (demo/server.py) on this machine.
//
// The page polls the server's status (models, the current run) and follows the current run's
// event stream (Server-Sent Events). The server runs on localhost, which browsers let an HTTPS
// page reach; Chrome asks the visitor once to allow it.

const POLL_MS = 2000;
const CONNECT_TIMEOUT_MS = 3000;

export class LiveServer {
  // onStatus(status | null): every poll, null when the server can't be reached.
  // onRun(runStatus): a run to follow appeared (a new one, or the one going when we connected).
  // onEvents(events): new events of the followed run, in order.
  constructor({ onStatus, onRun, onEvents }) {
    Object.assign(this, { onStatus, onRun, onEvents });
    this.base = null;
    this.status = null;
    this.timer = null;
    this.source = null;
    this.runId = null;
    this.watching = true; // follow the current run's events (Live), or only poll the status (Replay)
  }

  get connected() { return !!this.status; }

  async connect(port) {
    this.disconnect();
    this.base = `http://localhost:${port}`;
    await this.poll();
    if (!this.status) return false;
    this.timer = setInterval(() => this.poll(), POLL_MS);
    return true;
  }

  disconnect() {
    clearInterval(this.timer);
    this.timer = null;
    this.source?.close();
    this.source = null;
    this.runId = null;
    this.status = null;
  }

  async request(path, body) {
    const opts = { signal: AbortSignal.timeout(CONNECT_TIMEOUT_MS) };
    if (body !== undefined) {
      Object.assign(opts, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    }
    const res = await fetch(this.base + path, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  async poll() {
    try {
      this.status = await this.request("/api/status");
    } catch {
      this.status = null;
    }
    this.onStatus(this.status);
    const run = this.status?.run;
    if (this.watching && run && run.id !== this.runId) this.follow(run);
  }

  // Replay: keep polling, so the page can still tell a run is going, but stop following events.
  watch(on) {
    this.watching = on;
    if (!on) {
      this.source?.close();
      this.source = null;
      this.runId = null;
    }
  }

  // Follow a run's events from its start. EventSource reconnects by itself after a dropped
  // connection, resuming after the last event it got.
  follow(run) {
    this.source?.close();
    this.runId = run.id;
    this.onRun(run);
    const source = new EventSource(this.base + "/api/events");
    this.source = source;
    let batch = [];
    let flushing = false;
    source.onmessage = (msg) => {
      if (source !== this.source) return;
      batch.push(JSON.parse(msg.data));
      // Hand events over in batches, at most once per frame: a page that connects late gets
      // the whole run so far in one burst.
      if (!flushing) {
        flushing = true;
        requestAnimationFrame(() => {
          flushing = false;
          const events = batch;
          batch = [];
          if (source === this.source && events.length) this.onEvents(events);
        });
      }
    };
    source.addEventListener("end", () => source.close());
    // The server moved on to a newer run; the next poll picks it up.
    source.addEventListener("replaced", () => { source.close(); this.runId = null; });
  }

  // prompts: {agent: whole system prompt} the attendee edited; opening: their edited opening message.
  start(scenario, model, prompts = {}, opening = undefined) {
    return this.request("/api/runs", { scenario, model, prompts, opening }).then((s) => this.apply(s));
  }
  stop() { return this.request("/api/runs/stop", {}).then((s) => this.apply(s)); }
  clear() { return this.request("/api/runs/clear", {}).then((s) => this.apply(s)); }
  recheck() { return this.request("/api/models/check", {}).then((s) => this.apply(s)); }

  apply(status) {
    this.status = status;
    this.onStatus(status);
    if (this.watching && status.run && status.run.id !== this.runId) this.follow(status.run);
  }
}
