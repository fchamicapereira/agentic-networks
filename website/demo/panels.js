// Activity panel: every agent's actions in one rolling feed, in run order. Append-only while
// playing; rebuilt only when seeking back past entries already shown. Agent text is untrusted:
// it goes into textContent, or through setMarkdown, which sanitizes it.
// In a narrated view the feed has only the commands (the agents' thoughts are in the bubbles on
// the graph, and messages in the message box), under a "Story so far" box (StoryBox) that ends
// with the outcome.

import { fmtTime, redact, setMarkdown } from "./state.js";
import { badge } from "./identity.js";

function md(cls, text) {
  const e = document.createElement("div");
  e.className = cls;
  setMarkdown(e, text);
  return e;
}

function h(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = redact(text);
  return e;
}

// Event types the panel shows: commands with their reasons, and the model's own words.
// Messages are left out (the spotlight under the graph shows each one), and so are state
// changes such as going idle (the graph shows those).
const PANEL_TYPES = new Set(["exec", "assistant", "thinking"]);

export class AgentPanel {
  constructor(root, run) {
    this.root = root;
    this.run = run;
    this.list = root.querySelector(".panel-list");
    this.shown = 0; // number of feed entries already rendered
    this.narrated = false;
    this.refeed();
    this.list.replaceChildren();
  }

  // Pick up events appended to the run since (a live run grows; the entries shown stay).
  refeed() {
    this.feed = this.narrated ? this.run.narration
      : this.run.events.filter((e) => PANEL_TYPES.has(e.type) && this.run.nodes.includes(e.node));
  }

  // Switch between the agents' own words and the narrator's.
  setNarrated(on) {
    if (on === this.narrated) return;
    this.narrated = on;
    this.root.classList.toggle("narrated", on);
    this.refeed();
    this.shown = 0;
    this.list.replaceChildren();
  }

  show(world) {
    if (this.shown > 0 && this.feed[this.shown - 1].t > world.now) {
      this.shown = 0;
      this.list.replaceChildren();
    }
    const stick = this.list.scrollHeight - this.list.scrollTop - this.list.clientHeight < 40;
    let added = false;
    while (this.shown < this.feed.length && this.feed[this.shown].t <= world.now) {
      this.list.appendChild(this.render(this.feed[this.shown]));
      added = true;
      this.shown++;
    }
    if (added && stick) this.list.scrollTop = this.list.scrollHeight;
    // The placeholder is not an entry: count entries only, or it would remove itself on one
    // frame and come back on the next (a visible flicker while playing).
    const empty = this.list.querySelector(".empty");
    const note = world.now === 0 && !this.run.live ? "Press play to start the replay." : "Nothing yet.";
    if (this.shown) empty?.remove();
    else if (!empty) this.list.appendChild(h("li", "empty", note));
    else if (empty.textContent !== note) empty.textContent = note;
  }

  render(e) {
    const li = h("li", `entry ${e.type}`);
    li.style.setProperty("--c", this.run.ident.get(e.node).color);
    // Every entry opens with the agent's name on its colour, so it is clear whose it is.
    const head = h("div", "entry-head");
    head.append(badge(this.run.ident, e.node), h("span", "time", fmtTime(e.t)));
    li.append(head);
    switch (e.type) {
      case "exec":
        if (e.reason) li.append(h("div", "reason", e.reason));
        li.append(h("code", "cmd", "$ " + e.command));
        break;
      case "assistant":
      case "thinking":
        li.append(md("prose", e.text));
        break;
    }
    return li;
  }
}

// "Story so far": the narrator's story lines up to now, newest last, and the outcome once the
// run is over. For people who walk up in the middle of a run.
export class StoryBox {
  constructor(root, run) {
    this.root = root;
    this.run = run;
    this.scroller = root.querySelector(".story-scroll");
    this.list = root.querySelector("ol");
    this.outcome = root.querySelector(".story-outcome");
    this.shown = -1;
    this.ended = null;
  }

  show(world, on) {
    this.root.hidden = !on || !this.run.narrated;
    if (this.root.hidden) return;
    const n = this.run.story.filter((c) => c.t <= world.now).length;
    if (n !== this.shown) {
      this.shown = n;
      this.list.replaceChildren(...this.run.story.slice(0, n).map((c, i) => {
        const li = h("li", i === n - 1 ? "latest" : "", c.text);
        li.style.setProperty("--c", this.run.ident.get(c.node)?.color || "");
        return li;
      }));
      if (!n) this.list.append(h("li", "empty", "Nothing has happened yet."));
      this.scroller.scrollTop = this.scroller.scrollHeight;
    }
    const ended = !!this.run.outcome && world.now >= this.run.duration - 0.5;
    if (ended !== this.ended) {
      this.ended = ended;
      this.outcome.hidden = !ended;
      if (ended) this.outcome.replaceChildren(h("strong", "", this.run.outcome.headline), h("p", "", this.run.outcome.text));
      this.scroller.scrollTop = this.scroller.scrollHeight; // keep the newest line, or the outcome, in view
    }
  }
}
