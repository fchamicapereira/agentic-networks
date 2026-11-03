// The message spotlight: one knowledge-plane message at a time, large enough to read on a
// projector, held on screen for a reading time that depends on its length (seconds at 1×, over
// app.js READ_PACE, divided by the playback speed). The app pauses the run clock while a
// message is up.
// In a narrated run it shows the message's gist (a one-line summary by Claude) instead (the
// footer's Original switch brings back the agent's own text); at the end of the run, the outcome.

import { redact, setMarkdown } from "./state.js";
import { badge } from "./identity.js";

const WORDS_PER_S = 3.5; // ~210 words per minute: a comfortable pace for reading off a screen
const MIN_S = 5, MAX_S = 40;
// A gist (narrated runs) is one sentence, read by people walking past who glance up mid-message:
// it stays up longer per word, and never less than GIST_MIN_S.
const GIST_WORDS_PER_S = 2, GIST_MIN_S = 9;

export function readingTime(text, { gist = false } = {}) {
  const words = String(text).trim().split(/\s+/).length;
  if (gist) return Math.min(Math.max(3 + words / GIST_WORDS_PER_S, GIST_MIN_S), MAX_S);
  return Math.min(Math.max(2 + words / WORDS_PER_S, MIN_S), MAX_S);
}

const who = (id) => (id === "human" ? "Laptop owner" : id);

export class Spotlight {
  constructor(root) {
    this.root = root;
    this.ident = new Map();
    this.head = root.querySelector(".spot-head");
    this.reason = root.querySelector(".spot-reason");
    this.text = root.querySelector(".spot-text");
    this.bar = root.querySelector(".spot-bar i");
    this.count = root.querySelector(".spot-count");
    this.gist = root.querySelector(".spot-gist");
    this.clear("");
  }

  // n: position of this message in the run (1-based), of: number of messages in the run.
  // gist: its summary, in a narrated view (else null).
  show(m, { n, of, gist = null }) {
    this.root.classList.remove("idle", "outcome");
    this.root.classList.toggle("narrated", !!gist);
    this.gist.textContent = gist ? redact(gist) : "";
    // The card wears the sender's colour; both ends carry their node's colour.
    this.root.style.setProperty("--c", this.ident.get(m.from)?.color || "");
    this.head.replaceChildren(badge(this.ident, m.from, who(m.from)), document.createTextNode(" → "), badge(this.ident, m.to, who(m.to)));
    this.count.textContent = `message ${n} of ${of}`;
    // The sender's stated reason for the message: from "Actions" up, like commands' reasons.
    this.reason.textContent = m.reason && !gist ? redact(m.reason) : "";
    this.reason.hidden = !this.reason.textContent;
    setMarkdown(this.text, m.text);
    this.text.scrollTop = 0;
    this.progress(0);
  }

  clear(placeholder) {
    this.root.classList.add("idle");
    this.root.classList.remove("narrated", "outcome");
    this.gist.textContent = "";
    this.head.replaceChildren();
    this.count.textContent = "";
    this.reason.hidden = true;
    this.text.textContent = placeholder;
    this.progress(0);
  }

  // f: fraction of the reading time used. Text that overflows the card scrolls along with it,
  // after a short head start, so a long message can be read without touching anything.
  progress(f) {
    this.bar.style.width = `${Math.min(f, 1) * 100}%`;
    const overflow = this.text.scrollHeight - this.text.clientHeight;
    if (overflow > 0 && f > 0) this.text.scrollTop = Math.min(Math.max((f - 0.15) / 0.75, 0), 1) * overflow;
  }

  // The run is over: its outcome, summarized by Claude from the agents' reports.
  showOutcome(c) {
    this.clear("");
    this.root.classList.remove("idle");
    this.root.classList.add("narrated", "outcome");
    this.root.style.setProperty("--c", "");
    const head = document.createElement("span");
    head.textContent = "How it ended";
    this.head.replaceChildren(head);
    this.gist.textContent = redact(c.headline);
    this.text.classList.remove("md");
    this.text.textContent = redact(c.text);
  }
}
