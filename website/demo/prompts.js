// Prompts dialog: each agent's system prompt, one tab per agent. Most of a prompt is harness
// boilerplate every agent gets; what is specific to an agent comes first, and the shared rest is
// folded under "Common instructions". Nothing is rewritten, only regrouped. Prompt text is
// untrusted: it goes into textContent only.

import { redact } from "./state.js";
import { badge } from "./identity.js";

// A prompt is a list of blocks separated by blank lines or headings (top-level lines ending in
// ":"). A heading block's body is split into items: a line at the body's base indentation starts
// one, deeper lines continue it (wrapped text, a tool's parameters). A block without a heading is
// a paragraph, kept whole.
function blocks(text) {
  const out = [];
  let cur = null;
  for (const line of text.split("\n")) {
    if (!line.trim()) { cur = null; continue; }
    const prose = !/^\s/.test(line) && !line.startsWith("-");
    const heading = prose && line.trimEnd().endsWith(":");
    // A plain top-level sentence after a heading's bulleted or indented list starts a new paragraph.
    const listEnds = prose && cur?.head && cur.lines.length && !(!/^\s/.test(cur.lines[0]) && !cur.lines[0].startsWith("-"));
    if (heading || !cur || listEnds) { cur = { head: heading ? line : null, lines: heading ? [] : [line] }; out.push(cur); }
    else cur.lines.push(line);
  }
  for (const b of out) {
    if (b.head === null) { b.items = [b.lines]; continue; }
    const indent = (l) => l.length - l.trimStart().length;
    const base = b.lines.length ? indent(b.lines[0]) : 0;
    b.items = [];
    for (const l of b.lines) {
      if (!b.items.length || indent(l) <= base) b.items.push([l]);
      else b.items[b.items.length - 1].push(l);
    }
  }
  return out;
}

// id -> { own, common }: what is specific to the agent, and what every agent in the run shares.
// An item (or paragraph) is shared only if every one of its lines appears in every agent's
// prompt; it stays whole either way. Headings go with their items, on both sides if need be.
// With a single agent there is nothing to compare: all of it is its own.
export function splitPrompts(prompts) {
  const ids = [...prompts.keys()];
  const lineSets = ids.map((id) => new Set(prompts.get(id).split("\n").map((l) => l.trim()).filter(Boolean)));
  const shared = (lines) => ids.length > 1 && lines.every((l) => lineSets.every((s) => s.has(l.trim())));
  const out = new Map();
  for (const id of ids) {
    const own = [], common = [];
    for (const { head, items } of blocks(prompts.get(id))) {
      const mine = items.filter((it) => !shared(it)).flat(), theirs = items.filter((it) => shared(it)).flat();
      if (head === null) { (mine.length ? own : common).push([...mine, ...theirs].join("\n")); continue; }
      if (mine.length || !shared([head])) own.push([head, ...mine].join("\n"));
      if (theirs.length || (!items.length && shared([head]))) common.push([head, ...theirs].join("\n"));
    }
    out.set(id, { own: own.join("\n\n"), common: common.join("\n\n") });
  }
  return out;
}

export class PromptsDialog {
  constructor(dialog) {
    this.dialog = dialog;
    this.tabs = dialog.querySelector(".tabs");
    this.body = dialog.querySelector(".prompt-body");
    this.run = null;
  }

  setRun(run) {
    this.run = run;
    const prompts = new Map(run.events.filter((e) => e.type === "prompt" && run.nodes.includes(e.node)).map((e) => [e.node, e.text]));
    this.split = splitPrompts(prompts);
    this.ids = run.nodes.filter((id) => this.split.has(id));
  }

  get available() { return !!this.run && this.ids.length > 0; }

  open(id = this.ids[0]) {
    if (!this.available) return;
    this.tabs.replaceChildren(...this.ids.map((n) => {
      const b = document.createElement("button");
      b.setAttribute("role", "tab");
      b.append(badge(this.run.ident, n));
      b.addEventListener("click", () => this.show(n));
      return b;
    }));
    const sel = this.ids.includes(id) ? id : this.ids[0];
    this.show(sel);
    if (!this.dialog.open) this.dialog.showModal();
    this.tabs.children[this.ids.indexOf(sel)].focus(); // not the first tab, which would look selected
  }

  show(id) {
    [...this.tabs.children].forEach((b, k) => b.setAttribute("aria-selected", this.ids[k] === id));
    const { own, common } = this.split.get(id);
    this.dialog.style.setProperty("--c", this.run.ident.get(id).color);
    const mine = document.createElement("pre");
    mine.className = "prompt-own";
    mine.textContent = redact(own);
    const parts = [mine];
    if (common) {
      const d = document.createElement("details");
      const s = document.createElement("summary");
      s.textContent = "Common instructions (the same for every agent)";
      const pre = document.createElement("pre");
      pre.textContent = redact(common);
      d.append(s, pre);
      parts.push(d);
    }
    this.body.replaceChildren(...parts);
    this.body.scrollTop = 0;
  }
}
