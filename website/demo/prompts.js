// Prompts dialog: each agent's system prompt, one tab per agent, and the message a run opens with
// (the laptop owner's complaint in the KP scenarios). Read-only, most of a prompt is harness
// boilerplate every agent gets: what is specific to an agent comes first, and the shared rest is
// folded under "Common instructions". Nothing is rewritten, only regrouped. In Live, before a run
// starts, the dialog edits instead: each agent's whole prompt, exactly as the agent will get it.
// Prompt text is untrusted: it goes into textContent and textarea values only.

import { redact } from "./state.js";
import { badge } from "./identity.js";

export const OPENING = "opening"; // the tab of the message a run opens with
export const MAX_PROMPT_CHARS = 12000, MAX_OPENING_CHARS = 2000; // as demo/server.py checks

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
    this.resetAll = dialog.querySelector(".reset-all");
    this.resetAll.addEventListener("click", () => {
      this.editor?.reset(null);
      this.show(this.current);
    });
    this.run = null;
    this.editor = null;
  }

  // run: the run on screen. editor (or null, read-only): { original: Map id -> text,
  // current: Map id -> text, change(id, text), reset(id | null) } over the same ids, OPENING included.
  setRun(run, editor = null) {
    this.run = run;
    this.editor = editor;
    const prompts = new Map(run.events.filter((e) => e.type === "prompt" && run.nodes.includes(e.node)).map((e) => [e.node, e.text]));
    this.split = splitPrompts(prompts);
    this.ids = run.nodes.filter((id) => prompts.has(id));
    // The opening message: a preview names it; a run has it as its first message from outside.
    const first = run.messages.find((m) => run.pseudo.has(m.from));
    this.opening = run.start.opening?.text ?? first?.text ?? null;
    this.openingFrom = run.start.opening?.from ?? first?.from ?? null;
    if (this.opening !== null) this.ids.push(OPENING);
    this.resetAll.hidden = !editor;
  }

  get available() { return !!this.run && this.ids.length > 0; }

  edited(id) { return !!this.editor && this.editor.current.get(id) !== this.editor.original.get(id); }

  open(id = this.ids[0]) {
    if (!this.available) return;
    this.tabs.replaceChildren(...this.ids.map((n) => {
      const b = document.createElement("button");
      b.setAttribute("role", "tab");
      b.append(n === OPENING ? badge(this.run.ident, this.openingFrom, "Laptop owner") : badge(this.run.ident, n));
      b.addEventListener("click", () => this.show(n));
      return b;
    }));
    const sel = this.ids.includes(id) ? id : this.ids[0];
    this.show(sel);
    if (!this.dialog.open) this.dialog.showModal();
    this.tabs.children[this.ids.indexOf(sel)].focus(); // not the first tab, which would look selected
  }

  marks() {
    [...this.tabs.children].forEach((b, k) => {
      b.setAttribute("aria-selected", this.ids[k] === this.current);
      b.classList.toggle("edited", this.edited(this.ids[k]));
    });
    this.resetAll.disabled = !this.ids.some((id) => this.edited(id));
  }

  show(id) {
    this.current = id;
    const who = id === OPENING ? this.openingFrom : id;
    this.dialog.style.setProperty("--c", this.run.ident.get(who)?.color || "");
    this.body.replaceChildren(...(this.editor ? this.editView(id) : this.readView(id)));
    this.marks();
    this.body.scrollTop = 0;
  }

  readView(id) {
    if (id === OPENING) {
      const note = document.createElement("p");
      note.className = "prompt-note";
      note.textContent = "The message that starts the run.";
      const pre = document.createElement("pre");
      pre.className = "prompt-own";
      pre.textContent = redact(this.opening);
      return [note, pre];
    }
    const { own, common } = this.split.get(id);
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
    return parts;
  }

  // The whole text, editable, exactly as the run will use it.
  editView(id) {
    const opening = id === OPENING;
    const max = opening ? MAX_OPENING_CHARS : MAX_PROMPT_CHARS;
    const note = document.createElement("p");
    note.className = "prompt-note";
    note.textContent = opening
      ? "The message that starts the run. Edit it to ask something else; it is sent exactly as written."
      : "This agent's whole system prompt, exactly as it will get it. Edit any part of it. " +
        "Your edits stay in this browser, and are used when you press Play.";
    const area = document.createElement("textarea");
    area.className = "prompt-edit";
    area.spellcheck = false;
    area.maxLength = max;
    area.value = this.editor.current.get(id);
    area.setAttribute("aria-label", opening ? "The opening message" : `${id}'s system prompt`);
    const foot = document.createElement("div");
    foot.className = "prompt-foot";
    const count = document.createElement("span");
    count.className = "prompt-count";
    const reset = document.createElement("button");
    reset.textContent = "Reset to original";
    const update = () => {
      count.textContent = `${area.value.length.toLocaleString()} / ${max.toLocaleString()} characters`;
      reset.disabled = !this.edited(id);
      this.marks();
    };
    area.addEventListener("input", () => { this.editor.change(id, area.value); update(); });
    reset.addEventListener("click", () => { this.editor.reset(id); area.value = this.editor.current.get(id); update(); });
    foot.append(count, reset);
    update();
    return [note, area, foot];
  }
}
