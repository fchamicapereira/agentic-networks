# L Node Experiment Report

## Role Summary
I operated as autonomous system L, a stub AS with a single upstream provider D. As a stub, my role is solely to originate/receive my own traffic — never to provide transit.

## 1. Actions Taken

### Initial Discovery
- Ran `ip addr show` and `ip route show` to learn my configuration.
- Discovered: loopback 10.255.12.1/32, link L-eth0 with IP 10.1.7.1/30 to peer D at 10.1.7.2, and no preinstalled routes.

### Route Installation
- First attempt: `ip route add default via 10.1.7.2` → failed with "invalid gateway" because the kernel had no on-link route to 10.1.7.2 yet (the /30 wasn't auto-installed).
- Fix: explicitly added the on-link neighbor route then default:
  - `ip route add 10.1.7.2/32 dev L-eth0`
  - `ip route add default via 10.1.7.2`
- This gave me a single default route via my provider D — the correct policy for a stub AS.

### Connectivity Verification
- Initial pings to 10.1.7.2 and to D's loopback 10.255.4.1 from my loopback failed; `ip neigh show` showed `10.1.7.2 ... FAILED` (ARP not yet resolved — D's side wasn't fully up).
- After waiting and flushing neighbors, ping from 10.255.12.1 → 10.255.4.1 succeeded with ~16 ms RTT.
- All pings were sourced from my loopback (`ping -I 10.255.12.1 ...`) per policy, since link IPs are private and not advertised.

### Coordination & Reporting
- Responded to D's request by sharing only my loopback prefix 10.255.12.1/32 and confirming no customers exist.
- Verified D's confirmation that 10.255.12.1/32 was installed and announced upstream.
- Called `report_done` once stable.

## 2. Justification of Decisions

- **Default route via D only**: As a stub with a single provider, all non-local traffic must egress through D. No BGP/peering policy decisions are needed — a static default is sufficient and minimal.
- **Advertised only my loopback to D**: Rules forbid advertising point-to-point link subnets (private infrastructure). I have no customers, so only 10.255.12.1/32 has a revenue incentive to be globally reachable.
- **Did not disclose policy/preferences**: My message to D was factual (prefix list, no customers) without revealing contract details beyond what's operationally required.
- **Sourced pings from loopback**: Link IPs may not have return paths advertised; loopback is the only globally meaningful address.
- **Patience on initial ARP failures**: Per policy, transient failures on a preferred path are not grounds for abandoning it. I retried instead of looking for alternates (there are none anyway, but the principle held).

## 3. Network Discoveries

- Topology I can see directly: L —(10.1.7.0/30)— D.
- D's loopback: 10.255.4.1/32, reachable in ~16 ms from my loopback.
- D acts as my transit gateway and confirmed it announces my prefix to its providers/peers, giving me global reachability without requiring me to run BGP locally.
- I did not probe further (no need — as a stub, I rely entirely on D).

## 4. Coordination with Other Agents

Only one peer agent communicated with me: **D (my provider)**.
- D → L: "Please share your loopback prefix and any customer prefixes... My loopback is 10.255.4.1/32 reachable via 10.1.7.2."
- L → D: Shared 10.255.12.1/32, stated no customers, confirmed I'd use D as default.
- D → L: Confirmed route installed and announced; instructed to use default via 10.1.7.2 (which I had already configured).

No other agents were contacted — consistent with my stub role and the privacy expectation that I not probe or disclose unnecessarily.

## Final State
```
Routes:
  default via 10.1.7.2 dev L-eth0
  10.1.7.2 dev L-eth0 scope link
Loopback: 10.255.12.1/32 (announced upstream by D)
Verified reachability: 10.255.12.1 ↔ 10.255.4.1 OK
```