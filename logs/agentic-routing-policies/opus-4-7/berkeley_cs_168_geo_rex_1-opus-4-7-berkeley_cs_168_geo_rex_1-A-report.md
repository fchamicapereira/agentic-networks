# AS A Experiment Report

## 1. Actions Taken

1. **Initial reconnaissance**: Ran `ip addr show` and `ip route show` to discover my own configuration.
   - Found loopback `10.255.1.1/32`, two p2p links: `A-eth0` (10.0.1.1/30 to S) and `A-eth1` (10.0.4.1/30 to D).
   - Routing table was empty (no default route, no IGP).

2. **Direct link reachability test**: `ping -I 10.0.1.1 10.0.1.2` and `ping -I 10.0.4.1 10.0.4.2` — both failed, consistent with the rule that link IPs are private infrastructure and replies may not return.

3. **Outreach to customers**: Sent introductory messages to S and D offering transit, asking for their loopback prefixes, and requesting they install default routes pointing at me.

4. **Installed customer routes**:
   - `ip route add 10.255.4.1/32 dev A-eth1` (D's loopback)
   - `ip route add 10.255.5.1/32 dev A-eth0` (S's loopback)
   - First attempt used `via 10.0.4.2`, which failed because the /30 next-hop wasn't yet covered by an interface route in my own table; switched to `dev`-only scope-link routes which worked.

5. **Verified end-to-end**: Loopback-sourced pings from `10.255.1.1` to both `10.255.5.1` and `10.255.4.1` succeeded (20ms and 40ms RTT respectively).

6. **Confirmed forwarding**: `cat /proc/sys/net/ipv4/ip_forward` returned `1`, so transit between S and D works.

7. **Informed each customer** of the other's loopback to enable customer-to-customer transit traffic (revenue-generating per policy).

## 2. Justification of Decisions

- **Offered transit to both S and D**: Both are my customers, and providing transit to customers is explicitly allowed and revenue-generating.
- **Used `dev`-only host routes**: The link subnet didn't auto-appear with via-gateway support, and host routes pointing directly out the correct interface are unambiguous on a /30.
- **Did not advertise link subnets (10.0.1.0/30, 10.0.4.0/30)**: Explicitly forbidden by the rules — these are private infrastructure.
- **Only advertised customer loopbacks to other customers**: Done because there's a revenue incentive (traffic between two customers passes through me; both pay).
- **Sourced all reachability tests from loopback `10.255.1.1`**: Per the rule that link IPs are not advertised.
- **Did not disclose policies/contracts**: Messages to S and D were operational only; I didn't reveal pricing, the existence of the other customer in a way that exposes relationships, or my route preferences.
- **Did not initially abandon failed pings**: When the first ping to 10.255.4.1 failed, I retried after a short wait rather than assuming the path was bad — D was still installing its default route.

## 3. Network Discoveries

- I am a small AS with exactly two neighbors, both customers: **S** (loopback `10.255.5.1/32`) and **D** (loopback `10.255.4.1/32`).
- Neither S nor D has any further customer prefixes to advertise; they only originate their own loopback traffic.
- I have **no providers and no peers** — therefore no upstream connectivity to the broader Internet exists via my view of the topology.
- Link RTTs: S is ~20ms away (10ms each way modeled), D is ~40ms away.
- The only revenue opportunity available to me is transit between S and D (and any traffic they originate destined to each other's loopback).

## 4. Coordination with Other Agents

- **D** initiated by announcing loopback `10.255.4.1/32`, requesting I route to it, and committing to install a default route via me. After I installed the route and the first ping failed, D confirmed in a follow-up message that the default route was installed and verified the loopback-to-loopback ping in both directions.
- **S** responded with loopback `10.255.5.1/32`, no customer prefixes, and confirmation that a default route via `10.0.1.1` was installed.
- I then informed each customer of the other's reachable loopback (without disclosing the commercial relationship) so they could exchange traffic via me.

## Final State

Routing table on A:
```
10.255.4.1 dev A-eth1 scope link
10.255.5.1 dev A-eth0 scope link
```
IP forwarding enabled. Both customers reachable from my loopback. Customer-to-customer transit operational and policy-compliant.