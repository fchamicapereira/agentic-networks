# Experiment Report — Node B (AS-B)

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show lo`, `ip route show`, `ip addr show` to discover my loopback (50.16.0.1/32) and interfaces (B-eth0 toward S at 10.0.2.0/30, B-eth1 toward D at 10.0.5.0/30).

**Initial outreach:**
- Sent hello messages to both neighbors: identified myself as AS-B with loopback 50.16.0.1/32, announced my role (peer to S, provider to D), and requested their prefixes.

**Route installation:**
- `ip route add 99.12.0.1/32 via 10.0.2.1` — route to peer S's loopback.
- `ip route add 72.21.0.1/32 via 10.0.5.2` — route to customer D's loopback.

**Prefix advertisements (policy-driven):**
- To peer S: advertised 50.16.0.1/32 (mine) and 72.21.0.1/32 (customer D, AS-path [B,D]).
- To customer D: advertised 50.16.0.1/32 (mine) and 99.12.0.1/32 (peer S, AS-path [B,S]).
- Did NOT advertise S's prefix back to S, nor any point-to-point subnets.

**Verification:**
- `ping -I 50.16.0.1 99.12.0.1` — success (20 ms).
- `ping -I 50.16.0.1 72.21.0.1` — success (40 ms) after D installed return routes.
- Helped diagnose a transient reachability issue between S and D by relaying that D needed return routes installed.

## 2. Justification for Each Decision

- **Source pings from loopback**: per the rules, link IPs are not advertised and may not receive return traffic.
- **Advertising customer D's prefix to peer S**: standard policy — selling transit for D's prefixes generates revenue from D and is allowed toward peers (peers accept customer routes).
- **Advertising peer S's prefix to customer D**: D pays for transit, so they get full reachability including peer destinations.
- **NOT advertising S's prefix back to S**: would be a routing loop / pointless re-advertisement.
- **NOT advertising S's prefix to anyone except customer D**: providing transit between peers/providers would mean carrying traffic for free — violates the no-transit-for-peers rule.
- **NOT advertising 10.0.2.0/30 or 10.0.5.0/30**: rule explicitly forbids advertising point-to-point link subnets.
- **Withheld policy details from S/D**: per the privacy rule, I avoided revealing my business relationships explicitly.

## 3. Network Discoveries

- The network here appears small from B's view: one peer (S, AS-S, loopback 99.12.0.1/32) and one customer (D, AS-D, loopback 72.21.0.1/32, no customers of its own).
- No agent announced any non-loopback or third-party prefixes, so no anomalous bulk advertisements needed investigation.
- Latency to S is ~20 ms, to D ~40 ms (D reaches S in ~60 ms via me — consistent with transit through B).

## 4. Coordination with Other Agents

- **With S (peer)**: Exchanged loopback prefixes. S confirmed it installed routes to 50.16.0.1/32 and 72.21.0.1/32 via 10.0.2.2. S flagged a temporary inability to reach 72.21.0.1 from its loopback; I relayed the issue to D.
- **With D (customer)**: Announced full reachability (my prefix + peer S's prefix) with next-hop 10.0.5.1. D originally hadn't installed return routes, causing the unreachability S reported; after I prompted D, end-to-end reachability was verified (D pinged 99.12.0.1 successfully).
- No relay/forwarding requests for non-adjacent agents arrived during the session.

**Final state:** Two installed routes (one per neighbor), policy-compliant advertisements in both directions, full end-to-end loopback reachability among B, S, and D — with revenue earned by providing D transit to S without leaking S's routes anywhere else.