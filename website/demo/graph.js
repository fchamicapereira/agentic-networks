// Topology graph: layered layout (providers above customers, peers side by side, as in the
// paper's figures) drawn as SVG, plus per-frame updates for node state, the command each agent is running, and
// messages travelling along links. Each node is a box in the node's own colour.

const SVG = "http://www.w3.org/2000/svg";
const NODE_W = 116, NODE_H = 44, GAP_X = 190, GAP_Y = 118, PAD = 64;
const ENVELOPE_R = 11; // half the envelope's width, plus a little air
const CMD_CHARS = 21; // a command under its node is cut to roughly the space between nodes
const PSEUDO_LABEL = { human: "Laptop owner" };

// A cogwheel centred on (0, 0): `teeth` teeth between radii r and R, and a hole of radius h.
export function cogPath(R = 7.5, r = 5.6, h = 2.4, teeth = 8) {
  const pt = (rad, a) => `${(rad * Math.cos(a)).toFixed(2)},${(rad * Math.sin(a)).toFixed(2)}`;
  const step = (2 * Math.PI) / teeth, d = [];
  for (let i = 0; i < teeth; i++) {
    const a = i * step;
    d.push(pt(r, a - step * 0.32), pt(R, a - step * 0.2), pt(R, a + step * 0.2), pt(r, a + step * 0.32));
  }
  return `M${d.join("L")}Z M${h},0 A${h},${h} 0 1 0 ${-h},0 A${h},${h} 0 1 0 ${h},0Z`;
}

// The state mark: a disc holding one symbol per state — a turning cog (working: thinking or
// running a command), "zzz" (idle). CSS shows the one for the node's state; `show` picks one
// outright, for the legend.
export function appendMark(parent, attrs = {}, show = "") {
  const g = el("g", { ...attrs, class: "mark", "data-show": show }, parent);
  el("circle", { r: 14 }, g);
  el("path", { class: "sym cog", d: cogPath(10, 7.4, 3.2), "fill-rule": "evenodd" }, g);
  const zzz = el("g", { class: "sym zzz" }, g);
  for (const [x, y, size] of [[-6, 8, 10], [0, 3.5, 12], [6, -1.5, 14]]) el("text", { x, y, "font-size": size }, zzz).textContent = "z";
  return g;
}

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

// Hand-drawn layouts, as [column, row], used when they cover every node of a run. All read
// left to right along the traffic's path: the knowledge-plane topology from the user to the web
// server, Celer Bridge from TinyInc to AWS (with LegitAS hanging off TransitAS, as EveLink does
// off AS1), billing from TinyInc to Remote over either transit.
const FIXED = [
  { User: [0, 0], Uni: [1, 0], AS1: [2, 0], AS2: [3, 0], ACM: [4, 0], Web: [5, 0], EveLink: [2, 1], human: [0, 1] },
  { TinyInc: [0, 0], ISP: [1, 0], TransitAS: [2, 0], Tier1: [3, 0], AWS: [4, 0], LegitAS: [2, 1] },
  { TinyInc: [0, 0.5], ISP: [1, 0.5], Expensive: [2, 0], Cheap: [2, 1], Remote: [3, 0.5] },
];

// Small graphs: try every ordering within each level and keep the one with the fewest
// crossings and shortest links. Falls back to input order if that would be too many.
export function layout(run) {
  const edges = run.topo.links.map((l) => [l.a, l.b]);
  for (const [p, attach] of run.pseudo) edges.push([p, attach]);
  const ids = [...run.nodes, ...run.pseudo.keys()];
  const fixed = FIXED.find((f) => ids.every((id) => id in f));
  if (fixed) return { pos: new Map(ids.map((id) => [id, { x: fixed[id][0] * GAP_X, y: fixed[id][1] * GAP_Y }])), edges };

  const level = levels(run);

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

    // While a message is in the spotlight, its link is lit up underneath in the sender's colour.
    this.focusLine = el("line", { class: "focus-link", style: "display:none" }, svg);
    // Links are plain lines: who is whose provider or peer is left out of the picture. The
    // owner's link to their laptop (a pseudo-node) is dashed, since it is not a network link.
    const gEdges = el("g", { class: "edges" }, svg);
    const links = new Set(run.topo.links.map((l) => `${l.a}|${l.b}`));
    this.edgeEls = new Map(); // "a|b" and "b|a" -> line
    for (const [a, b] of edges) {
      const p1 = pos.get(a), p2 = pos.get(b);
      const s = boxExit(p1, p2.x, p2.y), e = boxExit(p2, p1.x, p1.y);
      const line = el("line", { x1: s.x, y1: s.y, x2: e.x, y2: e.y, class: links.has(`${a}|${b}`) ? "edge" : "edge pseudo" }, gEdges);
      this.edgeEls.set(`${a}|${b}`, line).set(`${b}|${a}`, line);
    }

    this.gMsgs = el("g", { class: "msgs" }, svg);
    const gNodes = el("g", { class: "nodes" }, svg);
    this.nodeEls = new Map();
    for (const [id, p] of pos) {
      const isPseudo = run.pseudo.has(id);
      const { color } = run.ident.get(id);
      const name = isPseudo ? PSEUDO_LABEL[id] || id : id;
      const g = el("g", { class: `node${isPseudo ? " pseudo" : ""}`, transform: `translate(${p.x},${p.y})`, style: `--c:${color}`, "aria-label": isPseudo ? name : `Agent ${id}` }, gNodes);
      if (isPseudo) {
        // A person outside the network (the laptop owner): a figure, not an agent's box.
        el("circle", { class: "person", cy: -13, r: 12 }, g);
        el("path", { class: "person", d: "M-21,26 a21,21 0 0 1 42,0 Z" }, g);
      } else {
        el("rect", { class: "box", x: -NODE_W / 2, y: -NODE_H / 2, width: NODE_W, height: NODE_H, rx: 9 }, g);
        el("text", { class: "label", y: 1 }, g).textContent = name;
      }
      const status = el("text", { class: "status", y: NODE_H / 2 + 16 }, g);
      const tip = el("title", {}, g);
      if (isPseudo) tip.textContent = name;
      // The state mark sits on the box's top-left corner.
      if (!isPseudo) appendMark(g, { transform: `translate(${-NODE_W / 2 + 2},${-NODE_H / 2 + 2})` });
      // Clicking an agent opens its system prompt; clicking the person, their message.
      g.setAttribute("tabindex", 0);
      g.setAttribute("role", "button");
      g.addEventListener("click", () => onSelect?.(id));
      g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); ev.stopPropagation(); onSelect?.(id); } });
      this.nodeEls.set(id, { g, status, tip, isPseudo });
    }
    this.envelope = el("g", { class: "dot", style: "display:none" }, this.gMsgs);
    el("rect", { x: -9, y: -6.5, width: 18, height: 13, rx: 2 }, this.envelope);
    el("path", { d: "M-9,-6.5 L0,1 L9,-6.5" }, this.envelope);
  }

  // world: World at the current time. opts: { focus (the spotlighted message, or null),
  // flight (0..1, how far its envelope has got), showCommand(id) -> whether the node's latest
  // command is still worth showing }
  update(world, { focus, flight, showCommand }) {
    // While a message is in the spotlight, its link stands out as an arrow in the sender's colour.
    // Nodes are not dimmed: fading is reserved for idle agents.
    this.svg.classList.toggle("focusing", !!focus);
    if (focus) this.svg.style.setProperty("--msg-c", this.run.ident.get(focus.from).color);
    const focusEdge = focus ? this.edgeEls.get(`${focus.from}|${focus.to}`) : null;
    for (const line of new Set(this.edgeEls.values())) line.classList.toggle("focus", line === focusEdge);
    const a = focus && this.pos.get(focus.from), b = focus && this.pos.get(focus.to);
    let s, e;
    if (a && b) {
      s = boxExit(a, b.x, b.y);
      e = boxExit(b, a.x, a.y);
      for (const [k, v] of Object.entries({ x1: s.x, y1: s.y, x2: e.x, y2: e.y })) this.focusLine.setAttribute(k, v);
      this.focusLine.style.display = "";
    } else {
      this.focusLine.style.display = "none";
    }
    for (const [id, n] of this.nodeEls) {
      const state = n.isPseudo ? "waiting" : world.stateOf(id);
      n.g.dataset.state = state;
      const w = world.node[id];
      // The line under a node: its state, or the command it is running.
      const cmd = !n.isPseudo && showCommand(id) ? w.cmd : null;
      n.status.classList.toggle("cmd", !!cmd);
      n.status.textContent = cmd
        ? "$ " + (cmd.length > CMD_CHARS ? cmd.slice(0, CMD_CHARS - 1) + "…" : cmd)
        : "";
      if (!n.isPseudo) n.tip.textContent = cmd ? `${id}: $ ${cmd}` : `${id} (${state})`;
    }

    // The spotlighted message: an envelope flies from the sender's box edge to the recipient's,
    // then waits there until the message is dismissed. It never covers either box. No other
    // message is drawn, so each one travels exactly once.
    const f = focus && a && b ? Math.min(Math.max(flight, 0), 1) : null;
    this.envelope.style.display = f === null ? "none" : "";
    if (f !== null) {
      // Inset by half the envelope, so it starts and parks just clear of the boxes.
      const len = Math.hypot(e.x - s.x, e.y - s.y), inset = Math.min(ENVELOPE_R, len / 2);
      const ux = len ? (e.x - s.x) / len : 0, uy = len ? (e.y - s.y) / len : 0;
      const x0 = s.x + ux * inset, y0 = s.y + uy * inset, x1 = e.x - ux * inset, y1 = e.y - uy * inset;
      const k = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2; // ease in-out
      this.envelope.style.setProperty("--c", this.run.ident.get(focus.from).color);
      this.envelope.setAttribute("transform", `translate(${x0 + (x1 - x0) * k},${y0 + (y1 - y0) * k})`);
    }
  }
}
