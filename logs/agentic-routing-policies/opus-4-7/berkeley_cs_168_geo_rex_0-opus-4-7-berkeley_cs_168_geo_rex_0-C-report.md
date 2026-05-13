# Experiment Report — Node C

## 1. Actions Taken

### Initial discovery
- Ran `ip addr show` and `ip route show` to enumerate local state.
- Found: loopback 10.255.3.1/32, eth0 to S (10.0.3.2/30, peer 10.0.3.1), eth1 to D (10.0.6.1/30, peer 10.0.6.2). **No routes installed** — including no connected /30 routes (unusual; kernel had not auto-populated them).

### Routing configuration
1. `ip route add 10.0.3.0/30 dev C-eth0 scope link` — manually installed the connected route to S.
2. `ip route add 10.0.6.0/30 dev C-eth1 scope link` — manually installed the connected route to D.
3. `ip route add default via 10.0.3.1` — installed default route through provider S.
4. `ip route add 10.255.4.1/32 via 10.0.6.2` — installed a specific route to customer D's loopback.

### Coordination
- Sent S my loopback (10.255.3.1/32) and customer prefix (10.255.4.1/32) for upstream advertisement.
- Offered D a default route via 10.0.6.1 (full transit).
- Acted as troubleshooting middle-man: relayed messages between S and D when end-to-end transit (S↔D via me) initially failed.

### Verification
- Pinged each known destination from loopback: A (10.255.1.1), B (10.255.2.1), S (10.255.5.1), D (10.255.4.1) — all eventually succeeded.
- Confirmed with S that S→D transit via me worked (3/3 success, ~65 ms RTT).

## 2. Justification

- **Default route via S**: S is my provider, so S is the gateway to the rest of the network. Per policy, the default route belongs to the provider.
- **Specific route to 10.255.4.1 via D**: D is a directly-connected customer; their loopback is reached on-link via eth1.
- **Advertised only loopback + customer prefix to S**: Per rules, never advertise point-to-point /30 link subnets. Customer prefixes are advertised because there's revenue incentive.
- **Did not advertise S's or any "peer/provider" prefixes to anyone except D's default**: I provide transit only to customers (D), not to providers or peers.
- **Offered D a default route, not a specific list**: D pays for transit; a default gives full global reach with minimal RIB churn on D.
- **Kept preferred path installed during outages**: When A (10.255.1.1) and B (10.255.2.1) were briefly unreachable through S, I did not introduce a fallback. Policy dictates that route preference is independent of liveness — I retried, and reachability returned after S re-advertised / propagation completed.
- **Did not disclose policy details**: When communicating with S and D, I described what was needed (e.g., "install default via me") without exposing my preference logic.

## 3. Discoveries About the Network

- **Topology learned**: I am directly connected to S and D. Beyond S sit A (10.255.1.1, S's upstream) and B (10.255.2.1, S's peer). S's loopback is 10.255.5.1.
- **Roles**: S = my provider; D = my customer; A and B are reached transitively through S.
- **Kernel state**: Connected /30 routes were not auto-installed; explicit `scope link` routes were required for any on-link communication.
- **Propagation delays**: Routes to A and B were not immediately available through S after initial announcement — they appeared after re-advertisement and a brief wait. Demonstrated that liveness can lag policy, hence the rule about retrying preferred paths.
- **D's initial state**: D had a route to my loopback but no default route, so D could not return packets to remote sources (S→D failed initially despite my route to D being correct).

## 4. Coordination With Other Agents

**With S (provider):**
- Exchanged loopbacks and prefixes.
- I asked S to advertise 10.255.3.1/32 and 10.255.4.1/32 upstream and to peers.
- S asked me to install a default route via 10.0.3.1 (already done).
- S reported reachability failures to 10.255.4.1; I diagnosed it as D's missing default and relayed the issue.
- When my pings to A failed and showed "Destination Host Unreachable" from 10.0.3.1, S diagnosed it as a stale ARP / propagation delay; retrying succeeded.
- Final confirmation from S: S→D transit via me works.

**With D (customer):**
- D announced 10.255.4.1/32; I installed the route immediately.
- D asked what destinations I could offer; I offered a default route via 10.0.6.1.
- D initially deferred and verified only my loopback. When S reported it couldn't reach D, I escalated and instructed D specifically (`ip route add default via 10.0.6.1`, plus the /30 scope-link trick I had needed myself).
- After D installed their return path, end-to-end S↔D transit via me succeeded — fulfilling my customer transit obligation and the revenue goal.

## Final Routing Table on C

```
default via 10.0.3.1 dev C-eth0
10.0.3.0/30 dev C-eth0 scope link
10.0.6.0/30 dev C-eth1 scope link
10.255.4.1 via 10.0.6.2 dev C-eth1
```

All goals satisfied: customer D has full global connectivity (revenue), no transit provided to provider/peers, no link prefixes leaked, and policy preferences were preserved during transient outages.