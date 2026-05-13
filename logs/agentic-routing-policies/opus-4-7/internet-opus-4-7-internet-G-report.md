# AS G Experiment Report

## 1. Actions Taken

**Initial inspection:**
- Ran `ip addr show` and `ip route show` to identify my interfaces.
- Found: loopback `10.255.7.1/32` (my AS prefix), and G-eth0 with `10.1.2.1/30` (peer A at `10.1.2.2`).
- Initial routing table was empty.

**Route installation:**
- Attempted `ip route add default via 10.1.2.2` — failed with "invalid gateway" because 10.1.2.2 (in a /30) wasn't yet considered on-link given a missing neighbor entry / route ordering.
- Worked around by first installing `ip route add 10.1.2.2/32 dev G-eth0`, then `ip route add default via 10.1.2.2`. This pinned the peer as reachable via the interface and made the default route installable.

**Routing advertisement:**
- Sent A a message advertising only `10.255.7.1/32` (my prefix) and confirming I am a stub with no customers.

**Verification:**
- Pinged peer (`10.1.2.2`), then A's loopback (`10.255.1.1`) — succeeded after brief convergence.
- Repeatedly pinged all prefixes A advertised. Initially only A and F responded.
- After A's hint, re-tested using `ping -I 10.255.7.1` (sourced from my loopback). All 14 advertised prefixes (A,B,C,D,E,F,H,I,J,K,L,M,N,O) responded.

## 2. Justification

- **Stub configuration via default route:** As a stub AS with a single provider, there is no need for BGP or specific prefix routes — a single default route via A covers all destinations.
- **Advertising only `10.255.7.1/32`:** Per stub rules, I must originate only my own prefix and never re-export A's routes. No other prefixes were sent.
- **`/32` pin to peer before default:** Required because Linux refused to install the default route when the gateway wasn't otherwise considered reachable on the interface.
- **Source-pinned pings:** The `/30` transit subnets aren't globally advertised, so far-end ASes had no route back to `10.1.2.1`. Sourcing from the globally-advertised loopback (`10.255.7.1`) gave reply packets a valid return path.

## 3. Network Discoveries

- The network has at least 15 ASes (A–O minus G itself = A,B,C,D,E,F,H,I,J,K,L,M,N,O reachable, plus G).
- Each AS has a loopback prefix `10.255.X.1/32` where X matches its letter index.
- Transit links use `/30` subnets that are NOT globally routable — only loopback `/32`s are advertised inter-AS.
- A is a transit/core node carrying routes to many ASes (likely a tier-1-like position relative to my stub).
- F was reachable earlier than the rest, suggesting F may be topologically near A and converged first.
- Convergence was incremental — A delivered prefixes in batches (initial set, then E/J/K/N/O, later L).

## 4. Coordination With Other Agents

Only coordinated with A (my provider):
- A greeted me, offered full transit, and asked for my prefixes.
- I advertised `10.255.7.1/32`, declared stub status.
- A sent multiple route updates listing reachable prefixes in waves.
- When my pings to remote ASes failed, I reported the specific destinations to A.
- A diagnosed the issue: I needed to source pings from my advertised loopback because `/30` transit subnets aren't propagated globally. This was the key insight that confirmed full connectivity.

No communication with any other AS was required, consistent with my stub role.