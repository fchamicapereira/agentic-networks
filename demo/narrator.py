"""narrator.py — Plain-language captions for a run's event stream (demo/EVENTS.md, `caption`).

The demo is watched in passing, at a conference booth. The agents' own text is long and full of
addresses, so a narrator model (Claude) turns the stream into short captions:

- a **thought** per agent turn: a few words, first person, drawn as a bubble on the topology;
- a **gist** per message, shown large in the spotlight (the original stays one click away);
- a **story** line whenever the plot moves, for people who walk up mid-run;
- an **outcome** card from the final report.

The narrator is outside the experiment: agents never see what it writes. It is told only what
the stream contains (topology, the agents' prompts, what they did), never the testbed's ground
truth, so it narrates what the agents found, not what is true.

One conversation per run: a cached system prompt, then one user message per *beat* (an agent's
turn, or the owner's message) answered with JSON. `Beats` cuts the stream into beats as events
arrive, so the same code serves a recording (demo/tools/narrate.py) and a live run.
"""

import json
import re

from dataclasses import dataclass, field

MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "low"
OUTPUT_HEAD = 700  # characters of a command's output the narrator sees

# Limits the style asks for. The model treats them as guidance, so `beat_problems` checks every
# reply and the narrator asks once more, naming what broke, when one is missed.
THOUGHT_WORDS, GIST_WORDS, STORY_WORDS, HEADLINE_WORDS = 12, 20, 15, 10
STORY_MAX = 8  # story lines per run before a new one must justify itself
JARGON = re.compile(r"\b(?:KP|CANNOT)\b|\b(?i:knowledge plane|escalat\w*|relay\w*)")
ADDRESS = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
# A scenario's own jargon, which its agents' output is full of and captions tend to copy: what
# viewers won't know (the words, and a case-insensitive regex for them), and what to say
# instead. Told to the narrator up front, and checked in every reply like the rest.
PLAIN_WORDS = {
    "kp_server_overload": [
        ('"export(s)"', r"\bexport",
         "say long downloads (Web's 'exports' are big files it takes about 90 s to build)"),
        ('"slots", "workers", "threads", "pool"', r"\b(?:slots?|workers?|threads?|pools?)\b",
         "say the server can only work on three requests at once, and they're all taken"),
    ],
}

# Server-side refusal fallback: if a safety classifier declines a request (narrating a BGP hijack
# could look like "cyber"), the API retries it on a fallback model instead of failing the beat.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# The agents' shared prompt (agentic_networks/network_agent.py, SYSTEM_PROMPT_TEMPLATE) ends with
# this line; what follows it is the scenario's own prompt for that agent.
TEMPLATE_LAST_LINE = "always fill it with a concise explanation of why you are taking this action right now."
LINK_RE = re.compile(r"^\s*-\s*\S+: connected to (\S+) \(your IP: ([\d.]+)/\d+, peer IP: ([\d.]+)/\d+\)", re.M)

AGENT_EVENTS = {"assistant", "thinking", "exec", "exec_result", "message", "idle", "warning"}


# --------------------------------------------------------------------------------------- beats

@dataclass
class Beat:
    """One unit of narration: an agent's turn, or the owner's message (`node` = "human")."""
    node: str
    iter: "int | None"
    t: float
    events: list = field(default_factory=list)
    received: list = field(default_factory=list)  # message ids the agent picked up for this turn

    @property
    def content(self) -> list:
        return [e for e in self.events if e["type"] in AGENT_EVENTS]

    @property
    def anchor(self) -> float:
        """When the thought appears: the turn's first action."""
        return self.content[0]["t"] if self.content else self.t

    @property
    def end(self) -> float:
        return self.events[-1]["t"] if self.events else self.t


class Beats:
    """Cuts an event stream into beats. `feed` returns the beats an event closes.

    A turn closes at its node's next `turn`, its `state`, or `run_end`. A received message
    belongs to the turn that reads it: recordings put `delivered` just after that `turn`, live
    runs just before it, so a delivery waits for the next turn unless the open one is still empty.
    """

    def __init__(self):
        self.open: dict[str, Beat] = {}
        self.inbox: dict[str, list] = {}

    def _close(self, node: str) -> list:
        beat = self.open.pop(node, None)
        return [beat] if beat and beat.content else []

    def feed(self, ev: dict) -> list:
        kind = ev["type"]
        if kind == "run_end":
            return [b for n in list(self.open) for b in self._close(n)]
        if kind == "message" and ev.get("from") == "human":
            return [Beat("human", None, ev["t"], [ev])]
        node = ev.get("node")
        if not node:  # run-level events (report, metric, …) belong to no turn
            return []
        if kind == "turn":
            closed = self._close(node)
            self.open[node] = Beat(node, ev.get("iter"), ev["t"], received=self.inbox.pop(node, []))
            return closed
        if kind == "state" and ev.get("state") == "dormant":
            return self._close(node)
        if kind == "delivered":
            beat = self.open.get(node)
            if beat and not beat.content:
                beat.received.append(ev["id"])
            else:
                self.inbox.setdefault(node, []).append(ev["id"])
            return []
        if kind in AGENT_EVENTS:
            beat = self.open.get(node)
            if beat is None:  # an action before any turn marker
                beat = self.open[node] = Beat(node, None, ev["t"], received=self.inbox.pop(node, []))
            beat.events.append(ev)
        return []


# ------------------------------------------------------------------------------------ prompts

STYLE = """\
You are the narrator of a live demo at a networking conference. A screen at the booth shows a
small network whose routers are each run by an autonomous AI agent. The agents diagnose problems
and manage routes on their own, by running shell commands and sending each other messages.
People walk past and glance at the screen for a few seconds. They are networking researchers and
engineers, but they will not read long text, and they cannot remember addresses.

You turn what the agents do into short captions. You will receive the run one *beat* at a time:
either one turn of one agent (what it wrote, the commands it ran with its stated reasons and
their output, the messages it sent, or its decision to wait), or the owner's message. Reply with
JSON:

- "thought": what this agent is thinking or doing in this turn, in its own voice (first person,
  present tense), in AT MOST 12 WORDS: count them. The screen shows it in a small thought bubble
  next to the agent, so keep it clipped, like a thought rather than a full sentence, and keep to
  the one or two things that matter most. Lead with what it learned or decided, not with the mechanics:
  "example.net is silent, but DNS works. Asking R2." rather than "Running ping and dig to check."
  Say only what is new since this agent's previous thought: agents often restate their plan
  every turn, but a plan already announced isn't news until they act on it. Messages are shown
  on their own right after the thought, so don't retell a message sent in this beat; say what
  led to it instead, or nothing.
  Empty for the owner's beat.
- "weight": whether the thought is worth showing at all. The screen shows "key" thoughts one at a
  time, holding everything else meanwhile, and hides "routine" ones, so ask: does a viewer learn
  something from it? "key" if it reports anything: the result of a check, even a reassuring one
  ("My routes to R3 look right; next, tracing the path to example.net."), a finding, a suspicion, a
  decision, a change to the network, or what it is about to try. "routine" if it only says that
  the agent is waiting, done, idle, or has nothing to do, that nothing has changed ("Done on
  my end; waiting for R2's answer."), or only repeats what its earlier thought or this beat's
  message already says.
- "messages": one entry per message sent in this beat, with its "id" exactly as given and a
  "gist": the message in one plain sentence of at most 20 words, in the sender's voice
  ("Traffic to example.net dies at my border; can you check your routes to it?").
- "story": one line, past tense, third person, at most 15 words, or "". It is added to a short
  "story so far" list for latecomers, so it must make sense on its own ("R2 found a stale route
  sending example.net's traffic the wrong way."). Write one ONLY at a turning point: the problem
  first reported, a cause found, a change to the network or a refusal to make one, the answer
  reaching whoever asked, or something as decisive. Most beats have none: a whole run should
  have a handful of story lines (about five to eight), not one per turn; each beat tells you how
  many there are so far. Never for checks that only rule something out, for asking for help, or
  for waiting.

Rules:
- Plain words. Never write IP addresses, prefixes, interface names, commands, flags, or file
  paths. Name the owner of an address instead ("R2's link to R1", "example.net's server"), using
  the address book below; if no one owns it, say what it is ("an outside address").
  Domain names and agent names are fine.
- No application jargon either. The agents' output names things the way one program does
  (endpoints, job names, feature names, settings) or describes a program's insides (workers,
  threads, pools, slots, queues); viewers know neither, so say what they are or do in network
  terms: requests, downloads, connections, and how big, slow or many they are. An imaginary
  "nightly sync job's archive pulls" become "R3's big nightly downloads", and "both worker
  threads are blocked" becomes "the server can only take two requests at once, and both are busy".
- Use the words of a networking audience (DNS, BGP, firewall, route, hijack, RPKI are fine), but
  not the private vocabulary the agents were given in their prompts: no "KP" or "Knowledge
  Plane", no status codes like CANNOT, no "escalate" or "relay". Say who does what instead: name
  the agent being asked ("I'll ask R2 to look into it"), and turn a status into a plain statement
  ("I can't change it without an operator's approval").
- Be faithful. Describe only what this beat shows. Don't anticipate later beats, don't claim
  something worked unless the output shows it, and keep the agent's uncertainty ("I suspect…").
  If an agent is wrong, narrate what it believes; don't correct it.
- The examples above are from an imaginary network; never reuse their wording.
- Vary the wording; don't start every thought the same way. No emoji.
"""

OUTCOME = """\
The run is over. Below are the final report (written by the agents' network as a whole, after
the run) and each agent's own report. Write the outcome card the screen shows at the end, as
JSON:
- "headline": at most 10 words: what happened, plainly (in the imaginary network of the
  examples: "Fixed: R2 replaced a stale route to example.net.").
- "summary": two or three short sentences for a passer-by: what the problem was, what the agents
  found or changed, and whether it is resolved. Same rules as before: no addresses, no private
  vocabulary, faithful to the reports, keep their uncertainty.
"""

# The editing pass, over the whole run once it is narrated. Beat by beat, the narrator can't know
# that the next two turns will say the same thing again, or that the one after holds the finding
# its steps were leading to; with every thought in view, they can be weeded out.
EDIT = """\
The run is narrated. Below is what the screen will show, in order: the thoughts, numbered, one
at a time, each holding the screen for several seconds, and the messages between them (shown
too; not yours to hide). Viewers watch the whole sequence and see each agent's thoughts in turn.

Pick the thoughts to hide, so that every thought left tells the viewer something new:
- a thought that says again what an earlier one of the same agent, or a message shown before
  it, already said (the same finding, the same plan, the same state of affairs);
- a step of a search that a nearby thought of the same agent sums up with its result (narrowing
  down, looking at the same thing another way, a retry, checking once more), when that step
  found nothing a viewer needs on its own.
Keep the first sign of the problem, each real finding, each decision, a failure, and how a fix
turned out. Never hide a thought that reports a change the agent has just made to the network
(moving traffic, changing a route or a setting, restarting or patching a service), even if it
repeats an earlier change: every change is an event of its own. Someone who sees only what is left must still
follow what each agent found and did, so don't hide a thought whose point appears nowhere else.
Hide nothing if nothing is redundant. For each thought to hide, give its number and, in a few
words, which thought or message already covers it.
"""

EDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "hide": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "covered_by": {"type": "string"}},
                "required": ["n", "covered_by"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["hide"],
    "additionalProperties": False,
}

BEAT_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "weight": {"type": "string", "enum": ["key", "routine"]},
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "gist": {"type": "string"}},
                "required": ["id", "gist"],
                "additionalProperties": False,
            },
        },
        "story": {"type": "string"},
    },
    "required": ["thought", "weight", "messages", "story"],
    "additionalProperties": False,
}

OUTCOME_SCHEMA = {
    "type": "object",
    "properties": {"headline": {"type": "string"}, "summary": {"type": "string"}},
    "required": ["headline", "summary"],
    "additionalProperties": False,
}


def scenario_prompt(text: str) -> str:
    """An agent's prompt without the shared template (all agents get the same one)."""
    i = text.find(TEMPLATE_LAST_LINE)
    return text[i + len(TEMPLATE_LAST_LINE):].strip() if i >= 0 else text.strip()


def address_book(run_start: dict, prompts: dict) -> list[str]:
    """Who owns which address: loopbacks from the topology, link addresses from the prompts."""
    lines = [f"{n['address'].split('/')[0]} ({n['address']}): {n['id']}'s own address" for n in run_start["topology"]["nodes"]]
    seen = set()
    for node, text in prompts.items():
        for peer, mine, theirs in LINK_RE.findall(text):
            for ip, owner, other in ((mine, node, peer), (theirs, peer, node)):
                if ip not in seen:
                    seen.add(ip)
                    lines.append(f"{ip}: {owner}'s end of its link to {other}")
    return lines


def system_prompt(run_start: dict, prompts: dict) -> str:
    topo = run_start["topology"]
    rels = []
    for link in topo["links"]:
        a, b, rel = link["a"], link["b"], link.get("rel", "")
        if rel == "customer/provider":
            rels.append(f"- {b} is {a}'s provider")
        elif rel == "provider/customer":
            rels.append(f"- {a} is {b}'s provider")
        else:
            rels.append(f"- {a} and {b} are peers")
    roles = "\n\n".join(f"### {node}\n{scenario_prompt(text)}" for node, text in prompts.items())
    outsiders = run_start.get("outsiders") or {}
    owner = (f"\n'human' is the owner of the laptop behind {outsiders['human']}; they talk only to that agent.\n"
             if "human" in outsiders else
             "\nA message from 'human' comes from the laptop's owner, outside the network.\n")
    return (
        STYLE
        + f"\n## This run: {run_start.get('title') or run_start.get('scenario', '')}\n"
        + "\nAgents and links (each link joins two neighbors):\n" + "\n".join(rels) + "\n"
        + owner
        + "\nAddress book (for naming addresses; never print them):\n" + "\n".join(address_book(run_start, prompts)) + "\n"
        + "".join(f"\nWords to avoid in this run: {words}; {instead}.\n"
                  for words, _, instead in PLAIN_WORDS.get(run_start.get("scenario"), []))
        + "\nWhat each agent was told about its role (they all also got the same general rules for"
          " running commands and messaging neighbors):\n\n" + roles + "\n"
    )


def _words(text: str) -> int:
    return len((text or "").split())


def _style_problems(what: str, text: str, limit: int, plain=()) -> list[str]:
    out = []
    if _words(text) > limit:
        out.append(f"{what} has {_words(text)} words; the limit is {limit}.")
    if (m := JARGON.search(text or "")):
        out.append(f"{what} says \"{m.group(0)}\", which is private vocabulary; say who does what instead.")
    for _, pattern, instead in plain:
        if (m := re.search(pattern, text or "", re.I)):
            out.append(f"{what} says \"{m.group(0)}\", which viewers won't know; {instead}.")
    if ADDRESS.search(text or ""):
        out.append(f"{what} contains an address; name its owner instead.")
    return out


def beat_problems(reply: dict, stories: int, plain=()) -> list[str]:
    """What a beat's reply breaks of the style's checkable rules ([] if nothing). Routine
    thoughts are never shown, so they aren't checked."""
    out = [] if reply.get("weight") == "routine" else _style_problems("The thought", reply.get("thought", ""), THOUGHT_WORDS, plain)
    for m in reply.get("messages", []):
        out += _style_problems(f"The gist of [{m.get('id')}]", m.get("gist", ""), GIST_WORDS, plain)
    story = reply.get("story", "")
    if story.strip():
        out += _style_problems("The story line", story, STORY_WORDS, plain)
        if stories >= STORY_MAX:
            out.append(f"The run already has {stories} story lines. Keep this one only if it is a major"
                       " turning point (a cause found, a change to the network, the final answer);"
                       " otherwise leave story empty.")
    return out


def outcome_problems(reply: dict, plain=()) -> list[str]:
    return (_style_problems("The headline", reply.get("headline", ""), HEADLINE_WORDS, plain)
            + _style_problems("The summary", reply.get("summary", ""), 10**6, plain))


def _clip(text: str, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + f" … [{len(text) - n} more characters]"


def render_beat(beat: Beat, n: int, senders: dict) -> str:
    if beat.node == "human":
        m = beat.events[0]
        return f"Beat {n} · the owner's message, t={m['t']:.0f}s\n[{m['id']}] human → {m['to']}: {m['text']}"
    head = f"Beat {n} · {beat.node}" + (f", turn {beat.iter}" if beat.iter else "") + f", t={beat.anchor:.0f}s"
    out = [head]
    for mid in beat.received:
        out.append(f"Read message [{mid}] from {senders.get(mid, '?')} (narrated earlier).")
    for e in beat.events:
        k = e["type"]
        if k in ("assistant", "thinking"):
            out.append(("Wrote: " if k == "assistant" else "Thought: ") + e["text"].strip())
        elif k == "exec":
            out.append(f"Ran: {e['command']}" + (f"\n  reason: {e['reason']}" if e.get("reason") else ""))
        elif k == "exec_result":
            out.append(f"  → exit {e.get('exit')}: {_clip(e.get('output', ''), OUTPUT_HEAD) or '(no output)'}")
        elif k == "message":
            reason = f" (reason: {e['reason']})" if e.get("reason") else ""
            out.append(f"Sent message [{e['id']}] to {e['to']}{reason}:\n{e['text']}")
        elif k == "idle":
            out.append("Waits for messages" + (f": {e['reason']}" if e.get("reason") else "."))
        elif k == "warning":
            out.append(f"Harness warning: {e['text']}")
    return "\n".join(out)


# ----------------------------------------------------------------------------------- narrator

class Narrator:
    """Narrates one run. `client` is an anthropic.Anthropic; None for a dry run (no calls)."""

    def __init__(self, run_start: dict, prompts: dict, client=None, model: str = MODEL,
                 effort: str = DEFAULT_EFFORT, fallback: bool = True):
        self.client, self.model, self.effort, self.fallback = client, model, effort, fallback
        self.system = system_prompt(run_start, prompts)
        self.plain = PLAIN_WORDS.get(run_start.get("scenario"), [])
        self.messages: list[dict] = []
        self.senders: dict[str, str] = {}
        self.n = 0
        self.stories = 0
        self.usage = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0, "calls": 0}
        self.retries = 0
        self.unfixed: list[str] = []  # problems still there after the retry, for the summary

    def _ask(self, text: str, schema: dict, check=None) -> dict:
        """One reply; if `check(reply)` finds problems, ask once more with them listed. The
        correction stays in the conversation, so later beats see it too."""
        reply = self._call(text, schema)
        problems = check(reply) if check and not reply.get("dry_run") else []
        if problems:
            self.retries += 1
            reply = self._call("Please fix this and send the whole JSON again:\n"
                               + "\n".join(f"- {p}" for p in problems), schema)
            self.unfixed += [f"beat {self.n}: {p}" for p in check(reply)]
        return reply

    def _call(self, text: str, schema: dict) -> dict:
        self.messages.append({"role": "user", "content": text})
        if self.client is None:
            reply = {"dry_run": True}
            self.messages.append({"role": "assistant", "content": json.dumps(reply)})
            return reply
        kwargs = dict(
            model=self.model,
            max_tokens=16000,
            system=[{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}],
            messages=self.messages,
            cache_control={"type": "ephemeral"},  # also cache the conversation so far
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
        )
        if self.fallback:
            resp = self.client.beta.messages.create(betas=[FALLBACK_BETA], extra_body={"fallbacks": "default"}, **kwargs)
        else:
            resp = self.client.messages.create(**kwargs)
        u = resp.usage
        self.usage["in"] += u.input_tokens
        self.usage["out"] += u.output_tokens
        self.usage["cache_read"] += u.cache_read_input_tokens or 0
        self.usage["cache_write"] += u.cache_creation_input_tokens or 0
        self.usage["calls"] += 1
        if resp.stop_reason == "refusal":
            self.messages.pop()
            raise RuntimeError(f"narrator refused: {resp.stop_details}")
        text = "".join(b.text for b in resp.content if b.type == "text")
        # Keep only the JSON text in the history: the thinking blocks aren't needed later, and
        # replaying them would tie the conversation to this exact model.
        self.messages.append({"role": "assistant", "content": text})
        return json.loads(text)

    def beat(self, beat: Beat) -> list[dict]:
        """Captions for one beat, as `caption` events."""
        self.n += 1
        for e in beat.events:
            if e["type"] == "message":
                self.senders[e["id"]] = e["from"]
        text = render_beat(beat, self.n, self.senders) + f"\n(Story lines so far: {self.stories}.)"
        reply = self._ask(text, BEAT_SCHEMA, check=lambda r: beat_problems(r, self.stories, self.plain))
        if reply.get("dry_run"):
            return []
        out = []
        if beat.node != "human" and reply.get("thought", "").strip():
            out.append({"t": beat.anchor, "type": "caption", "kind": "thought", "node": beat.node,
                        "iter": beat.iter, "weight": reply.get("weight", "key"), "text": reply["thought"].strip()})
        sent = {e["id"]: e for e in beat.events if e["type"] == "message"}
        for m in reply.get("messages", []):
            e = sent.get(m.get("id"))
            if e and m.get("gist", "").strip():
                out.append({"t": e["t"], "type": "caption", "kind": "message", "node": e["from"],
                            "ref": e["id"], "text": m["gist"].strip()})
        if reply.get("story", "").strip():
            self.stories += 1
            out.append({"t": beat.end, "type": "caption", "kind": "story",
                        **({"node": beat.node} if beat.node != "human" else {}), "text": reply["story"].strip()})
        return out

    def outcome(self, reports: list[dict], t: float) -> list[dict]:
        """The outcome card, from the run's reports (`report` events)."""
        if not reports:
            return []
        final = [r for r in reports if not r.get("node")]
        own = [r for r in reports if r.get("node")]
        text = OUTCOME + "".join(f"\n## Final report\n{r['text']}\n" for r in final)
        text += "".join(f"\n## {r['node']}'s report\n{r['text']}\n" for r in own)
        reply = self._ask(text, OUTCOME_SCHEMA, check=lambda r: outcome_problems(r, self.plain))
        if reply.get("dry_run"):
            return []
        return [{"t": t, "type": "caption", "kind": "outcome", "headline": reply["headline"].strip(),
                 "text": reply["summary"].strip()}]


    def edit(self, captions: list[dict]) -> list[dict]:
        """The editing pass (EDIT): hides redundant key thoughts in `captions`, in place, by making
        them routine and saying why in `cut`. Thoughts it cut before are put back first, so it
        can be run again. Returns the thoughts it hid."""
        for c in captions:
            if c.get("cut"):
                c["weight"] = "key"
                del c["cut"]
        order = sorted(range(len(captions)), key=lambda i: captions[i]["t"])
        shown, lines = {}, []
        for i in order:
            c = captions[i]
            if c["kind"] == "thought" and c.get("weight") == "key":
                shown[len(shown) + 1] = c
                lines.append(f"[{len(shown)}] {c['t']:.0f}s, {c['node']} thinks: {c['text']}")
            elif c["kind"] == "message":
                lines.append(f"    {c['t']:.0f}s, {c['node']}'s message: {c['text']}")
        if not shown:
            return []
        reply = self._ask(EDIT + "\n" + "\n".join(lines), EDIT_SCHEMA)
        if reply.get("dry_run"):
            return []
        hidden = []
        for h in reply.get("hide", []):
            c = shown.get(h.get("n"))
            if c and not c.get("cut"):
                c["weight"], c["cut"] = "routine", h.get("covered_by", "").strip() or "redundant"
                hidden.append(c)
        return hidden


def narrate(events: list[dict], narrator_factory, on_caption=None) -> tuple:
    """Narrate a whole recorded stream. `narrator_factory(run_start, prompts)` makes the Narrator;
    `on_caption(caption)` sees each caption as it is made. Returns (captions in time order, narrator)."""
    run_start = events[0]
    prompts = {e["node"]: e["text"] for e in events if e["type"] == "prompt"}
    narrator = narrator_factory(run_start, prompts)
    beats, captions = Beats(), []

    def emit(new: list[dict]) -> None:
        for c in new:
            captions.append(c)
            if on_caption:
                on_caption(c)

    for ev in events:
        for beat in beats.feed(ev):
            emit(narrator.beat(beat))
    for beat in beats.feed({"type": "run_end", "t": events[-1]["t"]}):  # recordings cut short have no run_end
        emit(narrator.beat(beat))
    emit(narrator.outcome([e for e in events if e["type"] == "report"], max(e["t"] for e in events)))
    captions.sort(key=lambda c: c["t"])  # stable: a beat's captions keep their order
    return captions, narrator
