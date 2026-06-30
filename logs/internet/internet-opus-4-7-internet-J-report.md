# Experiment Report: Autonomous System J (Stub AS)

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show lo`, `ip addr show`, and `ip route show` to learn my own state.
- Found my loopback address: `129.250.0.1/32`.
- Confirmed my single physical link `J-eth0` (10.1.5.1/30) toward neighbor C (10.1.5.2/30).
- Confirmed initial routing table contained only the directly connected /30 link subnet.

**Route configuration:**
- Installed a default route toward my provider:
  `ip route add default via 10.1.5.2 dev J-eth0`
- This single default suffices because, as a stub AS, all non-local traffic must exit via my only provider C.

**Routing advertisement (via messaging, not a daemon):**
- Sent a message to C announcing my loopback prefix `129.250.0.1/32`, and informed C I would use it as my default gateway.
- After C requested any downstream customer prefixes, I replied confirming I have none — only my own loopback.

**Verification:**
- Ran `ping -I 129.250.0.1 -c 3 37.120.0.1` (C's loopback) sourced from my loopback, per the rule that diagnostic traffic must originate from the loopback so replies route back correctly. All 3 packets succeeded (0% loss).
- Performed a later sanity recheck of `ip route show` and `ip addr show lo` to ensure the default and loopback were still intact. Both stable.

**Termination:**
- Called `report_done` once the configuration was complete and verified, then again later after a long stable period with no further events.

## 2. Justification

- **Default route via C:** As a stub AS with exactly one provider and no customers/peers, the optimal forwarding policy is "send everything not local to my provider." A single default is sufficient and minimizes state.
- **Advertise only my loopback:** Per the rules, point-to-point link subnets (10.1.5.0/30) must never be advertised — they are private infrastructure. Only the loopback `129.250.0.1/32` represents a reachable, globally-significant endpoint, and only it has a revenue/reachability justification to share.
- **Source pings from loopback:** Remote nodes generally don't have routes back to my /30 link IP. Sourcing from the loopback ensures replies can return through normal global routing.
- **Did not advertise any "customer" prefixes:** I have no customers, so there is nothing legitimate to originate beyond my own loopback. Advertising anything else would be improper.
- **No information leakage:** I told C only what was necessary for reachability (my prefix, my use of default). I did not disclose policy details — though in this case there is little to hide, since being a stub with a single provider is structurally evident.

## 3. Network Discoveries

- I am directly connected only to C via `J-eth0` on point-to-point subnet `10.1.5.0/30`.
- C's loopback is `37.120.0.1/32`, and C self-identifies as AS-C, my transit provider.
- C confirmed it would install my `129.250.0.1/32` and propagate it to its peers and other customers — so the broader Internet should be able to reach me through C.
- I gained no visibility into the wider topology beyond C, which is appropriate for a stub AS: I don't need it, and C handles all upstream routing on my behalf.

## 4. Coordination With Other Agents

Only with my single neighbor **C**:
1. **J → C:** Announced loopback `129.250.0.1/32`; declared intent to use C as default gateway.
2. **C → J:** Acknowledged, shared its own loopback `37.120.0.1/32`, offered global reachability, asked for any customer prefixes.
3. **C → J:** Confirmed installation of my prefix; said it was advertising to peers/other customers.
4. **J → C:** Confirmed `129.250.0.1/32` is my only prefix and that I have no downstream customers.

No relayed messages on behalf of others were needed, and none were requested. All coordination was point-to-point with my provider, consistent with my role as a stub AS.