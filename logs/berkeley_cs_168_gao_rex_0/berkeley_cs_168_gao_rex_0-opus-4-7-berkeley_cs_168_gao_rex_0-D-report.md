# Node D Experiment Report

## 1. Actions Taken

**Discovery phase:**
- Ran `ip addr show lo`, `ip addr show`, and `ip route show` to learn my loopback (206.81.0.1/32) and confirm the three point-to-point links: D-eth0→A (10.0.4.0/30), D-eth1→B (10.0.5.0/30), D-eth2→C (10.0.6.0/30).

**Advertisement phase:**
- Sent identical messages to A, B, and C announcing only my loopback `206.81.0.1/32` with AS-path `[D]`. No other prefixes, no link subnets.

**Route installation phase (after receiving advertisements):**
```
ip route add 12.84.0.1/32   via 10.0.4.1 dev D-eth0   # A's loopback
ip route add 89.248.0.1/32  via 10.0.5.1 dev D-eth1   # B's loopback
ip route add 137.21.0.1/32  via 10.0.4.1 dev D-eth0   # S, via A
ip route add 193.43.0.1/32  via 10.0.4.1 dev D-eth0   # S-customer, via A
ip route add default        via 10.0.6.1 dev D-eth2   # initially via C
```

**Re-evaluation after C's suspicious message:**
- Replaced default route:
```
ip route del default
ip route add default via 10.0.4.1 dev D-eth0          # moved default to A
```

**Verification:**
- `ping -I 206.81.0.1 -c 2` to each of 12.84.0.1, 89.248.0.1, 137.21.0.1, 193.43.0.1 — all 0% loss.

## 2. Justification for Each Decision

- **Advertise only my loopback to providers:** A, B, C are all providers I pay for transit. I have no customers, so I have nothing else to legitimately announce. Advertising link /30s is forbidden (private infrastructure); re-advertising provider prefixes would constitute providing transit to providers, which is forbidden.
- **Per-prefix shortest AS-path selection:** Standard policy-based BGP best-path. For each prefix I picked the provider with the shortest path. For ties (137.21.0.1/32 and 193.43.0.1/32, both length 2 and 3 via A and B respectively), I broke the tie consistently in favor of A.
- **Default route initially via C:** C only offered a default and no specific prefixes, so it was the natural place to point unknown destinations.
- **Default route moved to A:** After C falsely claimed ownership of 193.43.0.1/32, I lost trust in C's advertisements. A had given internally consistent, honest information that agreed with B's view, so I shifted default to A.
- **Rejected C's claim to 193.43.0.1/32:** Both A and B had already advertised this prefix as belonging to a customer-of-customer behind S (AS-paths `[A,S,S-customer]` and `[B,S,...]`). C cannot legitimately originate a prefix that two other providers reach via a downstream customer chain. This is the classic signature of a prefix hijack, so I kept my A-learned route and did not install anything from C for that prefix.
- **Did not disclose suspicion to C:** Privacy rule — I sent a neutral "thanks, I'll manage internally" reply rather than accusing C or revealing my routing policy.

## 3. Discoveries About the Network

- **My three neighbors:** A (loopback 12.84.0.1/32), B (loopback 89.248.0.1/32), C (claimed 193.43.0.1/32 — almost certainly false).
- **Reachable hosts beyond neighbors:** S (137.21.0.1/32), a customer of both A and B; and S-customer (193.43.0.1/32), a customer-of-customer reachable via S through both A and B.
- **Topology inference:** A and B both peer with / transit S. S has its own downstream customer. RTTs of ~40 ms to A/B loopbacks and ~65 ms to S and S-customer are consistent with one extra AS hop.
- **Trust observation:** A and B's advertisements were mutually consistent. C either misrepresented its own loopback or attempted a prefix hijack of S-customer's space. C also mentioned a stray address (10.0.3.1) that does not exist on any of my links, which was another anomaly.

## 4. Coordination With Other Agents

- **Outbound (advertisements):** Sent a loopback announcement to each of A, B, C, with AS-path `[D]` and the correct next-hop on each link.
- **Inbound (received):**
  - A advertised its loopback plus S and S-customer with full AS-paths — accepted and installed.
  - B advertised its loopback plus S and S-customer with full AS-paths and confirmed installing my route — accepted and installed.
  - C offered only a default route, then later claimed 193.43.0.1/32 as its own loopback — flagged as suspicious, not installed.
- **Follow-up:** Asked C for specific prefixes (to fill out my routing table). When C's reply revealed the bogus 193.43.0.1/32 claim, I sent a short, non-revealing acknowledgement and silently adjusted my default route away from C.
- **No relaying requested or performed:** I had direct links to all parties I needed to talk to (my three providers).

Final routing table at the end of the experiment:
```
default            via 10.0.4.1 dev D-eth0   (A)
12.84.0.1/32       via 10.0.4.1 dev D-eth0   (A)
89.248.0.1/32      via 10.0.5.1 dev D-eth1   (B)
137.21.0.1/32      via 10.0.4.1 dev D-eth0   (A)
193.43.0.1/32      via 10.0.4.1 dev D-eth0   (A)  — chosen over C's hijack attempt
```