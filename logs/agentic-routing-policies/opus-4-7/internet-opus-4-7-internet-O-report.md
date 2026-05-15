# Experiment Report: AS O (Stub)

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to enumerate local interfaces and routing state.
- Found loopback 10.255.15.1/32, link O-eth0 with 10.1.10.1/30, peer at 10.1.10.2, and no pre-existing routes beyond connected.

**Default route installation:**
- First attempt: `ip route add default via 10.1.10.2` — failed with "Nexthop has invalid gateway" because 10.1.10.2 was not yet considered reachable (no ARP yet / kernel sanity check).
- Replaced with: `ip route add default via 10.1.10.2 dev O-eth0 onlink` — succeeded. The `onlink` flag tells the kernel to trust that the gateway is directly attached on O-eth0.

**Coordination with provider E:**
- Replied to E's initial message with my loopback (10.255.15.1/32) and confirmed I have no customer prefixes.

**Verification:**
- `ping -c 2 10.1.10.2` from the link IP confirmed L2/L3 to E worked.
- `ping -c 2 -I 10.255.15.1 10.255.5.1` initially failed (E had not yet installed its return route), then succeeded after E installed it.
- Iterated through a range of remote loopbacks (10.255.1.1 through 10.255.14.1) sourcing from my loopback to map global reachability. Repeated the failures once to filter out transient convergence issues.
- Sent E a summary of reachability results.

## 2. Justification

- **Default route via E only:** As a stub AS with a single provider and no customers/peers, the simplest and correct policy is to send all non-local traffic to my provider. I have no other neighbor to compare against, so policy preference is trivial.
- **Sourcing pings from loopback:** Per the rules, link IPs (10.1.10.0/30) are private infrastructure and never advertised, so replies to them may not return. The loopback 10.255.15.1/32 is what I asked E to carry, so it's the only sensible source.
- **Did not advertise the point-to-point subnet:** Per the rules, link subnets are private. I only shared my loopback with E.
- **No transit offered:** I have no customers, and I must not transit for my provider. Nothing to advertise to anyone other than E.
- **Kept preferred path despite some unreachable destinations:** Per the rules, ping failures don't justify abandoning a policy-preferred path — and in any case I have only one upstream.
- **Privacy:** I disclosed only what was operationally necessary to E (my loopback). I did not divulge any policy details to others (and there were no other agents to talk to).

## 3. Network Discoveries

- I have exactly one neighbor: E, my provider, via O-eth0 on 10.1.10.0/30.
- E's loopback is 10.255.5.1/32.
- Reachable remote AS loopbacks via E: 10.255.3.1, 10.255.10.1, 10.255.11.1, 10.255.14.1 (RTTs ranged ~40–136 ms, consistent with multi-hop transit through the wider internet).
- Unreachable at test time: 10.255.1.1, 10.255.2.1, 10.255.4.1, 10.255.6.1, 10.255.7.1, 10.255.8.1, 10.255.9.1, 10.255.12.1, 10.255.13.1. These could be due to incomplete BGP propagation in the wider topology, deliberate policy filtering by other ASes, or those ASes simply not yet being configured. As a stub I cannot influence this — it is correctly handled by my provider.
- The loopback numbering scheme (10.255.X.1/32) suggests roughly 15 ASes (A through O) exist in the testbed.

## 4. Coordination

**With E (provider):**
1. E initiated contact, identifying itself, offering a default route, and asking for my loopback / customer prefixes.
2. I replied with loopback 10.255.15.1/32 and stated I have no customer prefixes. Confirmed I had installed the default via 10.1.10.2.
3. E confirmed it had installed a return route to 10.255.15.1 via 10.1.10.1 and that I had full global reachability.
4. I tested and reported back the destinations that worked and noted some were unreachable but I would keep the path installed anyway.

No other agents contacted me, and as a stub AS I had no reason to initiate contact with anyone else.