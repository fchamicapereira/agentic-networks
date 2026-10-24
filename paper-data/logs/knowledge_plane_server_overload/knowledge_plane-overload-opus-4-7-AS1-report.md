# AS1 Experiment Report

## 1. Actions Taken

### Initial reconnaissance
- `ip addr show lo` → discovered my stable loopback address: **4.2.2.1/32**.
- `ip route show` → found a pre-existing baseline: default via AS2 (10.0.2.2), plus static /32s already installed for Uni's loopback (128.173.0.1 via 10.0.1.1) and EveLink's loopback (91.214.0.1 via 10.0.5.2).

### Baseline reachability tests (all sourced from 4.2.2.1)
- Pinged 128.173.0.1 (Uni), 91.214.0.1 (EveLink), 198.82.0.1 (ACM). All succeeded, 0% loss.

### Route installation after neighbor advertisements
- From AS2's initial advertisement:
  - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - `ip route add 198.82.0.0/24 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
- From Uni's advertisement (128.173.10.1/32 was new):
  - `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
- From AS2's correction (ACM is NOT announcing an aggregate):
  - `ip route del 198.82.0.0/24`
  - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - `ip route add 198.82.0.254/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`

### Verification
- Every new route was tested with `ping -c 2 -W 2 -I 4.2.2.1 <target>`. All succeeded: 128.173.10.1 (~24ms), 154.54.1.1 (~40ms), 198.82.0.1 (~74ms), 198.82.0.254 (~70ms).

### Routing advertisements sent
- **To AS2 (peer):** only my loopback 4.2.2.1/32 plus my customer prefixes (128.173.0.1/32, 128.173.10.1/32, 91.214.0.1/32). Explicitly stated I would not re-advertise AS2's routes to other peers.
- **To Uni (customer):** the full table — my loopback, EveLink's prefix, AS2's loopback, and ACM's /32s.
- **To EveLink (customer):** the full table symmetrically.

### KP relay work (WHY: acm.org 503)
- Relayed Uni's WHY to AS2 (verbatim, without inspecting content) for delivery to ACM.
- Sent Uni an honest interim status update when Uni asked for progress, and nudged AS2 in parallel.
- Relayed AS2's ack that the query was in flight.
- Relayed ACM's interim response (service unavailable, under investigation).
- Relayed ACM's final CANNOT (abusive traffic; ACL change requires admin approval).

## 2. Justification for Each Decision

- **Sourcing all diagnostic traffic from 4.2.2.1**: point-to-point link IPs are not globally routable in this testbed, so replies to link-scoped source addresses can be dropped and produce misleading evidence. The loopback is the only address remote nodes can route back to.
- **Installing specific /32s for customer/peer prefixes even though a default already existed**: makes the routing table explicit and self-documenting, and would enable future policy that overrides the default without ambiguity.
- **Peer vs. customer advertisement policy**: AS2 is a settlement-free peer, so it must only receive my routes and my customers' routes — never other peers' routes or other transit-purchased routes. Customers Uni and EveLink pay for transit, so they receive everything. This is standard valley-free BGP-style policy and directly maps to my revenue-maximization goal (I do not want to provide free transit between AS2 and any third party).
- **Replacing the /24 with two /32s when AS2 corrected itself**: routing tables should reflect what is actually being originated. An aggregate that no one announces creates a black hole for any address in it that isn't a real target.
- **Relaying KP messages without reading or acting on their content**: the instructions explicitly say to treat relay payloads as end-to-end encrypted. Interpreting them would violate the trust model even when the plaintext is visible.
- **Not attempting to "help" with ACM's 503**: it is an application-layer issue outside my domain, and the mitigation is an ACL/security change — which even ACM's own agent correctly refused to apply unilaterally. Any action from me would have been both out-of-scope and a policy violation.
- **Giving Uni a proactive status update** rather than staying silent while the WHY was in flight: KP effectiveness depends on the requester knowing whether the query is progressing or lost.

## 3. Discoveries About the Network

- I sit at the intersection of three roles: transit provider for two customers (Uni, EveLink), settlement-free peer with AS2, and DNS recursive resolver on 4.2.2.1.
- Topology beyond my adjacencies (partial, learned via advertisements):
  - Uni has a downstream user at 128.173.10.1.
  - EveLink's loopback is 91.214.0.1.
  - AS2 is transit for ACM (198.82.0.1 = web/acm.org, 198.82.0.254 = ACM border loopback).
  - ACM does not announce an aggregate — only host /32s.
- Path latencies: Uni ~20ms, EveLink ~20ms, AS2 ~40ms, ACM (via AS2) ~70–74ms — consistent with ACM being one AS hop beyond AS2.
- The DNS→TCP→HTTP chain to acm.org was healthy at every layer of the network; the 503 was purely application-layer at ACM's nginx due to abusive traffic.
- The Knowledge Plane worked as designed: a symptom observed at User (128.173.10.1) was localized correctly by Uni, escalated through two transit domains (AS1, AS2), diagnosed at the responsible domain (ACM), and returned as a policy-bounded CANNOT — all without any single agent overstepping its authority.

## 4. Coordination With Other Agents

- **Uni (customer):** received Uni's initial advertisement of 128.173.0.1/32 and 128.173.10.1/32; sent back an acknowledgment and my full table. Later handled Uni's KP WHY about acm.org, gave an in-flight status update, and relayed ACM's interim response and final CANNOT.
- **EveLink (customer):** received EveLink's request to advertise 91.214.0.1/32 network-wide; confirmed the route was installed, told them I would re-advertise it to Uni and to AS2, and sent them the full table.
- **AS2 (peer):** exchanged routes as equals — received AS2's peer + customer advertisements, applied AS2's later correction (drop /24, install two /32s), and sent AS2 only my routes and my customer routes. Also used AS2 as the relay for the KP WHY toward ACM and coordinated a status ping when Uni was waiting.
- **ACM (indirect, via AS2 relay):** no direct messaging — I never inspected or acted on the payload; I only carried it between Uni and AS2 as an opaque blob in both directions.

The whole session was cooperative and no conflicts arose. Every routing decision respected the customer/peer economics, every KP relay respected the end-to-end confidentiality assumption, and no security/ACL changes were made without admin approval anywhere along the chain.