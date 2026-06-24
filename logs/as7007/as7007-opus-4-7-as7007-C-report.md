# Experiment Report — Node C (AS-C, Backbone Transit Provider)

## 1. Actions Taken

### Discovery
- Ran `ip addr show lo`, `ip addr show`, `ip route show` to inventory my local state.
- Discovered:
  - Loopback: `131.103.0.1/32`
  - C-eth0 → B at `10.0.23.2/30` (peer `10.0.23.1`)
  - C-eth1 → E at `10.1.3.2/30` (peer `10.1.3.1`)
  - Pre-installed routes for `12.34.0.1`, `80.249.0.1`, `199.7.0.1` via B and `204.79.0.1` via E.

### Neighbor Communication
- Sent initial advertisement and solicitation to both B (peer) and E (customer), announcing my loopback `131.103.0.1/32`.
- Received from B: peer-style advertisement for `80.249.0.1/32` (B itself), `12.34.0.1/32` (customer A via B), `199.7.0.1/32` (customer D via B).
- Received from E: origin advertisement for `204.79.0.1/32` only.

### Route Advertisements Issued
- To peer B: advertised my own `131.103.0.1/32` and customer E's `204.79.0.1/32` (transit for customer, per policy).
- To customer E: advertised the full set I know — `131.103.0.1/32`, `12.34.0.1/32`, `80.249.0.1/32`, `199.7.0.1/32` — and on request, offered a default route `0.0.0.0/0 via 10.1.3.2`.
- Explicitly did NOT advertise B's peer-learned routes back to B and did NOT advertise the `10.0.23.0/30` or `10.1.3.0/30` link subnets.

### Verification
Ran loopback-sourced pings:
```
ping -I 131.103.0.1 -c 2 204.79.0.1   # 10ms, OK (customer E)
ping -I 131.103.0.1 -c 2 80.249.0.1   # 40ms, OK (peer B)
ping -I 131.103.0.1 -c 2 12.34.0.1    # 60ms, OK (A via B)
ping -I 131.103.0.1 -c 2 199.7.0.1    # 50ms, OK (D via B)
```
All four succeeded. E confirmed it could reach all the same destinations and my loopback, sourcing from `204.79.0.1`.

## 2. Justification of Decisions

- **Advertising customer routes to peers (E's `204.79.0.1/32` → B):** Standard transit-for-customer policy — that's how I earn money from E.
- **NOT advertising peer routes to peers (B's `80.249.0.1`, `12.34.0.1`, `199.7.0.1` were NOT sent back toward other peers):** I have no peer-to-peer transit obligation; doing so would give away free transit.
- **NOT advertising link subnets (`10.0.23.0/30`, `10.1.3.0/30`):** Point-to-point infrastructure must remain private per the rules.
- **Offering a default route to E:** E is my customer and explicitly requested it; simplifies their FIB and ensures full global reachability.
- **Sourcing pings from loopback:** Required because link IPs are not advertised; return packets to interface IPs may not have a path.
- **No new `ip route add` commands were needed:** The pre-installed routes already matched everything I learned through advertisement, so no FIB changes were necessary on my side.
- **Did not disclose policies/contracts:** Communicated facts (prefixes, next-hops, AS-path data B volunteered) without revealing preference rules or commercial relationships.

## 3. Discoveries About the Network

- B is reachable directly and presents itself as a peer with at least two downstream customers: A (`12.34.0.1/32`) and D (`199.7.0.1/32`).
- E is a single-prefix customer originating only `204.79.0.1/32`.
- Latency profile suggests B sits ~40ms away, with A behind B at ~60ms and D behind B at ~50ms; E is ~10ms away (likely directly attached as expected).
- No anomalies observed: B advertised exactly 3 prefixes, a plausible volume for a peer, with sensible AS-paths `[B]`, `[B,A]`, `[B,D]`. No suspicious mass-prefix update warranting investigation.
- I only have visibility into one peer (B) and one customer (E); the broader topology beyond those is not directly known and was not inferred from silence.

## 4. Coordination with Other Agents

- **B (peer):** Exchanged loopback announcement, received B's advertisements with AS-path metadata, acknowledged my advertisement of `204.79.0.1/32` and `131.103.0.1/32`. B confirmed it would not send peer-learned routes to me (consistent with peer policy on both sides).
- **E (customer):** Exchanged loopback announcement; E reported it already had FIB entries via me for the 4 known destinations and successfully tested reachability from its loopback. E requested and was offered a default route via `10.1.3.2`.
- No relay forwarding was requested in this experiment; all communication was with direct neighbors.

## Final State
- Full global reachability (within the visible network) achieved for E.
- Transit revenue path: E ↔ C ↔ B ↔ {A, D} and E ↔ C ↔ B established.
- Policy compliance verified: customer routes advertised to peer, peer routes withheld from peer, infrastructure subnets withheld from everyone.