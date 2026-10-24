// The message spotlight: one knowledge-plane message at a time, large enough to read on a
// projector, held on screen for a reading time that depends on its length (real seconds,
// independent of the playback speed). The app pauses the run clock while a message is up.

import { redact } from "./state.js";

const WORDS_PER_S = 3.5; // ~210 words per minute: a comfortable pace for reading off a screen
const MIN_S = 5, MAX_S = 40;

export function readingTime(text) {
  const words = String(text).trim().split(/\s+/).length;
  return Math.min(Math.max(2 + words / WORDS_PER_S, MIN_S), MAX_S);
}

const who = (id) => (id === "human" ? "Laptop owner" : id);

export class Spotlight {
  constructor(root) {
    this.root = root;
    this.head = root.querySelector(".spot-head");
    this.reason = root.querySelector(".spot-reason");
    this.text = root.querySelector(".spot-text");
    this.bar = root.querySelector(".spot-bar i");
    this.count = root.querySelector(".spot-count");
    this.clear("");
  }

  // n: position of this message in the run (1-based), of: number of messages in the run.
  show(m, { level, n, of }) {
    this.root.classList.remove("idle");
    const from = document.createElement("span");
    from.className = "from";
    from.textContent = who(m.from);
    const to = document.createElement("span");
    to.className = "to";
    to.textContent = who(m.to);
    this.head.replaceChildren(from, document.createTextNode(" → "), to);
    this.count.textContent = `message ${n} of ${of}`;
    // The sender's stated reason for the message: from "Actions" up, like commands' reasons.
    this.reason.textContent = level >= 2 && m.reason ? redact(m.reason) : "";
    this.reason.hidden = !this.reason.textContent;
    this.text.textContent = redact(m.text);
    this.text.scrollTop = 0;
    this.progress(0);
  }

  clear(placeholder) {
    this.root.classList.add("idle");
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
}
