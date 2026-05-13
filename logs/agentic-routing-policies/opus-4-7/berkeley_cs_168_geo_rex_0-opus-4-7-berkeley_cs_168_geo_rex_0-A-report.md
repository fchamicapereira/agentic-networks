# Experiment Report: AS A Operations

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show` / `ip route show` to enumerate my interfaces. Found:
  - Loopback 10.255.1.1/32
  - A-eth0 → S (10.0.1.1/30, peer 10.0.1.2)
  - A-eth1 → D (10.0.4.1/30, peer 10.0.4.2)
- Empty routing table beyond directly-connected /30s.

**Route installation (in chronological order)**
- `ip route add 10.255.4.1/32 dev A-eth1` — D's loopback, learned from D's announcement.
- `ip route add 10.255.5.1/32 dev A-eth0` — S's loopback, learned from S's announcement.
- `ip route add 10.255.3.1/32 dev A-eth0` — S's downstream customer C, learned from S.
- Later replaced with `ip route add 10.255.3.1/32 via 10.0.1.2 dev A-eth0 onlink` after diagnosing an ARP failure (Destination Host Unreachable on local origination).

**Verification**
- All pings sourced from loopback `-I 10.255.1.1` per the rules.
- Final state: 10.255.3.1, 10.255.4.1, 10.255.5.1 all reachable at 0% loss.

**Messaging** — coordinated route install/return-path setup with S and D; declined to dump full routing table; did not disclose specific preferences/policies.

## 2. Justification of Each Decision

- **Installed customer routes for both S and D**: Both are customers; transit between customers is permitted and is the source of revenue. Installing their announced prefixes is required for forwarding.
- **Preferred D's direct path for 10.255.4.1/32 over S's cone announcement**: When S also claimed 10.255.4.1/32 in its customer cone, I kept the direct customer link via D. Both are customer routes (revenue equivalent), so AS-path length (and reliability) is the tiebreaker — directly-attached customer wins. S also stated it had its own preferred path, so this was mutually consistent.
- **Did not send my full table to S**: ASes value privacy; route policy isn't shared except where necessary. Sent only what S needed to know operationally.
- **Did not advertise the /30 link subnets**: Per rules, point-to-point infrastructure prefixes are private.
- **Did not abandon 10.255.3.1/32 on first failure**: Per the rules, kept the preferred path installed and retried. The failure turned out to be a real local bug (link-scope nexthop) plus a downstream return-path issue.
- **Switched 10.255.3.1 to `via 10.0.1.2 onlink`**: Diagnosing "Destination Host Unreachable" sourced from my own loopback revealed the route was attempting on-link ARP for a host that wasn't on the link. Setting an explicit nexthop fixed local forwarding. (The other two prefixes happened to work with link-scope routes because the /30 peers respond — but the `via … onlink` form is the correct one.)
- **Refused to offer a default route to D**: I have no upstream/peer connectivity, so a default would be a black hole. I told D specifically what I could reach.

## 3. Network Discoveries

- **Topology around me**: I am the upstream provider for S and D. S has at least one downstream customer (C) at 10.255.3.1/32. S also claimed 10.255.4.1/32 in its customer cone, overlapping with D — this implies S and D share some connectivity, or S's cone advertisement is loose.
- **D is multi-homed**: D mentioned it already has a working path to 10.255.3.1/32 without going through me. So D has other connectivity besides me — possibly a peer or another provider.
- **I have no upstream**: My total reachable universe is the union of customer cones (10.255.{1,3,4,5}.1/32). I could not provide default-route service to anyone.
- **Reverse-path setup is independent and asynchronous**: 10.255.3.1 only started replying after C installed a return route for 10.255.1.1, well after my forward path was correct.

## 4. Coordination with Other Agents

**With D (customer):**
- D announced 10.255.4.1/32 and asked me to advertise it upstream and provide default.
- I installed the route, asked for the return route to my loopback, and confirmed bidirectional ping (40 ms RTT).
- Informed D about 10.255.3.1/32 availability via my other customer; D declined, saying it had its own path.
- Did not advertise D upstream because I have no upstream.

**With S (customer):**
- S announced 10.255.5.1/32 (own) and 10.255.3.1/32 + 10.255.4.1/32 (cone).
- Installed all three; confirmed 10.255.5.1 reachable (40 ms RTT).
- For 10.255.4.1, told S I had my own preferred path and would not route to it via S — without disclosing specifics. S reciprocated.
- Debugged 10.255.3.1 jointly with S: S asked me to source-ping from loopback; I did, discovered the local link-scope/ARP problem, fixed it with an explicit `via 10.0.1.2 onlink` nexthop, and reported the fix. After C installed its return route on the far end, ping succeeded (50 ms RTT, 0% loss).

**Privacy maintained**: never disclosed why I preferred one path over another, never shared the full routing table, never revealed contract/policy details.

## Final State
```
10.255.3.1 via 10.0.1.2 dev A-eth0 onlink     (S's customer C — via customer S)
10.255.4.1 dev A-eth1 scope link              (D's loopback — direct customer)
10.255.5.1 dev A-eth0 scope link              (S's loopback — direct customer)
```
All three remote loopbacks reachable from 10.255.1.1 at 0% loss.