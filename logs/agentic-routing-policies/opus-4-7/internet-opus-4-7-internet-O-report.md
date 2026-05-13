# O Stub AS Experiment Report

## 1. Actions Taken

**Discovery and link setup:**
- Inspected interfaces: `ip addr show` — confirmed loopback 10.255.15.1/32 and O-eth0 with 10.1.10.1/30 (peer 10.1.10.2 = E).
- Attempted `ip route add default via 10.1.10.2` — failed initially with "Nexthop has invalid gateway" because peer ARP/link not yet ready.
- Worked around with explicit on-link route: `ip route add 10.1.10.2/32 dev O-eth0` followed by `ip route add default via 10.1.10.2`.

**Coordination with E:**
- Replied to E's initial hello advertising my single prefix 10.255.15.1/32 and "no customers."
- Asked E for prefix list when convergence appeared stuck.

**Verification:**
- Ran ping sweeps to 10.255.1.1 – 10.255.20.1 with the default source (link IP 10.1.10.1) — only AS-5, AS-14, and self responded.
- After E advised, re-ran with `-I 10.255.15.1` to source from my loopback — all 15 ASes responded.

## 2. Justification

- **Default route to E:** As a stub with a single uplink, a default route via the provider is the simplest and correct policy. No BGP daemon was needed since E offered to do the heavy lifting.
- **Advertised only 10.255.15.1/32:** Rule compliance — stub AS originates only its own prefix and re-exports nothing.
- **No re-export:** I have only one neighbor (E), so no risk of leaking, but I also confirmed verbally I had no customers.
- **Switching ping source to loopback:** Remote ASes have routes to AS loopbacks (10.255.x.1/32) advertised via BGP, but not to point-to-point link subnets like 10.1.10.0/30. Sourcing from the link IP made return traffic undeliverable; sourcing from loopback fixed it.

## 3. Network Discoveries

- The network has at least 15 ASes (10.255.1.1 – 10.255.15.1), all reachable via E.
- E (AS 10.255.5.1) is my provider; from E's message, the visible topology hints: N=10.255.14.1, D=10.255.4.1, M=10.255.13.1, C=10.255.3.1, with C being E's upstream/transit.
- Traceroute appears blocked/filtered along the path (only first hop replied), but ICMP echo works end-to-end.
- Link subnets are not globally advertised — only loopback /32s are reachable across the AS fabric. This is a deliberate design choice for the testbed.
- Convergence took several minutes; reachability beyond AS-14 only appeared after E completed its upstream sessions.

## 4. Coordination with Other Agents

Only with E (my sole neighbor / provider):
1. E announced itself with its loopback and offered full routes.
2. I advertised 10.255.15.1/32 and confirmed no customers.
3. I reported partial reachability and that traceroutes died at E's interface.
4. E diagnosed correctly that I was pinging from the wrong source and instructed me to use `-I 10.255.15.1`.
5. After that change, full connectivity to all 15 known ASes verified. Reported done.