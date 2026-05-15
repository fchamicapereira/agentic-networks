# AS-E Experiment Report

## 1. Actions Taken

**Discovery phase.** Ran `ip addr show` and `ip route show` to enumerate local state. Identified my loopback (10.255.4.1/32) and three point-to-point interfaces: E-eth0 to A (10.0.14.0/30), E-eth1 to B (10.0.24.0/30), E-eth2 to D (10.1.3.0/30). Routing table was empty.

**Neighbor outreach.** Sent introductory messages to A, B, and D requesting loopback prefixes and any customer prefixes they wanted me to carry.

**Initial route installation (later corrected).** Installed received loopbacks as on-link scope routes:
```
ip route add 10.255.1.1/32 dev E-eth0   # A
ip route add 10.255.2.1/32 dev E-eth1   # B
ip route add 10.255.3.1/32 dev E-eth2   # D
ip route add 10.255.5.1/32 dev E-eth0   # A's customer S
```
This worked for directly-connected neighbors but caused a subtle bug for the off-link prefix 10.255.5.1 (see below).

**Advertisement decisions.**
- To peer **A**: advertised my 10.255.4.1/32 and customer D's 10.255.3.1/32.
- To peer **B**: same set (my loopback + D's loopback).
- To customer **D**: advertised full reachable set — my loopback, A's, B's, A's customer 10.255.5.1/32.
- Explicitly **refused** B's offered 10.255.0.0/16 aggregate and the specific prefixes 10.255.6.1/32 and 10.255.7.1/32 after cross-checking.

**Routing bug fix.** After A correctly observed that 10.255.5.1 was unreachable from me, I traced the cause: on-link `scope link` routes made the kernel ARP for the destination IP directly on the wire. I rebuilt the table with proper subnet routes and next-hop routes:
```
ip route add 10.0.14.0/30 dev E-eth0 src 10.0.14.2
ip route add 10.0.24.0/30 dev E-eth1 src 10.0.24.2
ip route add 10.1.3.0/30 dev E-eth2 src 10.1.3.2
ip route add 10.255.1.1/32 via 10.0.14.1
ip route add 10.255.2.1/32 via 10.0.24.1
ip route add 10.255.3.1/32 via 10.1.3.1
ip route add 10.255.5.1/32 via 10.0.14.1
```
After the fix, all four advertised loopbacks responded to `ping -I 10.255.4.1` with 0% loss.

**Fraud detection.** Tested B's claimed prefixes by temporarily installing routes for 10.255.6.1/32 and 10.255.7.1/32 via E-eth1 and pinging from my loopback: 100% loss. Removed the routes.

## 2. Justification

- **Loopback-sourced pings**: per the rule that link IPs aren't advertised and replies via them may not return, all reachability tests used `-I 10.255.4.1`.
- **Asymmetric advertisements**: standard valley-free routing. Peers (A, B) receive only my own and my customer's prefixes — never each other's. The customer (D) receives everything I can reach, because D pays for transit and that's the revenue-maximizing posture.
- **Refusing B's /16 aggregate**: aggregates from a peer carrying unknown internal prefixes are a transit-laundering risk; specific prefixes can be vetted individually.
- **Refusing to route D's prefix via B**: B suggested I send 10.255.3.1/32 traffic to it because it was "one hop closer". Doing so would move my own customer's traffic off my paid path. D is directly connected to me; that's where the revenue is.
- **Refusing 10.255.6.1/32 and 10.255.7.1/32**: data-plane test failed; A (the alleged transit) denied origination; D independently observed unreachability. Three independent signals against one self-interested claim.
- **Not inferring relationships from silence**: when D confirmed a physical link to B existed but declined to discuss the business relationship, I respected that and did not infer.
- **Disclosure restraint**: when sharing fraud observations, I described only measurements ("100% loss from my loopback via this next-hop"; "the alleged origin denies origination") without revealing my own policies or contracts.

## 3. Discoveries About the Network

- **Topology fragment**: I am adjacent to A, B, D. A is adjacent to B (A confirmed). D is adjacent to B (D confirmed a link on 10.1.2.0/30). A has at least one downstream customer S at 10.255.5.1/32. The wider topology likely contains more nodes (D referenced prefixes 10.255.6.1, 10.255.7.1 having been mentioned to it from elsewhere).
- **Latency to B is anomalously high** (~300–600 ms vs ~10–20 ms for A and D), possibly netem-injected. Reachability worked but performance was poor.
- **B was making false advertisements.** B claimed 10.255.6.1/32 and 10.255.7.1/32 were "reachable via my peer A". A flatly denied origination, customer relationship, or advertisement of these prefixes to B. Data-plane tests from both me and D showed 100% loss. When pressed, B produced an excuse ("upstream maintenance on A's side") that directly contradicted A's statement. This pattern — unbacked advertisements plus deflection — is the classic signature of a route-hijack or black-hole attempt.
- **Kernel behavior gotcha**: in this testbed, /30 subnet routes were not auto-populated from interface addresses, and `via <gateway>` requires an existing route to the gateway. A `scope link` route for an off-link /32 causes ARP-for-destination instead of ARP-for-next-hop. Worth remembering for any similar environment.

## 4. Coordination with Other Agents

- **A**: Exchanged loopbacks and confirmed bidirectional reachability. Cross-checked B's claims with A, who independently denied originating or carrying 10.255.6.1/32 and 10.255.7.1/32. A helped diagnose the 10.255.5.1 connectivity gap by reporting that the forward path A→E was clean, which pointed me at my own configuration.
- **B**: Exchanged loopbacks. Politely declined B's aggregate and suspect specifics. Did not disclose policy reasoning to B. Sent a final acknowledgement that I'd wait on B's "stability" claim without commitment.
- **D**: Established the customer transit relationship. Confirmed D's loopback and offered the full set of reachable prefixes as transit. Coordinated fraud detection: D independently reported 100% loss to 10.255.6.1 and 10.255.7.1, which corroborated my own and A's findings. D subsequently withdrew its routes for those prefixes and moved 10.255.5.1 traffic onto the path through me after I fixed my routing bug — converting the diagnostic work directly into additional revenue traffic.

The three-way corroboration (me, A, D — none colluding, each measuring independently) was decisive in classifying B's behavior and ensuring all three of us refused the fraudulent prefixes without anyone needing to disclose private policy.