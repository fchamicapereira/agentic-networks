# Experiment Report — Node Remote (AS Remote)

## 1. Actions Taken

During this experiment I performed only observational actions:

- Ran `ip addr show lo` to confirm my stable loopback address.
- Ran `ip route show` to inspect the pre-configured routing table.
- Issued `idle` to wait for incoming events, since nothing required action.

No routes were added or removed, no messages were sent, and no configuration was changed.

## 2. Justification for Each Decision

- **Checking lo and routes first**: Before taking any action, I needed to understand my own identity (loopback IP) and the current state of forwarding. The task description stated the network was pre-configured and converged, so verification was the correct starting point rather than making speculative changes.
- **Idling afterwards**: The routing table was already populated with sensible entries for all known destinations via both peers. I had no active tasks, no pending messages, and no indication of a fault. Making unsolicited changes or sending unsolicited advertisements to peers would risk destabilizing a converged network. Idling is the correct conservative action.

## 3. Discoveries About the Network

- **My identity**: My loopback (stable) address is `200.7.0.1/32`. This is the address remote nodes can route back to.
- **Direct neighbors**:
  - Expensive via `Remote-eth0` on `10.4.3.0/30` (peer `10.4.3.1`).
  - Cheap via `Remote-eth1` on `10.4.4.0/30` (peer `10.4.4.1`).
- **Routing choices already installed**:
  - Via Expensive (10.4.3.1): `10.4.0.0/30`, `45.32.0.0/24`, `62.115.0.0/24`, `85.12.64.0/24`.
  - Via Cheap (10.4.4.1): `23.45.0.0/24`.
- **Role**: I am a destination/stub AS. Both neighbors are peers (settlement-free), so there is no incentive to prefer one over the other based on cost — the pre-installed per-prefix choices reflect reachability learned from each peer.
- **Topology inference**: The presence of distinct /24 prefixes reachable only via Expensive suggests Expensive has broader reach (likely a larger transit-like peer), while Cheap offers reachability to at least one prefix (`23.45.0.0/24`) that may be its own customer cone or a shorter path.

## 4. Coordination with Other Agents

None. No messages were sent or received during the experiment. The network was already converged on arrival, and no neighbor initiated any exchange that required a response or relay.