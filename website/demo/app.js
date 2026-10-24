// Demo viewer: replays a recorded run (demo/EVENTS.md) as a live network.

import { Clock, World, fmtTime, parseJsonl, parseRun, redact } from "./state.js";
import { Graph } from "./graph.js";
import { AgentPanel } from "./panels.js";
import { ThroughputChart } from "./chart.js";
import { Spotlight, readingTime } from "./spotlight.js";

const RECORDINGS = "recordings/";
const PAUSE_CAP_S = 3; // "Shorten waits": longest pause between events, in run seconds
const TRAVEL_REAL_S = 0.9; // how long a message takes to cross a link on screen, in real seconds
const COMMAND_REAL_S = 1.6; // how long a finished command stays under its node, in real seconds
const SPEEDS = [1, 2, 4, 8, 16, 32];

const $ = (sel) => document.querySelector(sel);
const ui = {
  scenario: $("#scenario"), model: $("#model"), levels: [...document.querySelectorAll(".detail button")],
  stage: $(".stage"), svg: $("#graph"), chart: $("#chart"), panel: $("#panel"), spot: $("#spotlight"),
  title: $("#run-title"), sub: $("#run-sub"),
  play: $("#play"), speed: $("#speed"), scrub: $("#scrub"), ticks: $("#ticks"), time: $("#time"),
  next: $("#next-msg"), prev: $("#prev-msg"), shorten: $("#shorten"), reports: $("#open-reports"),
  dialog: $("#reports"), reportTabs: $("#report-tabs"), reportBody: $("#report-body"), status: $("#status"),
};

let index = null, labels = {};
let run = null, world = null, clock = null, graph = null, panel = null, chart = null;
let playing = false, speed = 4, level = 2, p = 0, lastFrame = 0, selected = null, pinned = false;
// Message spotlight: while `spot` is set the run clock is held. `nextMsg` indexes the first
// message playback has not reached yet; messages sent at the same moment wait in `queue`.
const spotlight = new Spotlight(ui.spot);
let spot = null, queue = [], nextMsg = 0;
let loadToken = 0;

// --- loading ------------------------------------------------------------------------

async function init() {
  try {
    index = await (await fetch(RECORDINGS + "index.json")).json();
  } catch {
    ui.status.textContent = "Couldn't load the recordings index.";
    ui.status.hidden = false;
    return;
  }
  for (const r of index.runs) labels[r.model] = r.model_label;
  const scenarios = [...new Map(index.runs.map((r) => [r.scenario, r.title])).entries()];
  ui.scenario.replaceChildren(...scenarios.map(([id, title]) => new Option(title, id)));
  SPEEDS.forEach((s) => ui.speed.append(new Option(`${s}×`, s)));
  try { level = +(localStorage.getItem("demo.level") || 2); } catch {}
  setLevel(level);
  ui.speed.value = speed;

  await openFromHash();
}

// The URL hash names the run (#scenario/model), so links and the back button work.
async function openFromHash() {
  const [sc, md] = decodeURIComponent(location.hash.slice(1)).split("/");
  if (sc && index.runs.some((r) => r.scenario === sc)) ui.scenario.value = sc;
  fillModels(md);
  await load();
}

function fillModels(prefer) {
  const runs = index.runs.filter((r) => r.scenario === ui.scenario.value);
  ui.model.replaceChildren(...runs.map((r) => new Option(r.model_label, r.model)));
  if (prefer && runs.some((r) => r.model === prefer)) ui.model.value = prefer;
}

async function load() {
  const token = ++loadToken;
  const entry = index.runs.find((r) => r.scenario === ui.scenario.value && r.model === ui.model.value);
  if (!entry) return;
  history.replaceState(null, "", `#${entry.scenario}/${entry.model}`);
  setPlaying(false);
  ui.status.textContent = "Loading recording…";
  ui.status.hidden = false;
  let events;
  try {
    events = parseJsonl(await (await fetch(RECORDINGS + entry.file)).text());
  } catch {
    ui.status.textContent = "Couldn't load this recording.";
    return;
  }
  if (token !== loadToken) return; // a newer selection won
  ui.status.hidden = true;

  run = parseRun(events);
  world = new World(run);
  clock = new Clock(run, ui.shorten.checked ? PAUSE_CAP_S : Infinity);
  graph = new Graph(ui.svg, run, { onSelect: (id) => select(id, true) });
  panel = new AgentPanel(ui.panel, run, labels);
  chart = run.metrics.length ? new ThroughputChart(ui.chart, run.metrics) : null;
  ui.chart.hidden = !chart;
  ui.spot.hidden = !run.messages.length; // billing: no messages, the chart takes the space

  ui.title.textContent = run.start.title;
  // Every recording is a run from the paper; link it to the frozen paper data.
  const paperLink = document.createElement("a");
  paperLink.href = "../paper-data/";
  paperLink.textContent = `paper run, ${entry.paper}`;
  ui.sub.replaceChildren(
    `${labels[run.start.model] || run.start.model} · `, paperLink,
    ` · ${fmtTime(run.duration)} long · ${entry.messages} messages · ${entry.commands} commands`);
  selected = null;
  pinned = false;
  p = 0;
  drawTicks();
  seek(0);
}

// --- playback -------------------------------------------------------------------------

function setPlaying(on) {
  if (on && run && p >= clock.length) seek(0);
  playing = on && !!run;
  ui.play.textContent = playing ? "Pause" : "Play";
  ui.play.setAttribute("aria-pressed", playing);
  lastFrame = performance.now();
}

// Event types that count as an agent "acting", for auto-follow.
const ACTION_TYPES = new Set(["exec", "message", "assistant", "thinking", "idle", "state"]);

function followLatest(events) {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (ACTION_TYPES.has(e.type) && run.nodes.includes(e.node)) { selected = e.node; return; }
  }
}

// Jumping around never replays the messages passed over; only playback reaches them.
function seek(np) {
  p = Math.min(Math.max(np, 0), clock.length);
  world.advanceTo(clock.toRun(p));
  endSpot(false);
  nextMsg = run.messages.findIndex((m) => m.t > world.now);
  if (nextMsg < 0) nextMsg = run.messages.length;
  if (!pinned) followLatest(run.events.slice(0, world.i));
  render(true);
}

function startSpot(m) {
  spot = { m, total: readingTime(m.text), used: 0, shownAt: performance.now() };
  spotlight.show(m, { level, n: run.messages.indexOf(m) + 1, of: run.messages.length });
}

// Retire the current message; show the next one queued at the same moment, if any.
function endSpot(advance = true) {
  spot = null;
  if (advance && queue.length) return startSpot(queue.shift());
  queue = [];
  spotlight.clear(run && run.messages.length ? "Messages between the agents appear here, one at a time." : "");
}

function frame(now) {
  const dt = (now - lastFrame) / 1000;
  if (playing && run) {
    if (spot) {
      spot.used += dt;
      spotlight.progress(spot.used / spot.total);
      if (spot.used >= spot.total) endSpot();
      graphUpdate();
    } else {
      let np = Math.min(p + dt * speed, clock.length);
      let t = clock.toRun(np);
      const due = nextMsg < run.messages.length && run.messages[nextMsg].t <= t;
      if (due) {
        // Stop the clock exactly at the message, and put it (and any sent at the same moment) up.
        t = run.messages[nextMsg].t;
        np = clock.toPlay(t);
        while (nextMsg < run.messages.length && run.messages[nextMsg].t <= t) queue.push(run.messages[nextMsg++]);
      }
      p = np;
      const applied = world.advanceTo(t);
      if (due) startSpot(queue.shift());
      if (!pinned) followLatest(applied);
      render(false);
      if (p >= clock.length && !spot) setPlaying(false);
    }
  } else if (run) {
    graphUpdate(); // keep the spotlighted envelope flying even while paused
  }
  lastFrame = now;
  requestAnimationFrame(frame);
}

function graphUpdate() {
  const pNow = p;
  graph.update(world, {
    level,
    selected,
    focus: spot ? spot.m : null,
    travel: (m) => {
      // The spotlighted message flies in real time: the run clock is held while it is up.
      if (spot && m.id === spot.m.id) return (performance.now() - spot.shownAt) / 1000 / TRAVEL_REAL_S;
      const ps = clock.toPlay(m.t);
      const d = run.deliveredAt.get(m.id);
      const span = Math.min(d !== undefined ? clock.toPlay(d) - ps : Infinity, TRAVEL_REAL_S * speed);
      return span > 0 ? (pNow - ps) / span : 1;
    },
    showCommand: (id) => {
      const n = world.node[id];
      return n.cmd && (world.stateOf(id) === "exec" || pNow - clock.toPlay(n.cmdT) < COMMAND_REAL_S * speed);
    },
  });
}

function render(force) {
  if (!selected) selected = run.nodes[0];
  graphUpdate();
  panel.show(selected, level, world, force);
  chart?.update(world.now);
  ui.scrub.max = clock.length;
  ui.scrub.value = p;
  ui.time.textContent = `${fmtTime(world.now)} / ${fmtTime(run.duration)}`;
  ui.reports.disabled = world.now < run.duration - 0.5 || !run.reports.length;
}

function select(id, pin) {
  selected = id;
  pinned = pin;
  ui.panel.classList.toggle("pinned", pinned);
  render(false);
}

function setLevel(l) {
  level = l;
  ui.stage.dataset.level = l;
  ui.levels.forEach((b) => b.setAttribute("aria-checked", +b.dataset.level === l));
  try { localStorage.setItem("demo.level", l); } catch {}
  if (run) {
    render(true);
    if (spot) spotlight.show(spot.m, { level, n: run.messages.indexOf(spot.m) + 1, of: run.messages.length });
  }
}

// → / ←: step through messages. → first finishes the one on screen (and any queued with it);
// ← goes back to the previous message. Either way the target is put in the spotlight.
function jumpMessage(dir) {
  if (!run) return;
  const msgs = run.messages;
  const cur = spot ? msgs.indexOf(spot.m) : nextMsg - 1;
  if (dir > 0 && spot && queue.length) return endSpot();
  const i = dir > 0 ? (spot ? cur + 1 : nextMsg) : cur - (spot ? 1 : 0);
  if (i < 0 || i >= msgs.length) return;
  const m = msgs[i];
  seek(clock.toPlay(m.t));
  // Put the message itself up, plus later ones sent at the same moment.
  nextMsg = i + 1;
  while (nextMsg < msgs.length && msgs[nextMsg].t <= m.t) queue.push(msgs[nextMsg++]);
  startSpot(m);
  render(false);
}

function drawTicks() {
  ui.ticks.replaceChildren();
  for (const m of run.messages) {
    const i = document.createElement("i");
    i.style.left = `${(clock.toPlay(m.t) / clock.length) * 100}%`;
    ui.ticks.append(i);
  }
}

// --- reports --------------------------------------------------------------------------

function openReports() {
  const tabs = [...run.reports].sort((a, b) => (a.node ? 1 : 0) - (b.node ? 1 : 0));
  ui.reportTabs.replaceChildren(...tabs.map((r, i) => {
    const b = document.createElement("button");
    b.textContent = r.node ? r.node : "Final report";
    b.addEventListener("click", () => showReport(tabs, i));
    return b;
  }));
  showReport(tabs, 0);
  ui.dialog.showModal();
}

function showReport(tabs, i) {
  [...ui.reportTabs.children].forEach((b, k) => b.setAttribute("aria-selected", k === i));
  const html = window.marked ? window.marked.parse(redact(tabs[i].text)) : null;
  if (html && window.DOMPurify) ui.reportBody.innerHTML = window.DOMPurify.sanitize(html);
  else ui.reportBody.textContent = redact(tabs[i].text);
  ui.reportBody.scrollTop = 0;
}

// --- wiring ---------------------------------------------------------------------------

ui.scenario.addEventListener("change", () => { fillModels(ui.model.value); load(); });
ui.model.addEventListener("change", load);
ui.levels.forEach((b) => b.addEventListener("click", () => setLevel(+b.dataset.level)));
ui.play.addEventListener("click", () => setPlaying(!playing));
ui.speed.addEventListener("change", () => (speed = +ui.speed.value));
ui.scrub.addEventListener("input", () => seek(+ui.scrub.value));
ui.next.addEventListener("click", () => jumpMessage(1));
ui.prev.addEventListener("click", () => jumpMessage(-1));
ui.shorten.addEventListener("change", () => {
  if (!run) return;
  const t = world.now;
  clock = new Clock(run, ui.shorten.checked ? PAUSE_CAP_S : Infinity);
  p = clock.toPlay(t);
  drawTicks();
  render(false);
});
ui.reports.addEventListener("click", openReports);
window.addEventListener("hashchange", () => {
  if (index && location.hash !== `#${ui.scenario.value}/${ui.model.value}`) openFromHash();
});
$("#close-reports").addEventListener("click", () => ui.dialog.close());
ui.panel.querySelector(".follow").addEventListener("click", () => select(selected, false));
document.addEventListener("keydown", (ev) => {
  // Form controls keep their own keys (arrows move the slider, space toggles a checkbox);
  // a focused button already turns space into a click.
  if (ev.target.closest("select, input, dialog") || ev.ctrlKey || ev.metaKey || ev.altKey) return;
  if (ev.key === " " && ev.target.closest("button, summary")) return;
  if (ev.key === " ") { ev.preventDefault(); setPlaying(!playing); }
  else if (ev.key === "ArrowRight") jumpMessage(1);
  else if (ev.key === "ArrowLeft") jumpMessage(-1);
  else if (ev.key >= "1" && ev.key <= "4") setLevel(+ev.key);
});

init();
requestAnimationFrame(frame);
