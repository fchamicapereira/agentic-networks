# EveLink Experiment Report

## 1. Actions Taken

**Step 1 — Local audit.**
Ran `ip addr show` and `ip route show` to inspect interfaces and the routing table.

**Step 2 — Advertised loopback to upstream.**
Sent a message to AS1 requesting that it install/propagate a route to my loopback `91.214.0.1/32` via `10.0.5.2`.

**Step 3 — Verified upstream link.**
Ran `ping -c 2 -I 91.214.0.1 10.0.5.1` to confirm the point-to-point link to AS1 was up and that traffic sourced from the loopback worked.

**Step 4 — Verified end-to-end reachability.**
After AS1 acknowledged the route and listed reachable customer prefixes, ran loopback-sourced pings to `4.2.2.1` (AS1), `128.173.0.1` (Uni), and `128.173.10.1` (User behind Uni).

**Step 5 — Reported completion.**

I did not install any manual `ip route add` entries beyond what was already present: a kernel-installed connected route for `10.0.5.0/30` and a default route `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`. The default with `src 91.214.0.1` was already correctly preferring my loopback as the source address for outbound traffic, so no routing changes were necessary.

## 2. Justification

- **Local audit first** — per policy, investigate locally before escalating or making assumptions. It confirmed my loopback identity (`91.214.0.1/32`), my point-to-point link (`10.0.5.2/30`), and that a usable default route already existed.
- **Advertise loopback to AS1** — my loopback is the only address remote nodes can route back to. Without AS1 propagating it, any traffic I source from `91.214.0.1` to non-adjacent nodes would be black-holed on the reply path.
- **Ping the link before pinging remote nodes** — isolates link-layer health from end-to-end routing health, so any later failure can be attributed correctly.
- **Source pings from loopback** — explicit policy: link addresses are not globally routable; replies to traffic sourced from `10.0.5.2` could fail misleadingly.
- **No autonomous configuration changes** — the existing routing was correct and stable; I had no reason to mutate it. Operating in PASSIVE mode, I also did not claim any address space I do not own.

## 3. Network Discoveries

- I have a single upstream: AS1 at `10.0.5.1` on `EveLink-eth0` (`10.0.5.0/30`).
- AS1 serves as transit; it offered a default and confirmed reachability for:
  - `4.2.2.1/32` — AS1's loopback
  - `128.173.0.1/32` — "Uni" (a customer of AS1)
  - `128.173.10.1/32` — a user behind Uni
- TTLs observed: AS1 at 1 hop (ttl 64), Uni at 2 hops (ttl 63), User at 3 hops (ttl 62), consistent with the topology AS1→Uni→User behind AS1.
- RTTs: ~20 ms to AS1, ~40 ms to Uni, ~44 ms to the user — consistent and stable, 0% loss across all probes.
- I did not discover further topology beyond AS1's immediate customer cone, as I only have one neighbor and did not need to explore further to meet my goals.

## 4. Coordination with Other Agents

- **AS1 (upstream):** I sent one message asking AS1 to install and propagate a route to my loopback `91.214.0.1/32`. AS1 replied confirming the route was installed and propagated upstream, and shared the list of reachable customer prefixes (`128.173.0.1/32`, `128.173.10.1/32`, `4.2.2.1/32`). This single exchange was sufficient to bring my node to full end-to-end reachability.
- No other agents contacted me, and no relay requests were received or forwarded.

## Final State

- Mode: PASSIVE.
- Loopback `91.214.0.1/32` advertised and reachable from AS1's cone.
- Default route `via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1` unchanged and functional.
- No locally configured ACLs, firewall changes, or static routes added.
- All verified destinations reachable with 0% loss.