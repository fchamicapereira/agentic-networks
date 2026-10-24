// Topology graph: layered layout (providers above customers, peers side by side, as in the
// paper's figures) drawn as SVG, plus per-frame updates for node state, the command each agent is running, and
// messages travelling along links.

const SVG = "http://www.w3.org/2000/svg";
const NODE_W = 116, NODE_H = 44, GAP_X = 170, GAP_Y = 118, PAD = 64;
const CMD_CHARS = 21; // a command under its node is cut to roughly the space between nodes
const PSEUDO_LABEL = { human: "Laptop owner" };

function el(name, attrs = {}, parent) {
  const e = document.createElementNS(SVG, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

// --- layout -----------------------------------------------------------------------

function levels(run) {
  const ids = run.nodes;
  const providers = new Map(ids.map((id) => [id, []]));
  const group = new Map(ids.map((id) => [id, id]));
  const find = (x) => (group.get(x) === x ? x : find(group.get(x)));
  for (const l of run.topo.links) {
    const [ra] = l.rel.split("/");
    if (ra === "customer") providers.get(l.a).push(l.b);
    else if (ra === "provider") providers.get(l.b).push(l.a);
    else group.set(find(l.a), find(l.b)); // peers share a level
  }
  const members = new Map();
  for (const id of ids) {
    const g = find(id);
    if (!members.has(g)) members.set(g, []);
    members.get(g).push(id);
  }
  const memo = new Map(), visiting = new Set();
  const levelOf = (g) => {
    if (memo.has(g)) return memo.get(g);
    if (visiting.has(g)) return 0; // relationship cycle: give up gracefully
    visiting.add(g);
    let lv = 0;
    for (const m of members.get(g)) for (const p of providers.get(m)) lv = Math.max(lv, levelOf(find(p)) + 1);
    visiting.delete(g);
    memo.set(g, lv);
    return lv;
  };
  const level = new Map(ids.map((id) => [id, levelOf(find(id))]));
  // Pseudo-nodes sit beside the agent they talk to, not on a row of their own.
  for (const [p, attach] of run.pseudo) level.set(p, level.get(attach) ?? 0);
  return level;
}

function permutations(arr) {
  if (arr.length <= 1) return [arr];
  const out = [];
  arr.forEach((x, i) => {
    for (const rest of permutations([...arr.slice(0, i), ...arr.slice(i + 1)])) out.push([x, ...rest]);
  });
  return out;
}

// Small graphs: try every ordering within each level and keep the one with the fewest
// crossings and shortest links. Falls back to input order if that would be too many.
export function layout(run) {
  const level = levels(run);
  const edges = run.topo.links.map((l) => [l.a, l.b]);
  for (const [p, attach] of run.pseudo) edges.push([p, attach]);

  const byLevel = [];
  for (const [id, lv] of level) (byLevel[lv] ||= []).push(id);
  const rows = byLevel.map((r) => r || []);
  const choices = rows.map((r) => (r.length <= 6 ? permutations(r) : [r]));
  const combos = choices.reduce((n, c) => n * c.length, 1);

  const place = (order) => {
    const pos = new Map();
    order.forEach((row, lv) => row.forEach((id, i) => pos.set(id, { x: (i - (row.length - 1) / 2) * GAP_X, y: lv * GAP_Y, lv, i })));
    return pos;
  };
  const cost = (pos) => {
    let c = 0;
    for (const [a, b] of edges) {
      const pa = pos.get(a), pb = pos.get(b);
      c += Math.abs(pa.x - pb.x) / GAP_X;
      if (pa.lv === pb.lv && Math.abs(pa.i - pb.i) > 1) c += 20; // peer link through a node
    }
    for (let i = 0; i < edges.length; i++) {
      for (let j = i + 1; j < edges.length; j++) {
        const [a, b] = edges[i].map((n) => pos.get(n)), [c2, d] = edges[j].map((n) => pos.get(n));
        const [ta, ba] = a.lv <= b.lv ? [a, b] : [b, a], [tc, bc] = c2.lv <= d.lv ? [c2, d] : [d, c2];
        if (ta.lv === tc.lv && ba.lv === bc.lv && ta.lv !== ba.lv && (ta.x - tc.x) * (ba.x - bc.x) < 0) c += 10;
      }
    }
    return c;
  };

  let best = rows, bestCost = Infinity;
  if (combos <= 50000) {
    const walk = (lv, acc) => {
      if (lv === rows.length) {
        const c = cost(place(acc));
        if (c < bestCost) { bestCost = c; best = acc.slice(); }
        return;
      }
      for (const ch of choices[lv]) { acc.push(ch); walk(lv + 1, acc); acc.pop(); }
    };
    walk(0, []);
  }
  return { pos: place(best), edges };
}

// Point where the segment from the centre of a node box towards (tx, ty) leaves the box.
function boxExit(c, tx, ty, w = NODE_W, h = NODE_H) {
  const dx = tx - c.x, dy = ty - c.y;
  if (!dx && !dy) return { x: c.x, y: c.y };
  const s = Math.min(dx ? (w / 2 + 4) / Math.abs(dx) : Infinity, dy ? (h / 2 + 4) / Math.abs(dy) : Infinity);
  return { x: c.x + dx * s, y: c.y + dy * s };
}

// --- rendering ----------------------------------------------------------------------

export class Graph {
  constructor(svg, run, { onSelect } = {}) {
    this.svg = svg;
    this.run = run;
    svg.replaceChildren();
    const { pos, edges } = layout(run);
    this.pos = pos;

    const xs = [...pos.values()].map((p) => p.x), ys = [...pos.values()].map((p) => p.y);
    const minX = Math.min(...xs) - NODE_W / 2 - PAD, maxX = Math.max(...xs) + NODE_W / 2 + PAD;
    const minY = Math.min(...ys) - NODE_H / 2 - PAD * 0.8, maxY = Math.max(...ys) + NODE_H / 2 + PAD * 0.8;
    svg.setAttribute("viewBox", `${minX} ${minY} ${maxX - minX} ${maxY - minY}`);

    const defs = el("defs", {}, svg);
    // userSpaceOnUse: arrowheads keep their size when a link is drawn thicker (focus).
    const marker = el("marker", { id: "arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 11, markerHeight: 11, markerUnits: "userSpaceOnUse", orient: "auto-start-reverse" }, defs);
    el("path", { d: "M0,0 L10,5 L0,10 z", class: "arrowhead" }, marker);
    const msgMarker = el("marker", { id: "msg-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 16, markerHeight: 16, markerUnits: "userSpaceOnUse", orient: "auto" }, defs);
    el("path", { d: "M0,0 L10,5 L0,10 z", class: "msg-arrowhead" }, msgMarker);

    const gEdges = el("g", { class: "edges" }, svg);
    const rel = new Map(run.topo.links.map((l) => [`${l.a}|${l.b}`, l.rel]));
    this.edgeEls = new Map(); // "a|b" and "b|a" -> line
    for (const [a, b] of edges) {
      const r = rel.get(`${a}|${b}`) || "pseudo";
      // Arrow points from provider to customer.
      const [from, to] = r === "customer/provider" ? [b, a] : [a, b];
      const p1 = pos.get(from), p2 = pos.get(to);
      const s = boxExit(p1, p2.x, p2.y), e = boxExit(p2, p1.x, p1.y);
      const cls = r === "peer/peer" ? "edge peer" : r === "pseudo" ? "edge pseudo" : "edge transit";
      const line = el("line", { x1: s.x, y1: s.y, x2: e.x, y2: e.y, class: cls }, gEdges);
      if (cls === "edge transit") line.setAttribute("marker-end", "url(#arrow)");
      this.edgeEls.set(`${a}|${b}`, line).set(`${b}|${a}`, line);
    }

    // While a message is in the spotlight, its link is redrawn as an arrow in the direction the
    // message travels (the link's own arrow shows the business relationship, not the message).
    this.focusLine = el("line", { class: "focus-arrow", "marker-end": "url(#msg-arrow)", style: "display:none" }, svg);
    this.gMsgs = el("g", { class: "msgs" }, svg);
    const gNodes = el("g", { class: "nodes" }, svg);
    this.nodeEls = new Map();
    for (const [id, p] of pos) {
      const isPseudo = run.pseudo.has(id);
      const g = el("g", { class: `node${isPseudo ? " pseudo" : ""}`, transform: `translate(${p.x},${p.y})`, tabindex: 0, role: "button", "aria-label": `Agent ${id}` }, gNodes);
      el("rect", { class: "halo", x: -NODE_W / 2 - 6, y: -NODE_H / 2 - 6, width: NODE_W + 12, height: NODE_H + 12, rx: 14 }, g);
      el("rect", { class: "box", x: -NODE_W / 2, y: -NODE_H / 2, width: NODE_W, height: NODE_H, rx: 9 }, g);
      const label = el("text", { class: "label", y: 1 }, g);
      label.textContent = isPseudo ? PSEUDO_LABEL[id] || id : id;
      const status = el("text", { class: "status", y: NODE_H / 2 + 16 }, g);
      const tip = el("title", {}, g);
      const inbox = el("g", { class: "inbox", transform: `translate(${NODE_W / 2 - 2},${-NODE_H / 2 + 2})` }, g);
      el("circle", { r: 10 }, inbox);
      const inboxN = el("text", { y: 4 }, inbox);
      if (!isPseudo) {
        g.addEventListener("click", () => onSelect?.(id));
        g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); onSelect?.(id); } });
      }
      this.nodeEls.set(id, { g, status, tip, inbox, inboxN, isPseudo });
    }
    this.dots = new Map();
  }

  // world: World at the current time. opts: { level, selected, focus (message or null),
  // travel(m) -> 0..1 progress,
  // showCommand(id) -> whether the node's latest command is still worth showing }
  update(world, { level, selected, focus, travel, showCommand }) {
    // While a message is in the spotlight, its sender, recipient, and link stand out.
    this.svg.classList.toggle("focusing", !!focus);
    const focusEdge = focus ? this.edgeEls.get(`${focus.from}|${focus.to}`) : null;
    for (const line of new Set(this.edgeEls.values())) line.classList.toggle("focus", line === focusEdge);
    const a = focus && this.pos.get(focus.from), b = focus && this.pos.get(focus.to);
    if (a && b) {
      const s = boxExit(a, b.x, b.y), e = boxExit(b, a.x, a.y);
      for (const [k, v] of Object.entries({ x1: s.x, y1: s.y, x2: e.x, y2: e.y })) this.focusLine.setAttribute(k, v);
      this.focusLine.style.display = "";
    } else {
      this.focusLine.style.display = "none";
    }
    for (const [id, n] of this.nodeEls) {
      const state = n.isPseudo ? "waiting" : world.stateOf(id);
      n.g.dataset.state = state;
      n.g.classList.toggle("selected", id === selected);
      n.g.classList.toggle("focus", !!focus && (id === focus.from || id === focus.to));
      const w = world.node[id];
      // The line under a node: its state, or (from "Actions" up) the command it is running.
      const cmd = !n.isPseudo && level >= 2 && showCommand(id) ? w.cmd : null;
      n.status.classList.toggle("cmd", !!cmd);
      n.status.textContent = cmd
        ? "$ " + (cmd.length > CMD_CHARS ? cmd.slice(0, CMD_CHARS - 1) + "…" : cmd)
        : n.isPseudo ? "" : state === "dormant" ? "idle" : state === "thinking" ? "thinking…" : state === "exec" ? "running a command" : "";
      n.tip.textContent = cmd ? `${id}: $ ${cmd}` : n.isPseudo ? "" : `${id} (${state})`;
    }

    // Messages: travel along the link, then wait as an unread envelope at the recipient.
    const flying = world.inFlight();
    const waiting = new Map();
    const live = new Set();
    for (const m of flying) {
      const f = travel(m);
      if (f >= 1) { waiting.set(m.to, (waiting.get(m.to) || 0) + 1); continue; }
      live.add(m.id);
      let dot = this.dots.get(m.id);
      if (!dot) {
        dot = el("g", { class: `dot${this.run.pseudo.has(m.from) ? " human" : ""}` }, this.gMsgs);
        el("rect", { x: -9, y: -6.5, width: 18, height: 13, rx: 2 }, dot);
        el("path", { d: "M-9,-6.5 L0,1 L9,-6.5" }, dot);
        this.dots.set(m.id, dot);
      }
      const a = this.pos.get(m.from), b = this.pos.get(m.to);
      if (!a || !b) continue;
      const e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2; // ease in-out
      dot.setAttribute("transform", `translate(${a.x + (b.x - a.x) * e},${a.y + (b.y - a.y) * e})`);
    }
    for (const [id, dot] of this.dots) if (!live.has(id)) { dot.remove(); this.dots.delete(id); }
    for (const [id, n] of this.nodeEls) {
      const k = waiting.get(id) || 0;
      n.inbox.style.display = k ? "" : "none";
      if (k) n.inboxN.textContent = k;
    }
  }
}
