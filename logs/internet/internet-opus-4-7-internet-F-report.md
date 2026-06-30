# AS F Experiment Report

## Role and Setup
I operated as AS F, a stub AS with a single uplink to provider A on interface F-eth0 (10.1.1.1/30 ↔ 10.1.1.2/30). My loopback address (and only globally-routable prefix) is 77.88.0.1/32.

## 1. Actions Taken

**Discovery**
- `ip addr show lo` → confirmed loopback 77.88.0.1/32.
- `ip route show` → confirmed only the directly-connected link route (10.1.1.0/30) was present.

**Routing configuration**
- `ip route add default via 10.1.1.2 dev F-eth0` — installed a single default route pointing at provider A. No per-prefix routes were ever installed.

**Advertisement to A** (via send_message)
- Advertised only 77.88.0.1/32, origin AS F.
- Explicitly told A I have no customer prefixes.
- Did not advertise the 10.1.1.0/30 point-to-point subnet.

**Connectivity verification** (all sourced from my loopback with `ping -I 77.88.0.1`)
- 12.34.0.1 (A) — OK (~20–60 ms)
- 24.96.0.1 (B) — OK (~100 ms)
- 141.193.0.1 (via C) — OK (~160 ms)
- 193.34.0.1, 202.12.0.1 (later prefixes from A) — OK (~216–224 ms)
- 46.4.0.1 (D) — 100% packet loss

**Notification**
- Reported the D unreachability to A so they could investigate upstream.

## 2. Justification for Each Decision

- **Default route only**: As a stub AS with a single provider that offers full Internet reachability, a default route is sufficient and minimizes state. Installing the per-prefix list A sent would be redundant.
- **Advertising only my loopback**: I have no customers, and link subnets are infrastructure that must not be leaked. The loopback is my only stable, globally-reachable identity.
- **Not advertising 10.1.1.0/30**: Explicit rule — point-to-point link subnets are private and have no revenue incentive to share.
- **Not providing transit**: As a stub with only a provider relationship, accepting/transiting routes for anyone else would violate policy (don't provide transit for providers; I have no customers/peers).
- **Sourcing pings from loopback**: Required because link IPs are not advertised network-wide, so replies to them may not return — using the loopback gives a true end-to-end test.
- **Reporting D unreachability to A rather than acting**: Out of my control as a stub; only A (and its upstreams) can fix routing toward D.

## 3. What I Discovered About the Network

- A is my provider and reaches at least: B (24.96.0.1), C (37.120.0.1), D (46.4.0.1), G (88.150.0.1), and several deeper prefixes via B, C, and D (e.g., 95.211.0.1, 104.28.0.1 via B; 151.101.0.1, 178.62.0.1 via D; 62.210.0.1, 129.250.0.1, 141.193.0.1 via C; and later 193.34.0.1, 202.12.0.1).
- RTTs suggested topology depth: A ~20–60 ms (1 hop), B ~100 ms, via-C ~160 ms, the latest two ~216–224 ms (likely 3+ hops away).
- Reachability to AS D's loopback (46.4.0.1) was broken at the time of testing, even though several "via D" prefixes were not tested; the failure is somewhere upstream of A.
- A advertised prefixes in modest, incremental batches with plausible origins — no anomalous mass-advertisement, so no need to filter.

## 4. Coordination With Other Agents

Only with A (my sole neighbor):
1. Sent an initial advertisement of 77.88.0.1/32 and a statement that I have no customers.
2. Responded to A's request for prefixes by re-confirming the same single prefix.
3. Received A's two prefix-list updates (informational; not installed since default covers them).
4. Notified A of the 46.4.0.1 (D) reachability failure as a courtesy heads-up.

I did not communicate with any non-adjacent agents and did not relay any messages (none were requested).

## Final State
- Routes: `default via 10.1.1.2 dev F-eth0` + kernel-installed `10.1.1.0/30`.
- Advertised prefixes: 77.88.0.1/32 only.
- Transit provided: none (compliant with stub policy).
- Outcome: end-to-end reachability working for all tested destinations except D, which is an upstream issue.