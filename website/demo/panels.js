// Agent panel: one agent's stream of actions. Append-only while playing; rebuilt from scratch
// after a seek, a node switch, or a detail-level change. Agent text is untrusted: it only
// ever goes into textContent.

import { fmtTime, redact } from "./state.js";

function h(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = redact(text);
  return e;
}

// Which event types the agent panel shows at each detail level (1 = minimal ... 4 = everything).
const PANEL_MIN_LEVEL = {
  exec: 2, message: 2, delivered: 2, state: 2,
  assistant: 3, thinking: 3, idle: 3,
  turn: 4, warning: 4, prompt: 4, usage: 4,
};

export class AgentPanel {
  constructor(root, run, labels) {
    this.root = root;
    this.run = run;
    this.labels = labels;
    this.head = root.querySelector(".panel-head");
    this.list = root.querySelector(".panel-list");
    this.node = null;
    this.level = 2;
    this.shown = 0; // number of this node's events already rendered
    this.byNode = new Map();
    this.msgById = new Map(run.messages.map((m) => [m.id, m]));
    this.resultById = new Map(run.events.filter((e) => e.type === "exec_result").map((e) => [e.id, e]));
    for (const e of run.events) {
      const n = e.type === "delivered" ? e.node : e.node;
      if (!n) continue;
      if (!this.byNode.has(n)) this.byNode.set(n, []);
      this.byNode.get(n).push(e);
    }
  }

  show(node, level, world, force = false) {
    if (node !== this.node || level !== this.level || force) {
      this.node = node;
      this.level = level;
      this.shown = 0;
      this.list.replaceChildren();
    }
    this.renderHead(world);
    if (!node) return;
    const evs = this.byNode.get(node) || [];
    const stick = this.list.scrollHeight - this.list.scrollTop - this.list.clientHeight < 40;
    let added = false;
    while (this.shown < evs.length && evs[this.shown].t <= world.now) {
      const item = this.render(evs[this.shown]);
      if (item) { this.list.appendChild(item); added = true; }
      this.shown++;
    }
    // exec results arrive after their exec card is drawn: fill them in when due.
    if (level >= 4) {
      for (const card of this.list.querySelectorAll(".exec[data-pending]")) {
        const r = this.resultById.get(card.dataset.id);
        if (r && r.t <= world.now) { this.fillResult(card, r); delete card.dataset.pending; }
      }
    }
    if (added && stick) this.list.scrollTop = this.list.scrollHeight;
    if (!this.list.childElementCount) {
      this.list.appendChild(h("li", "empty", world.now === 0 ? "Press play to start the replay." : "Nothing yet at this detail level."));
    } else {
      this.list.querySelector(".empty")?.remove();
    }
  }

  renderHead(world) {
    const id = this.node;
    if (!id) { this.head.replaceChildren(h("div", "panel-title", "Click an agent")); return; }
    const n = world.node[id];
    const state = world.stateOf(id);
    const title = h("div", "panel-title", id);
    const meta = h("div", "panel-meta");
    meta.append(h("span", `chip state-${state}`, { thinking: "thinking", exec: "running a command", dormant: "done · asleep", acting: "acting", waiting: "waiting" }[state]));
    if (n.iter) meta.append(h("span", "muted", `iteration ${n.iter}/${n.of}`));
    const model = this.run.models[id];
    if (model) meta.append(h("span", "muted", this.labels[model] || model));
    this.head.replaceChildren(title, meta);
  }

  render(e) {
    if ((PANEL_MIN_LEVEL[e.type] ?? 99) > this.level) return null;
    const li = h("li", `entry ${e.type}`);
    const time = h("span", "time", fmtTime(e.t));
    switch (e.type) {
      case "exec": {
        if (e.reason) li.append(h("div", "reason", e.reason));
        const cmd = h("div", "cmd");
        cmd.append(time, h("code", "", "$ " + e.command));
        li.append(cmd);
        li.dataset.id = e.id;
        if (this.level >= 4) {
          const r = this.resultById.get(e.id);
          li.dataset.pending = "";
          if (r && r.t <= e.t) { this.fillResult(li, r); delete li.dataset.pending; }
        }
        return li;
      }
      case "message": {
        const head = h("div", "msg-head");
        head.append(time, h("span", "", `✉ to ${e.to}`));
        if (e.reason) li.append(h("div", "reason", e.reason));
        li.append(head, h("div", "msg-text", e.text));
        return li;
      }
      case "delivered": {
        const m = this.msgById.get(e.id);
        if (!m) return null;
        const head = h("div", "msg-head");
        head.append(time, h("span", "", `✉ from ${m.from === "human" ? "the laptop owner" : m.from}`));
        li.append(head, h("div", "msg-text", m.text));
        return li;
      }
      case "state":
        li.append(time, h("span", "", e.state === "dormant" ? `Reported done: ${e.summary || ""}` : "Woken up by a message"));
        return li;
      case "assistant":
      case "thinking":
        li.append(time, h("div", "prose", e.text));
        return li;
      case "idle":
        li.append(time, h("span", "", "Passed the turn" + (e.reason ? ` — ${e.reason}` : "")));
        return li;
      case "turn":
        li.append(h("span", "", `iteration ${e.iter}/${e.of}`));
        return li;
      case "warning":
        li.append(time, h("span", "", e.text));
        return li;
      case "prompt": {
        const d = h("details");
        d.append(h("summary", "", "System prompt"), h("pre", "", e.text));
        li.append(d);
        return li;
      }
      case "usage":
        li.append(time, h("span", "", `${e.in} in / ${e.out} out tokens · $${(e.usd ?? 0).toFixed(3)}`));
        return li;
    }
    return null;
  }

  fillResult(card, r) {
    const d = h("details", "output");
    const lines = r.output ? r.output.split("\n").length : 0;
    const sum = h("summary", "", r.output ? `output · ${lines} line${lines === 1 ? "" : "s"}` : "no output");
    if (r.exit !== 0) sum.append(h("span", "exit-bad", ` exit ${r.exit}`));
    d.append(sum);
    if (r.output) d.append(h("pre", "", r.output));
    card.append(d);
  }
}
