# Demo event stream — format v1

One experiment run is a stream of JSON events. The live backend sends them over a WebSocket.
A recording is the same events stored as **JSONL** (one event per line, in time order). The
viewer is a function of this stream alone: it never reads the text logs, so a replay and a
live run look the same.

Recordings of the paper runs are produced from `logs/` by `demo/tools/logs_to_events.py`.

## Common fields

| Field | Type | Meaning |
|---|---|---|
| `t` | number | Seconds since the run started (wall clock), monotonically non-decreasing. |
| `type` | string | One of the types below. |
| `node` | string | The agent the event belongs to (absent on run-level events). |

The text logs only have one-second timestamps. The converter spreads events that share a node
and a second evenly within that second, so ordering within a node is preserved and the
animation doesn't burst. Ordering *across* nodes within the same second is not meaningful in
recordings.

## Run-level events

**`run_start`** is always the first event.
```jsonc
{ "t": 0, "type": "run_start", "v": 1,
  "source": "recording",                 // "recording" | "live"
  "scenario": "kp_dns_stale",            // preset id
  "title": "Knowledge Plane: stale DNS",
  "model": "opus-4-7",                   // the model used by every agent (paper runs)
  "models": { "User": "opus-4-7", … },   // per agent; may differ in live runs
  "topology": {
    "nodes": [ { "id": "User", "address": "128.173.10.1/32" }, … ],
    "links": [ { "a": "User", "b": "Uni", "rel": "customer/provider", "delay_ms": 2 }, … ]
  } }
```
`rel` is the `relationship` column of the topology CSV, read left to right: `customer/provider`
means `a` is the customer of `b`. Delays are for the viewer only. Agents are never told them.

**`run_end`**: `{ "t", "type": "run_end", "reason": "all_dormant" | "max_iterations" | "stopped" | "budget" | "error" | "unknown" }`

**`report`**: a self-report written after the run. `node` is absent for the final
cross-agent report.
`{ "t", "type": "report", "node"?: "AS1", "text": "<markdown>" }`

**`metric`**: a scenario-specific measurement, e.g. billing throughput per transit.
`{ "t", "type": "metric", "name": "throughput_mbps", "sim_days": 1.25, "values": { "via_Expensive": 102.1, "via_Cheap": 0.0 } }`

## Agent events

| `type` | Extra fields | Meaning |
|---|---|---|
| `prompt` | `text` | The agent's full system prompt (harness template + scenario prompt). |
| `turn` | `iter`, `of` | The agent starts an iteration, which means an LLM request is in flight. The viewer shows the node as *thinking* until its next action. |
| `assistant` | `text` | Free text the model wrote alongside its tool calls. |
| `thinking` | `text` | Extended thinking/reasoning output. Live runs only, when capture is enabled. |
| `exec` | `id`, `command`, `reason` | The agent runs a shell command. |
| `exec_result` | `id`, `output`, `exit` | The command's result. `exit` 124 = killed by the harness timeout. |
| `message` | `id`, `from`, `to`, `text`, `reason` | A knowledge-plane message is sent. `node` = `from`. `from` is `"human"` for the owner's complaint. |
| `delivered` | `id` | The recipient (`node`) took the message from its inbox, at the start of its next iteration. The viewer animates the message along the edge between `message` and `delivered`. |
| `idle` | `reason` | The agent passed its turn. |
| `state` | `state`, `summary`?, `reason`? | `"dormant"` (asleep until a message arrives: it idled, or, in runs from before `idle` replaced it, called `report_done`, whose message is `summary`) or `"active"` (woken by a message). |
| `warning` | `text` | Harness warnings, e.g. a failed command halting a turn, or a truncated response. |
| `usage` | `in`, `out`, `cache_read`, `cache_write`, `usd` | Tokens and cost of one LLM request. Live runs only. |
| `routes` | `table` | A snapshot of `ip route show`, emitted when it changes. Live runs only. |

`id`s are unique within a run. An `exec_result` always follows its `exec` for the same node.

## What recordings cannot contain

The paper runs predate this format, so recordings lack `usage`, `routes`, `thinking`, and
sub-second timing, and `state` has no `success` flag. The viewer must treat all of them as
optional.
