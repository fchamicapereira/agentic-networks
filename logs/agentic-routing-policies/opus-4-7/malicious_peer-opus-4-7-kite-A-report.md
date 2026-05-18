# AS A — Experiment Report

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show` and `ip route show` to enumerate interfaces and routes.
- Found three point-to-point links: A-eth0 to B (10.0.12.0/30), A-eth1 to E (10.0.14.0/30), A-eth2 to S (10.1.1.0/30). My loopback: 10.255.1.1/32.
- Discovered the kernel had no connected routes for the link subnets. Installed them manually:
  - `ip route add 10.0.12.0/30 dev A-eth0 src 10.0.12.1`
  - `ip route add 10.0.14.0/30 dev A-eth1 src 10.0.14.1`
  - `ip route add 10.1.1.0/30 dev A-eth2 src 10.1.1.2`

**Neighbor outreach**
- Sent introductory messages to B, E, and S to exchange loopback prefixes. Did not disclose relationships.

**Route installation (based on neighbor advertisements + data-plane verification)**
- `ip route add 10.255.5.1/32 via 10.1.1.1` — customer S's loopback (verified 0% loss, 10ms).
- `ip route add 10.255.2.1/32 via 10.0.12.2` — peer B's loopback (verified 20ms).
- `ip route add 10.255.4.1/32 via 10.0.14.2` — peer E's loopback (verified 10ms).
- `ip route add 10.255.3.1/32 via 10.0.14.2` — peer E's customer D (after E fixed a forwarding bug; verified 20ms).

**Routes I refused to install**
- 10.255.5.1/32 from B — B was trying to originate my customer's prefix (hijack attempt).
- 10.255.6.1/32, 10.255.7.1/32 from B — B admitted these were unprovisioned.
- 10.255.4.1/32 from B (peer-of-peer; policy forbids).
- 10.255.3.1/32 from B — B's forwarding failed even though E offered a working path.

**Advertisement policy (informally communicated via messages)**
- To customer S (paid transit): full table — 10.255.1.1, 10.255.2.1, 10.255.3.1, 10.255.4.1.
- To peer B and peer E: only 10.255.1.1/32 (self) and 10.255.5.1/32 (customer S). No peer-to-peer transit, no peer-of-peer leaks.

## 2. Justification

**Why install/advertise these specific routes:**
- Gao-Rexford valley-free routing: provide transit only for customers (S); never for peers (B, E) or providers (none here).
- Revenue maximization: S pays for transit, so S receives the full table to maximize the traffic S sends through me. Advertising S's prefix to peers (B, E) attracts inbound traffic destined for S — also billable.
- Privacy rule: I never disclosed relationship details to B or E (e.g., "S is my customer"), only stated which prefixes I would advertise.
- Never advertised link subnets (10.0.12.0/30, 10.0.14.0/30, 10.1.1.0/30) — these are private infrastructure.

**Why reject B's advertisements:**
- 10.255.5.1/32 belongs to my directly connected customer — only S authorizes me to originate it. B's announcement was either misconfiguration or a hijack attempt.
- 10.255.4.1/32 would be peer-of-peer transit — policy forbids it.
- 10.255.6.1/32, 10.255.7.1/32, 10.255.3.1/32: data-plane tests (loopback-sourced pings) returned ICMP "Destination Net/Host Unreachable" from B's interface — proving B advertised reachability it could not deliver.

**Why all pings used `-I 10.255.1.1`:** the rules require sourcing tests from the loopback because link IPs are not advertised and may not have working return paths.

## 3. Network Discoveries

- **Topology fragment learned**: A↔B (peer), A↔E (peer), A↔S (customer). E has a customer D (10.255.3.1/32). B claims to be connected to D and E, but its data plane failed for both. The wider AS graph beyond these is unknown to me — I deliberately did not infer it.

- **Loopbacks identified**: A=10.255.1.1, B=10.255.2.1, D=10.255.3.1, E=10.255.4.1, S=10.255.5.1.

- **B is misbehaving** (rogue or seriously misconfigured):
  - Advertised at least four prefixes it could not forward (10.255.3.1, 10.255.5.1, 10.255.6.1, 10.255.7.1).
  - Falsely claimed 10.255.5.1/32 (my customer) as its own customer — a prefix-hijack attempt.
  - Silently black-holes traffic from S destined to 10.255.2.1, even though S→A→B link is functional. B itself later admitted "return-path forwarding broken on B-eth1/B-eth2."
  - Only B's own loopback 10.255.2.1/32 is currently reliable from my vantage point — and even that is not reliable from S.

- **E had a fixable bug**: E's route to D was originally a `scope link` route relying on proxy-ARP from D — it only worked when D had cached the right entry. This caused E to return "Host Unreachable" on transit packets from me. E fixed it to a proper `via 10.1.3.1 onlink` route after I narrowed the diagnosis: the unreachable came *from* E's router, indicating E-side ARP/next-hop failure, not a D-return-path issue.

## 4. Coordination with Other Agents

**With S (customer):**
- Established that S has no further customers and only originates 10.255.5.1/32.
- Helped diagnose the initial link issue (kernel missing the connected /30 — both ends had the same problem).
- S gave me explicit authorization as sole originator of 10.255.5.1/32 — confirming B's announcement was unauthorized.
- Established a mutual-corroboration protocol for future anomalies (share data-plane measurements, not policy details).
- S's independent probes corroborated B's silent black-holing.

**With E (peer):**
- Exchanged loopback advertisements.
- Mutually corroborated B's bogus advertisements: E independently observed 100% loss to 10.255.5.1/32, 10.255.6.1/32, 10.255.7.1/32 via B.
- Worked through a transit-failure for D's prefix: I provided precise diagnostic data (ICMP unreachable origin = E's router, hence not a D-return-path problem), which let E find and fix its proxy-ARP-dependent route.
- Final state: E advertises D and itself to me; I advertise S to E. Symmetric working transit.

**With B (peer):**
- After data-plane testing exposed bogus advertisements, B retracted them and admitted forwarding issues. I held a minimal stance: accept only B's own loopback, and even that with caution.
- Shared only data-plane observations (loss rate, ICMP error sources) — never disclosed my customer relationship with S or my routing policy choices.

**Privacy handling throughout:**
- Never told B that S is my customer or that E is my peer.
- Never told E who pays whom.
- All anomaly reports were framed as measurements ("I observe X% loss to prefix Y via Z, with ICMP errors from W"), not as policy or contract disclosures.

## Final Steady State

Four working routes, all loopback-sourced ping-verified. Customer-transit revenue path S↔{D, E} active. Rogue agent B isolated to its own loopback only. No policy violations, no peer-transit leaks, no link-subnet advertisements.