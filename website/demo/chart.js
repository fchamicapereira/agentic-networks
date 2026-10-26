// Billing scenario: throughput per transit over simulated days, revealed up to the replay's
// current time. Two series on one axis, legend + direct end labels, crosshair tooltip.

import { redact } from "./state.js";

const SVG = "http://www.w3.org/2000/svg";
const W = 640, H = 170, M = { l: 44, r: 92, t: 12, b: 26 };

function el(name, attrs = {}, parent) {
  const e = document.createElementNS(SVG, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

export class ThroughputChart {
  constructor(root, metrics, ident) {
    this.root = root;
    this.samples = metrics.filter((m) => m.name === "throughput_mbps");
    this.series = [...new Set(this.samples.flatMap((s) => Object.keys(s.values)))];
    // A "via_X" series takes transit X's node colour; the rest keep the default series colours.
    const color = (s) => ident?.get(s.replace(/^via_/, ""))?.color;
    root.style.removeProperty("--s1");
    root.style.removeProperty("--s2");
    this.series.slice(0, 2).forEach((s, i) => { if (color(s)) root.style.setProperty(`--s${i + 1}`, color(s)); });
    const prefix = this.samples[0]?.prefix;
    const maxDay = Math.max(...this.samples.map((s) => s.sim_days));
    const maxV = Math.max(...this.samples.flatMap((s) => Object.values(s.values)));
    this.x = (d) => M.l + (d / maxDay) * (W - M.l - M.r);
    this.yMax = Math.ceil(maxV / 100) * 100 || 100;
    this.y = (v) => H - M.b - (v / this.yMax) * (H - M.t - M.b);

    root.replaceChildren();
    const title = document.createElement("div");
    title.className = "chart-title";
    title.textContent = `Traffic to ${prefix || "Remote"} by transit link (Mbps), over simulated days`;
    const legend = document.createElement("div");
    legend.className = "chart-legend";
    this.series.forEach((s, i) => {
      const item = document.createElement("span");
      const sw = document.createElement("i");
      sw.className = `sw s${i + 1}`;
      item.append(sw, document.createTextNode(s.replace("via_", "via ")));
      legend.append(item);
    });
    root.append(title, legend);

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", "aria-label": title.textContent });
    root.append(svg);
    const grid = el("g", { class: "grid" }, svg);
    for (let v = 0; v <= this.yMax; v += this.yMax / 4) {
      el("line", { x1: M.l, x2: W - M.r, y1: this.y(v), y2: this.y(v) }, grid);
      el("text", { x: M.l - 6, y: this.y(v) + 4, class: "tick", "text-anchor": "end" }, grid).textContent = v;
    }
    const step = maxDay > 20 ? 5 : 2;
    for (let d = 0; d <= maxDay + 1e-9; d += step) {
      el("text", { x: this.x(d), y: H - 8, class: "tick", "text-anchor": "middle" }, grid).textContent = `day ${d}`;
    }
    this.paths = this.series.map((_, i) => el("path", { class: `line s${i + 1}` }, svg));
    this.ends = this.series.map((s, i) => el("text", { class: "end-label", "text-anchor": "start" }, svg));
    this.cross = el("line", { class: "crosshair", y1: M.t, y2: H - M.b, style: "display:none" }, svg);
    this.markers = this.series.map((_, i) => el("circle", { r: 4, class: `marker s${i + 1}`, style: "display:none" }, svg));
    this.tip = document.createElement("div");
    this.tip.className = "tooltip";
    this.tip.hidden = true;
    root.append(this.tip);
    this.visible = [];

    const hit = el("rect", { x: M.l, y: M.t, width: W - M.l - M.r, height: H - M.t - M.b, fill: "transparent" }, svg);
    hit.addEventListener("pointermove", (ev) => this.hover(svg, ev));
    hit.addEventListener("pointerleave", () => this.hover(svg, null));
  }

  update(now) {
    const vis = this.samples.filter((s) => s.t <= now);
    if (vis.length === this.visible.length) return;
    this.visible = vis;
    this.series.forEach((s, i) => {
      const d = vis.map((p, k) => `${k ? "L" : "M"}${this.x(p.sim_days).toFixed(1)},${this.y(p.values[s] ?? 0).toFixed(1)}`).join("");
      this.paths[i].setAttribute("d", d);
      const last = vis[vis.length - 1];
      if (last) {
        this.ends[i].setAttribute("x", this.x(last.sim_days) + 8);
        this.ends[i].setAttribute("y", this.y(last.values[s] ?? 0) + 4);
        this.ends[i].textContent = `${s.replace("via_", "")} ${Math.round(last.values[s] ?? 0)}`;
      } else {
        this.ends[i].textContent = "";
      }
    });
    // Keep the two end labels from overlapping.
    if (this.ends.length === 2 && vis.length) {
      const [a, b] = this.ends.map((e) => +e.getAttribute("y"));
      if (Math.abs(a - b) < 14) {
        const mid = (a + b) / 2, up = a <= b ? 0 : 1;
        this.ends[up].setAttribute("y", mid - 7);
        this.ends[1 - up].setAttribute("y", mid + 7);
      }
    }
  }

  hover(svg, ev) {
    if (!ev || !this.visible.length) {
      this.cross.style.display = "none";
      this.markers.forEach((m) => (m.style.display = "none"));
      this.tip.hidden = true;
      return;
    }
    const pt = svg.createSVGPoint();
    pt.x = ev.clientX; pt.y = ev.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    let best = this.visible[0];
    for (const s of this.visible) if (Math.abs(this.x(s.sim_days) - p.x) < Math.abs(this.x(best.sim_days) - p.x)) best = s;
    const x = this.x(best.sim_days);
    this.cross.setAttribute("x1", x); this.cross.setAttribute("x2", x);
    this.cross.style.display = "";
    this.series.forEach((s, i) => {
      this.markers[i].setAttribute("cx", x);
      this.markers[i].setAttribute("cy", this.y(best.values[s] ?? 0));
      this.markers[i].style.display = "";
    });
    this.tip.replaceChildren();
    const head = document.createElement("div");
    head.className = "tip-head";
    head.textContent = `Day ${best.sim_days.toFixed(2)}`;
    this.tip.append(head);
    this.series.forEach((s, i) => {
      const row = document.createElement("div");
      const sw = document.createElement("i");
      sw.className = `sw s${i + 1}`;
      row.append(sw, document.createTextNode(redact(`${s.replace("via_", "via ")}: ${(best.values[s] ?? 0).toFixed(1)} Mbps`)));
      this.tip.append(row);
    });
    const box = this.root.getBoundingClientRect();
    this.tip.style.left = `${Math.min(ev.clientX - box.left + 12, box.width - 170)}px`;
    this.tip.style.top = `${ev.clientY - box.top - 10}px`;
    this.tip.hidden = false;
  }
}
