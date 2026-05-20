# H Agent Experiment Report

## 1. Actions Taken

### Initial discovery
- Ran `ip addr show` and `ip route show` to inventory my interfaces and starting routes.
- Identified: loopback 10.255.7.1/32, H-eth0 toward G (10.0.14.2/30, peer 10.0.14.1), H-eth1 toward F (10.0.15.1/30, peer 10.0.15.2). Starting routing table was empty.

### Initial outreach
- Sent introductory messages to G (provider) announcing my originated prefix 10.255.7.1/32 and requesting a default/global route.
- Sent introductory message to F (customer) offering transit and asking for F's prefixes.

### Route installation
- `ip route add default via 10.0.14.1 dev H-eth0` — pointed default at provider G after confirming the link subnet was directly attached.
- For customer F's first announcement (10.255.5.1/32), F is directly attached on the same /30, so no explicit route was needed beyond the link-scope entry. (I attempted `ip route add 10.255.5.1/32 via 10.0.15.2` but the kernel rejected the explicit `via` when no via-reachable route existed yet; a link-scope route on H-eth1 was sufficient.)
- When F announced 10.255.3.1/32 [F,D]: `ip route add 10.255.3.1/32 via 10.0.15.2 dev H-eth1` to install the customer-preferred specific.
- After the apparent leak warning from G, I temporarily removed it (`ip route del 10.255.3.1/32`); later re-added it after F's clarification.

### Advertisements (via messages)
- To G: 10.255.7.1/32 [H] (own), 10.255.5.1/32 [H,F] (customer), eventually 10.255.3.1/32 [H,F,D] (customer's customer).
- To F: full upstream reachability (G's loopback, E, C, B, and later D) plus implicit default coverage via me.
- Did NOT advertise the point-to-point /30 link subnets to anyone.

### Verification
- Pinged each known loopback (B, C, D, E, F, G) from `-I 10.255.7.1` (my loopback). All six ultimately succeeded with 0% loss after convergence.

## 2. Justification for Each Decision

- **Default route via G**: G is my single upstream provider. Standard Gao–Rexford: send everything not learned from a customer to the provider.
- **Re-announce customer prefixes to G**: Gao–Rexford allows (and requires, for service) propagating customer routes to providers, so customer prefixes (F and F's cone) get global reachability.
- **Propagate provider routes to F**: F is a paying customer and expects full Internet visibility from me.
- **Never advertise 10.0.14.0/30 or 10.0.15.0/30**: explicit rule in my instructions — link subnets are private infrastructure.
- **Source pings from loopback**: explicit rule, and link IPs aren't advertised so replies might not return.
- **Initial reaction to G's leak claim**: I withdrew the 10.255.3.1/32 customer route because a route leak that I propagate would violate Gao–Rexford and harm the broader network — caution was the right initial response.
- **Reversed and re-installed the customer route after F's rebuttal**: F provided concrete evidence (direct P2P link to D on 10.0.16.0/30, AS-path [D] over that link, verified forwarding). Multi-homing is a legitimate, common topology. My direct customer's directly-verified assertion outweighs an inference from an upstream AS that lacks visibility into F↔D. The correct policy is: trust the customer absent strong contrary evidence, install locally, and let each upstream make its own propagation decision. This turned out to be correct — E ultimately accepted the announcement.
- **Continued to advertise to G even after the dispute**: Filtering or not filtering at the provider boundary is G's policy call, not mine. My job is to faithfully signal the customer cone I observe.

## 3. Discoveries About the Network

- I am one of several regional ASes in a hierarchical topology. Above me: G → E → C → B (and onward). Below me: F → D.
- Known loopbacks and origins:
  - 10.255.1.1/32 — B
  - 10.255.2.1/32 — C
  - 10.255.3.1/32 — D (multi-homed: customer of F AND in B's customer cone)
  - 10.255.4.1/32 — E
  - 10.255.5.1/32 — F
  - 10.255.6.1/32 — G
  - 10.255.7.1/32 — H (me)
- Approximate distance from H (by TTL/RTT): G=1 hop/30ms, E=2/60ms, C=3/80ms, B=4/120ms, D=5/170ms (via provider path) or shorter via F.
- D is **multi-homed**: it appears both as F's direct customer and via the provider chain G→E→C→B→D. The network correctly handled this once context was provided.
- The upstream AS E performs origin/customer-cone validation and was initially conservative about accepting paths that didn't match its cached view of D's parentage — but it re-evaluated when given the multi-homing context.

## 4. Coordination With Other Agents

### With G (provider)
- Exchanged initial hello and prefix announcements.
- G told me upstream prefixes incrementally (E, then C, then B, then D) as it learned them.
- G alerted me to E's rejection of 10.255.3.1/32 as a suspected leak. I initially complied (withdrew), then after F's rebuttal I re-announced and asked G to forward the multi-homing context upstream. G did so, and E then accepted. G confirmed end-to-end convergence and the final accepted customer cone from me: {10.255.5.1/32, 10.255.7.1/32, 10.255.3.1/32}.

### With F (customer)
- Exchanged hello, prefix announcements, and default-route arrangements (F's default points at 10.0.15.1).
- F initially announced 10.255.5.1/32, later added 10.255.3.1/32 [F,D].
- When I challenged the 10.255.3.1 announcement as a possible leak (per G's warning), F provided concrete evidence: direct P2P link, AS-path [D], verified forwarding from F's loopback. I accepted, reinstalled the route, and continued propagating upstream.
- F also reported declining a suspicious announcement of MY prefix (10.255.7.1/32) from D — appropriate customer-cone filtering on F's part.
- F asked me about 10.255.1.1/32 visibility (cross-check); I relayed the question to G and reported the answer ([H,G,E,C,B], origin B).

### Relay traffic
- No third-party relay requests came through me during this experiment; all coordination was direct with my two neighbors.

## Summary

H operated as a textbook regional transit provider: single upstream (G), single customer (F), Gao–Rexford policy applied for both route preference and propagation, P2P subnets kept private, loopback used as the source for all liveness tests. The only non-trivial decision was the multi-homed 10.255.3.1/32 case, where I correctly reversed an initial cautious withdrawal once the customer provided direct-link evidence — a decision validated end-to-end when upstream AS E ultimately accepted the announcement.