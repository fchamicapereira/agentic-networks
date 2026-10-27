// Demo viewer: replays a recorded run (demo/EVENTS.md) as a live network, or, in Live mode,
// follows a run going on a demo server on this machine (demo/server.py, see live.js).

import { Clock, World, fmtTime, indexRun, parseJsonl, parseRun, redact } from "./state.js";
import { Graph, appendMark } from "./graph.js";
import { AgentPanel } from "./panels.js";
import { ThroughputChart } from "./chart.js";
import { Spotlight, readingTime } from "./spotlight.js";
import { identities } from "./identity.js";
import { OPENING, PromptsDialog } from "./prompts.js";
import { LiveServer } from "./live.js";

const RECORDINGS = "recordings/";
const PAUSE_CAP_S = 3; // longest pause between events, in run seconds (mostly waiting on the models)
const COMMAND_REAL_S = 1.6; // how long a finished command stays under its node, in real seconds
const FLIGHT_S = 1.5; // how long the spotlighted message's envelope takes to cross its link, at 1×
const SPEEDS = [1, 2, 4, 8, 16, 32];
const DEFAULT_PORT = 8800;
// How a live run ended, for the subtitle (run_end reasons, demo/EVENTS.md).
const ENDINGS = { all_dormant: "every agent idle", max_iterations: "out of iterations", stopped: "stopped",
  budget: "out of budget", error: "failed", unknown: "ended" };

const $ = (sel) => document.querySelector(sel);
const ui = {
  scenario: $("#scenario"), model: $("#model"),
  stage: $(".stage"), svg: $("#graph"), chart: $("#chart"), panel: $("#panel"), spot: $("#spotlight"),
  title: $("#run-title"), sub: $("#run-sub"), pill: $("#run-pill"), editedTag: $("#edited-tag"),
  play: $("#play"), speed: $("#speed"), scrub: $("#scrub"), ticks: $("#ticks"), time: $("#time"),
  next: $("#next-msg"), prev: $("#prev-msg"), reports: $("#open-reports"),
  dialog: $("#reports"), reportTabs: $("#report-tabs"), reportBody: $("#report-body"), status: $("#status"),
  modes: [...document.querySelectorAll(".mode button")], conn: $("#conn"), port: $("#port"),
  connect: $("#connect"), recheck: $("#recheck"), stop: $("#stop-run"), clear: $("#clear-run"), catchUp: $("#catch-up"),
};

let index = null, labels = {};
let run = null, world = null, clock = null, graph = null, panel = null, chart = null;
let playing = false, speed = 1, p = 0, lastFrame = 0;
// Message spotlight: while `spot` is set the run clock is held. `nextMsg` indexes the first
// message playback has not reached yet; messages sent at the same moment wait in `queue`.
const spotlight = new Spotlight(ui.spot);
const prompts = new PromptsDialog($("#prompts"));
let resumeAfterPrompts = false;
let spot = null, queue = [], nextMsg = 0;
let loadToken = 0;
let mode = "replay";
let replayEntry = null; // the recording on screen (index.json entry)
// Live: the server connection, and the followed run's events until its run_start arrives.
const live = new LiveServer({ onStatus: liveStatus, onRun: liveRun, onEvents: liveEvents });
let livePending = [];
let liveModelsSig = "";
// Each scenario as a run would start (the server's /api/scenarios), drawn before a run.
const previews = new Map();
let following = null; // id of the server's run on screen (or being started)
// A run plays by itself only when Play on this page started it; one found already going (on
// coming back to Live, or after a reload) opens paused.
let startedHere = false, autoplay = false;
// Attendees' edits to a scenario's prompts and opening message, kept in this browser:
// { "<scenario>|<guide|plain>": { <agent or OPENING>: text } }. Prompts for models with a tool
// guide in their prompt (Qwen, GLM) differ from the others', so they are kept apart.
const EDITS_KEY = "demo-edits";
let edits = loadEdits();

// --- loading ------------------------------------------------------------------------

async function init() {
  try {
    index = await (await fetch(RECORDINGS + "index.json")).json();
  } catch {
    notice("Couldn't load the recordings index.");
    return;
  }
  for (const r of index.runs) labels[r.model] = r.model_label;
  fillReplayScenarios();
  SPEEDS.forEach((s) => ui.speed.append(new Option(`${s}×`, s)));
  ui.speed.value = speed;
  ui.port.value = savedPort();

  if (location.hash === "#live") await setMode("live");
  else await openFromHash();
}

function fillReplayScenarios() {
  const scenarios = [...new Map(index.runs.map((r) => [r.scenario, r.title])).entries()];
  ui.scenario.replaceChildren(...scenarios.map(([id, title]) => new Option(title, id)));
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
  notice("Loading recording…");
  let events;
  try {
    events = parseJsonl(await (await fetch(RECORDINGS + entry.file)).text());
  } catch {
    notice("Couldn't load this recording.");
    return;
  }
  if (token !== loadToken || mode !== "replay") return; // a newer selection won
  replayEntry = entry;
  openRun(events);
}

// Put a run on screen from its events so far, at its start.
function openRun(events) {
  ui.status.hidden = true;
  ui.stage.classList.remove("no-run");
  enableTransport();
  run = parseRun(events);
  run.live = mode === "live";
  run.ident = identities(run);
  spotlight.ident = run.ident;
  world = new World(run);
  clock = new Clock(run, PAUSE_CAP_S);
  graph = new Graph(ui.svg, run, { onSelect: openPrompts });
  prompts.setRun(run);
  $("#open-prompts").disabled = !prompts.available;
  panel = new AgentPanel(ui.panel, run);
  chart = run.metrics.length ? new ThroughputChart(ui.chart, run.metrics, run.ident) : null;
  ui.chart.hidden = !chart;
  // Billing has no messages: the chart takes the space. A live run (or preview) has none yet,
  // so it goes by whether its scenario's recordings have any.
  ui.spot.hidden = !run.messages.length && !(run.live && scenarioHasMessages(run.start.scenario));

  ui.title.textContent = titleOf(run.start.scenario) || run.start.title;
  subtitle();
  controls();
  p = 0;
  drawTicks();
  seek(0);
}

const titleOf = (scenario) => index?.runs.find((r) => r.scenario === scenario)?.title;
const scenarioHasMessages = (scenario) => !!index?.runs.some((r) => r.scenario === scenario && r.messages > 0);

function subtitle() {
  ui.editedTag.hidden = !(mode === "live" && run && (run.preview && !following
    ? Object.keys(edits[editsKey(run.start.scenario, ui.model.value)] || {}).length
    : live.status?.run?.id === following && live.status.run.edited?.length));
  if (!run) return;
  if (run.preview) {
    const model = labels[ui.model.value] || ui.model.value;
    ui.sub.textContent = following ? `Model: ${model} · starting…` : `Model: ${model} · ready · press Play to run it`;
    return;
  }
  const model = labels[run.start.model] || run.start.model;
  if (!run.live) {
    ui.sub.textContent = summary(model, `Duration: ${fmtTime(run.duration)}`, replayEntry.messages, replayEntry.commands);
    return;
  }
  const s = live.status?.run;
  const state = run.ended ? `ended after ${fmtTime(run.duration)}: ${ENDINGS[run.endReason] || run.endReason}`
    : s?.state === "stopping" ? "stopping…" : `running for ${fmtTime(s ? s.elapsed : run.duration)}`;
  ui.sub.textContent = summary(model, `Live run, ${state}`, run.messages.length, run.events.filter((e) => e.type === "exec").length);
}

// Spelled out, so nobody has to guess what a bare "4 messages" counts.
const summary = (model, time, messages, commands) =>
  [`Model: ${model}`, time, `Messages exchanged: ${messages}`, `Shell commands run: ${commands}`].join(" · ");

// --- playback -------------------------------------------------------------------------

// The newest events of a live run that is still going: playback waits there for more.
const atLiveEdge = () => run.live && !run.ended;

function setPlaying(on) {
  if (on && run && p >= clock.length && !atLiveEdge()) seek(0);
  playing = on && !!run && !run.preview;
  lastFrame = performance.now();
  controls();
}

// Play/Pause, and in Live Stop and Clear. Play on a scenario's preview starts the run; Stop and
// Clear act on the server's run on screen (Clear: stop it if need be, and delete it, so the
// scenario is ready to run again).
function controls() {
  ui.play.classList.toggle("playing", playing);
  ui.play.setAttribute("aria-pressed", playing);
  ui.play.querySelector("span").textContent = playing ? "Pause" : "Play";
  const s = mode === "live" ? live.status : null;
  const going = !!s?.run && s.run.state !== "ended";
  if (mode === "live" && run?.preview) {
    ui.play.title = "Start the run";
    ui.play.disabled = !s || going || !!s.clearing || ui.model.selectedOptions[0]?.disabled !== false;
  } else {
    ui.play.title = playing ? "Pause (the run carries on)" : "Play";
    ui.play.disabled = !run;
  }
  // The server's run on screen, or still starting (its scenario's preview showing meanwhile).
  const shown = mode === "live" && !!run && !!s?.run && s.run.id === following;
  ui.stop.disabled = !shown || !going || s.run.state === "stopping";
  ui.clear.disabled = !shown || !!s.clearing;
}

// Jumping around never replays the messages passed over; only playback reaches them.
function seek(np) {
  p = Math.min(Math.max(np, 0), clock.length);
  world.advanceTo(clock.toRun(p));
  endSpot(false);
  nextMsg = run.messages.findIndex((m) => m.t > world.now);
  if (nextMsg < 0) nextMsg = run.messages.length;
  render();
}

function startSpot(m) {
  spot = { m, total: readingTime(m.text), used: 0 };
  spotlight.show(m, { n: run.messages.indexOf(m) + 1, of: run.messages.length });
}

// Retire the current message; show the next one queued at the same moment, if any.
function endSpot(advance = true) {
  spot = null;
  if (advance && queue.length) return startSpot(queue.shift());
  queue = [];
  spotlight.clear("");
}

function frame(now) {
  const dt = (now - lastFrame) / 1000;
  if (playing && run) {
    if (spot) {
      spot.used += dt * speed; // the reading time shrinks with the playback speed
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
      world.advanceTo(t);
      if (due) startSpot(queue.shift());
      render();
      if (p >= clock.length && !spot && !atLiveEdge()) setPlaying(false);
    }
  }
  lastFrame = now;
  requestAnimationFrame(frame);
}

function graphUpdate() {
  const pNow = p;
  graph.update(world, {
    focus: spot ? spot.m : null,
    // The spotlighted message's envelope crosses its link in FLIGHT_S (at 1×), then waits at the
    // recipient while the message is read (the run clock is held while it is up).
    flight: spot ? spot.used / Math.min(FLIGHT_S, spot.total) : 0,
    showCommand: (id) => {
      const n = world.node[id];
      return n.cmd && (world.stateOf(id) === "exec" || pNow - clock.toPlay(n.cmdT) < COMMAND_REAL_S * speed);
    },
  });
}

function render() {
  graphUpdate();
  panel.show(world);
  chart?.update(world.now);
  ui.scrub.max = clock.length;
  ui.scrub.value = p;
  ui.time.textContent = `${fmtTime(world.now)} / ${fmtTime(run.duration)}`;
  ui.catchUp.disabled = p >= clock.length - 0.01;
  ui.reports.disabled = world.now < run.duration - 0.5 || !run.reports.length;
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

// Skip: stop showing the current message and carry on from where it was sent (the next message
// still gets its turn in the spotlight).
function skipMessage() {
  if (!spot) return;
  endSpot();
  render();
}

function drawTicks() {
  ui.ticks.replaceChildren();
  for (const m of run.messages) {
    const i = document.createElement("i");
    i.style.background = run.ident.get(m.from).color;
    i.style.left = `${clock.length ? (clock.toPlay(m.t) / clock.length) * 100 : 0}%`;
    ui.ticks.append(i);
  }
}

// --- modes ----------------------------------------------------------------------------

async function setMode(m) {
  if (m === mode && (m === "replay" || live.connected)) return;
  mode = m;
  document.body.classList.toggle("live", m === "live");
  ui.modes.forEach((b) => b.setAttribute("aria-pressed", b.dataset.mode === m));
  setPlaying(false);
  if (m === "live") {
    history.replaceState(null, "", "#live");
    live.watch(true);
    clearStage("Live run", "Connecting to the demo server…");
    await connectLive();
  } else {
    // Keep an eye on the server (a run there carries on): the Live toggle shows it going.
    live.watch(false);
    runIndicator(live.status);
    delete ui.scenario.dataset.live;
    ui.scenario.disabled = ui.model.disabled = false;
    fillReplayScenarios();
    await openFromHash();
  }
}

// An empty stage, with a note where the graph goes: before a live run's events arrive.
function clearStage(title, note) {
  run = null;
  ui.stage.classList.add("no-run");
  endSpot(false);
  ui.svg.replaceChildren();
  ui.panel.querySelector(".panel-list").replaceChildren();
  ui.chart.hidden = true;
  ui.ticks.replaceChildren();
  ui.title.textContent = title;
  ui.sub.textContent = "";
  ui.time.textContent = "0:00 / 0:00";
  ui.scrub.value = 0;
  for (const b of [ui.next, ui.prev, ui.reports, ui.catchUp, $("#open-prompts")]) b.disabled = true;
  ui.scrub.disabled = true;
  notice(note);
  controls();
}

function enableTransport() {
  for (const b of [ui.next, ui.prev, $("#open-prompts")]) b.disabled = false;
  ui.scrub.disabled = false;
}

// A notice on the stage (empty text hides it); one ending in "…" says we're waiting, with a
// spinner. Over a drawn network it is a small badge in the drawing's bottom-right corner, out of
// the way; with nothing drawn, a card in the middle of the stage.
function notice(text) {
  ui.status.hidden = !text;
  const parts = [text || ""];
  if (text?.endsWith("…")) {
    const spin = document.createElement("span");
    spin.className = "spin";
    spin.setAttribute("aria-hidden", "true");
    parts.unshift(spin);
  }
  ui.status.replaceChildren(...parts);
  const corner = !!text && !!run && ui.svg.childElementCount > 0;
  ui.status.classList.toggle("corner", corner);
  if (!corner) {
    ui.status.style.top = ui.status.style.right = "";
    return;
  }
  // The stage scrolls, and an SVG element has no offsetTop: measure where the drawing is.
  const wrap = ui.status.offsetParent.getBoundingClientRect(), box = ui.svg.getBoundingClientRect();
  ui.status.style.top = `${box.bottom - wrap.top + ui.status.offsetParent.scrollTop - 8}px`;
  ui.status.style.right = `${wrap.right - box.right + 8}px`; // anchored right: it grows leftwards
}

// A scenario as a run would start: its topology and prompts, before (or while) starting it.
function showPreview(scenario) {
  const events = previews.get(scenario);
  setPlaying(false);
  if (!events) {
    clearStage(titleOf(scenario) || "Live run", "Preparing this scenario…");
    return;
  }
  // Each prompt as the chosen model's agents will get it: the attendee's edit, or the original.
  const { current } = promptsFor(scenario, ui.model.value);
  openRun(events.map((e) => (e.type === "prompt" ? { ...e, text: current.get(e.node) }
    : e.type === "run_start" && e.opening ? { ...e, opening: { ...e.opening, text: current.get(OPENING) } } : { ...e })));
  run.preview = true;
  // Editable until the run starts; a preview standing in while a run starts is not.
  if (!following) prompts.setRun(run, editorFor(scenario, ui.model.value));
  for (const b of [ui.next, ui.prev]) b.disabled = true;
  ui.scrub.disabled = true;
  subtitle();
  controls();
}

// --- edited prompts -------------------------------------------------------------------

function loadEdits() {
  try { return JSON.parse(localStorage.getItem(EDITS_KEY)) || {}; } catch { return {}; }
}

function saveEdits() {
  try { localStorage.setItem(EDITS_KEY, JSON.stringify(edits)); } catch { /* private mode: kept for this visit only */ }
}

const usesGuide = (model) => !!live.status?.models.find((m) => m.key === model)?.tool_guide;
const editsKey = (scenario, model) => `${scenario}|${usesGuide(model) ? "guide" : "plain"}`;

// A scenario's prompts and opening message on a model: as the paper has them (original), and as
// the run would get them (current: the attendee's edits on top). An agent with a set model
// (Celer's LegitAS) goes by its own model for the tool guide.
function promptsFor(scenario, model) {
  const events = previews.get(scenario) || [];
  const original = new Map();
  for (const e of events.filter((e) => e.type === "prompt")) {
    original.set(e.node, usesGuide(e.model || model) && e.tool_guide ? `${e.text}\n\n${e.tool_guide}` : e.text);
  }
  const opening = events[0]?.opening;
  if (opening) original.set(OPENING, opening.text);
  const mine = edits[editsKey(scenario, model)] || {};
  const current = new Map([...original].map(([id, text]) => [id, mine[id] ?? text]));
  return { original, current };
}

function editorFor(scenario, model) {
  const { original, current } = promptsFor(scenario, model);
  const key = editsKey(scenario, model);
  const store = () => {
    const changed = Object.fromEntries([...current].filter(([id, text]) => text !== original.get(id)));
    if (Object.keys(changed).length) edits[key] = changed;
    else delete edits[key];
    saveEdits();
    subtitle();
  };
  return {
    original, current,
    change(id, text) { current.set(id, text); store(); },
    reset(id) {
      for (const k of id === null ? [...original.keys()] : [id]) current.set(k, original.get(k));
      store();
    },
  };
}

// What Play sends: only what differs from the original.
function changedPrompts(scenario, model) {
  const { original, current } = promptsFor(scenario, model);
  const out = { prompts: {} };
  for (const [id, text] of current) {
    if (text === original.get(id)) continue;
    if (id === OPENING) out.opening = text;
    else out.prompts[id] = text;
  }
  return out;
}

async function loadPreviews(ids) {
  if (ids.every((id) => previews.has(id))) return;
  try {
    for (const [id, events] of Object.entries(await live.request("/api/scenarios"))) previews.set(id, events);
  } catch {
    return;
  }
  if (mode === "live") showChosenScenario();
}

// Nothing else on the stage (no run followed): show the chosen scenario as it would start.
function showChosenScenario() {
  if (following || (run && !run.preview)) return;
  if (run?.preview && run.start.scenario === ui.scenario.value) return; // already on screen
  if (previews.has(ui.scenario.value)) showPreview(ui.scenario.value);
}

// --- live -----------------------------------------------------------------------------

function savedPort() {
  try { return +localStorage.getItem("demo-port") || DEFAULT_PORT; } catch { return DEFAULT_PORT; }
}

async function connectLive() {
  const port = Math.round(+ui.port.value) || DEFAULT_PORT;
  ui.port.value = port;
  try { localStorage.setItem("demo-port", port); } catch { /* private mode: not remembered */ }
  ui.conn.textContent = `Connecting to localhost:${port}…`;
  ui.conn.className = "conn";
  liveModelsSig = "";
  following = null;
  if (await live.connect(port)) return;
  if (mode !== "live") return;
  liveStatus(null);
}

// Every poll of the server: the connection, the models' availability, and the run buttons.
// Whether a run is going on the server, wherever the page is: a pulsing dot on the Live toggle,
// and in Live a "Running" pill by the title. The dropdowns lock meanwhile, and say why.
function runIndicator(status) {
  const r = status?.run;
  const going = !!r && r.state !== "ended";
  ui.modes.find((b) => b.dataset.mode === "live").classList.toggle("running", going);
  ui.modes.find((b) => b.dataset.mode === "live").title = going ? "A run is going on the demo server" : "";
  ui.pill.hidden = !(mode === "live" && going);
  if (!ui.pill.hidden) ui.pill.textContent = r.state === "stopping" ? "Stopping…" : `Running ${fmtTime(r.elapsed)}`;
  const why = mode === "live" && going ? "Locked while a run is going: Stop or Clear it first" : "";
  ui.scenario.title = ui.model.title = why;
}

function liveStatus(status) {
  runIndicator(status);
  if (mode !== "live") return;
  const port = ui.port.value;
  if (!status) {
    ui.conn.textContent = `Not connected (nothing answers on localhost:${port})`;
    ui.conn.className = "conn bad";
    ui.recheck.disabled = true;
    controls();
    if (!run) {
      notice("No demo server is running on this machine at that port. " +
        "See “How to start the server”, or connect to another port.");
    }
    return;
  }
  ui.conn.textContent = `Connected to localhost:${port}${status.fake ? " (fake runs)" : ""}`;
  ui.conn.className = "conn ok";

  if (ui.scenario.dataset.live !== "1") {
    const titles = new Map(index.runs.map((r) => [r.scenario, r.title]));
    ui.scenario.replaceChildren(...status.scenarios.map((id) => new Option(titles.get(id) || id, id)));
    ui.scenario.dataset.live = "1";
  }
  // Rebuild the model list only when something changed: rebuilding closes it under the cursor.
  const sig = JSON.stringify([status.models, status.checking]);
  if (sig !== liveModelsSig) {
    liveModelsSig = sig;
    const keep = ui.model.value;
    ui.model.replaceChildren(...status.models.map((m) => {
      const mark = status.checking && m.ok === null ? "…" : m.ok ? "✓" : m.ok === false ? "✗" : "?";
      const o = new Option(`${mark} ${m.label}`, m.key);
      o.disabled = m.ok === false;
      o.title = m.ok === false ? m.error : m.ok ? "Answered the last check" : "Not checked yet";
      return o;
    }));
    const usable = status.models.filter((m) => m.ok !== false).map((m) => m.key);
    ui.model.value = usable.includes(keep) ? keep : usable[0] || status.models[0].key;
    for (const m of status.models) labels[m.key] = m.label;
  }
  ui.recheck.disabled = status.checking;
  ui.recheck.textContent = status.checking ? "Checking models…" : "Recheck";

  const going = status.run && status.run.state !== "ended";
  ui.scenario.disabled = ui.model.disabled = !!going || status.clearing;
  if (following && !status.run) {
    // The run on screen was cleared (here or from another page): back to the scenario.
    following = null;
    livePending = [];
    showPreview(ui.scenario.value);
  }
  if (going) {
    ui.scenario.value = status.run.scenario;
    ui.model.value = status.run.model;
  }
  loadPreviews(status.previews);
  showChosenScenario();
  if (!run && !following) {
    notice("Preparing the scenarios…");
  }
  subtitle();
  controls();
}

// A run to follow: a new one, or the one going (or last finished) when we connected. Its
// scenario's preview stays on screen until the run's own events arrive.
function liveRun(r) {
  livePending = [];
  following = r.id;
  autoplay = startedHere;
  startedHere = false;
  ui.scenario.value = r.scenario;
  ui.model.value = r.model;
  showPreview(r.scenario);
  notice(r.state === "ended" ? "Loading the last run…" : "Building the network and starting the agents…");
}

function liveEvents(events) {
  if (mode !== "live") return;
  if (!run || run.preview) {
    livePending.push(...events);
    if (livePending[0]?.type !== "run_start") {
      // The run ended before it got going (e.g. Docker failed): there is nothing to show.
      const end = livePending.find((e) => e.type === "run_end");
      if (end && end.reason === "stopped") {
        following = null; // nothing of it to show: back to the scenario, ready to run
        subtitle();
        controls();
        notice("Stopped before the network was up.");
      } else if (end) {
        ui.title.textContent = "The run did not start";
        notice(`It ended (${ENDINGS[end.reason] || end.reason}) before the network was up. ` +
          "The server's terminal, and run.out in the run's folder under demo/logs/, say why.");
      }
      return;
    }
    openRun(livePending);
    livePending = [];
    setPlaying(autoplay);
    return;
  }
  // Keep the position (in run time) while the run grows under it.
  const t = clock.toRun(p);
  const wasEnded = run.ended;
  const before = { pseudo: run.pseudo.size, idle: run.startIdle.size, prompts: prompts.ids?.length, metrics: run.metrics.length };
  run.events.push(...events);
  indexRun(run);
  if (run.pseudo.size !== before.pseudo) {
    // Someone outside the network appeared (the laptop owner): redraw with them.
    run.ident = identities(run);
    spotlight.ident = run.ident;
    graph = new Graph(ui.svg, run, { onSelect: openPrompts });
  }
  if (run.pseudo.size !== before.pseudo || run.startIdle.size !== before.idle) {
    // Who is there, or who starts asleep, became known only now: rebuild the state from the start.
    world = new World(run);
    world.advanceTo(t);
  }
  prompts.setRun(run);
  if (prompts.ids.length !== before.prompts) $("#open-prompts").disabled = !prompts.available;
  panel.refeed();
  if (run.metrics.length !== before.metrics) {
    chart = new ThroughputChart(ui.chart, run.metrics, run.ident);
    ui.chart.hidden = false;
  }
  ui.spot.hidden = !run.messages.length && !scenarioHasMessages(run.start.scenario);
  clock = new Clock(run, PAUSE_CAP_S);
  p = clock.toPlay(t);
  drawTicks();
  subtitle();
  render();
  controls();
  if (run.ended && !wasEnded) live.poll(); // Play starts a new run again: don't wait for the next poll
}

async function liveAction(action) {
  try {
    await action();
  } catch (err) {
    notice(`The server said: ${err.message}`);
  }
}

// --- prompts --------------------------------------------------------------------------

// The replay pauses while the prompts are open, and picks up again when they close.
function openPrompts(id) {
  if (!prompts.available) return;
  if (id && run.pseudo.has(id)) id = OPENING; // the person: their message
  if (!$("#prompts").open) resumeAfterPrompts = playing;
  setPlaying(false);
  prompts.open(id);
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

ui.scenario.addEventListener("change", () => {
  if (mode === "replay") { fillModels(ui.model.value); load(); return; }
  following = null; // looking at another scenario: the last run gives way to its preview
  showPreview(ui.scenario.value);
});
ui.model.addEventListener("change", () => {
  if (mode === "replay") return load();
  following = null; // its prompts depend on the model (the tool guide): show it afresh
  showPreview(ui.scenario.value);
  subtitle();
  controls(); // Play follows the chosen model's availability
});
ui.modes.forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
ui.connect.addEventListener("click", connectLive);
ui.port.addEventListener("keydown", (ev) => { if (ev.key === "Enter") connectLive(); });
ui.recheck.addEventListener("click", () => liveAction(() => live.recheck()));
ui.stop.addEventListener("click", () => liveAction(() => live.stop()));
ui.clear.addEventListener("click", () => liveAction(() => live.clear()));
// To the newest event; a run still going carries on playing from there, a finished one stays at its end.
ui.catchUp.addEventListener("click", () => {
  if (!run) return;
  seek(clock.length);
  setPlaying(atLiveEdge());
});
$("#open-help").addEventListener("click", () => $("#help").showModal());
$("#help .close").addEventListener("click", () => $("#help").close());
ui.play.addEventListener("click", () => {
  if (mode === "live" && run?.preview) {
    startedHere = true;
    const { prompts: edited, opening } = changedPrompts(ui.scenario.value, ui.model.value);
    return liveAction(() => live.start(ui.scenario.value, ui.model.value, edited, opening)).finally(() => { startedHere = false; });
  }
  setPlaying(!playing);
});
ui.speed.addEventListener("change", () => (speed = +ui.speed.value));
ui.scrub.addEventListener("input", () => { if (run) seek(+ui.scrub.value); });
ui.next.addEventListener("click", () => jumpMessage(1));
ui.prev.addEventListener("click", () => jumpMessage(-1));
$("#skip-msg").addEventListener("click", skipMessage);
ui.reports.addEventListener("click", openReports);
window.addEventListener("hashchange", () => {
  if (!index) return;
  if (location.hash === "#live") setMode("live");
  else if (mode === "live") setMode("replay");
  else if (location.hash !== `#${ui.scenario.value}/${ui.model.value}`) openFromHash();
});
$("#close-reports").addEventListener("click", () => ui.dialog.close());
$("#open-prompts").addEventListener("click", () => openPrompts());
$("#prompts .close").addEventListener("click", () => $("#prompts").close());
$("#prompts").addEventListener("close", () => { if (resumeAfterPrompts) setPlaying(true); resumeAfterPrompts = false; });
document.addEventListener("keydown", (ev) => {
  // Form controls keep their own keys (arrows move the slider, space toggles a checkbox);
  // a focused button already turns space into a click.
  if (ev.target.closest("select, input, dialog") || ev.ctrlKey || ev.metaKey || ev.altKey) return;
  if (ev.key === " " && ev.target.closest("button, summary")) return;
  if (ev.key === " ") { ev.preventDefault(); setPlaying(!playing); }
  else if (ev.key === "ArrowRight") jumpMessage(1);
  else if (ev.key === "ArrowLeft") jumpMessage(-1);
  else if (ev.key === "Enter" && !ev.target.closest("button, a, summary")) skipMessage();
});

for (const svg of document.querySelectorAll(".lg-mark")) appendMark(svg, {}, svg.dataset.show);
init();
requestAnimationFrame(frame);
