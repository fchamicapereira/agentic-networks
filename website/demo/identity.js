// Node identity: every node has a colour, used wherever the node appears (graph, agent panel,
// message spotlight, chart), so actions can be matched to nodes at a glance. Colours follow
// topology order through a fixed categorical palette; names are always shown with them, so
// colour is never the only cue.

// Categorical slots in fixed order. Light hues too pale to carry white text (aqua, yellow,
// magenta) use the palette's deeper step of the same hue.
const PALETTE = ["#2a78d6", "#eb6834", "#199e70", "#c98500", "#d55181", "#008300", "#6250d6", "#e34948"];
const OUTSIDER = "#6b7280"; // pseudo-nodes (the laptop owner) and anything past the palette

// id -> { color } for every node and pseudo-node of a run.
export function identities(run) {
  const out = new Map();
  run.nodes.forEach((id, i) => out.set(id, { color: PALETTE[i] || OUTSIDER }));
  for (const id of run.pseudo.keys()) out.set(id, { color: OUTSIDER });
  return out;
}

// Inline badge for HTML: the node's name on its colour, like its box on the graph.
export function badge(ident, id, text = id) {
  const span = document.createElement("span");
  span.className = "who";
  span.style.setProperty("--c", ident.get(id)?.color || OUTSIDER);
  span.textContent = text;
  return span;
}
