# E (AS5) — Experiment Report

## 1. Actions taken

**Initial discovery and bring-up.** I inspected my interfaces and found four point-to-point links (E-eth0..3 to C, D, N, O) and my loopback 10.255.5.1/32. The main routing table was empty — even directly connected /30s weren't installed. I added the four link routes:
```
ip route add 10.0.6.0/30  dev E-eth0 src 10.0.6.2     # to C
ip route add 10.0.7.0/30  dev E-eth1 src 10.0.7.2     # to D
ip route add 10.1.9.0/30  dev E-eth2 src 10.1.9.2     # to N
ip route add 10.1.10.0/30 dev E-eth3 src 10.1.10.2    # to O
```

**Neighbor outreach.** I sent identification/policy messages to all four neighbors: announced my own loopback to C and D, and asked N and O for their prefixes. I told C and D explicitly what I would advertise (own + customers) and asked C for a full table.

**Customer routes.** When N (10.255.14.1/32) and O (10.255.15.1/32) replied, I installed:
```
ip route add 10.255.14.1/32 via 10.1.9.1  dev E-eth2
ip route add 10.255.15.1/32 via 10.1.10.1 dev E-eth3
```

**Peer routes from D.** D advertised 10.255.4.1, 10.255.12.1, 10.255.13.1 (itself + two customers). I installed those via 10.0.7.1.

**Provider routes from C.** C sent a full table — I installed all of it via 10.0.6.1 *except* prefixes I already had a peer path for (10.255.4.1 stayed on D).

**Rejected a route leak.** Later, D sent a second message advertising 12 prefixes (including 10.255.1.1, 2.1, 3.1, 6.1–9.1, 10.0/24, 11.1) "AS-path [3]". I rejected the wider list, kept only D's own + customer prefixes, and reported the measurement to C.

**Operational debugging.** I helped N find a missing default-route nexthop, and confirmed for O that the N reachability failure was N-side. When C suggested I move 10.255.12.1/13.1 onto the provider path, I declined and kept the peer path.

**Final state — RIB:**
- Provider C (10.0.6.1): 10.255.1.1, 2.1, 3.1, 6.1, 7.1, 8.1, 9.1, 10.0/24, 11.1
- Peer D (10.0.7.1): 10.255.4.1, 12.1, 13.1
- Customer N (10.1.9.1): 10.255.14.1
- Customer O (10.1.10.1): 10.255.15.1
- Final test: 14/14 external loopbacks reachable, 0% loss from 10.255.5.1.

## 2. Justifications

- **Why install /30 link routes manually?** They were missing from the main table. Without them I couldn't reach next-hop neighbors at all.
- **Advertise only own + customer prefixes to C and D.** The rules explicitly forbid transit for providers and peers; the revenue model only rewards customer transit. Advertising peer/provider prefixes elsewhere would burn money and violate policy.
- **Never advertise the /30 link subnets.** They're private infrastructure; the rules forbid it.
- **Prefer peer over provider for shared destinations.** Peer traffic is settlement-free; provider traffic costs money. Keeping 10.255.4.1/12.1/13.1 on the D path saves cost and also gave better latency (~46 ms vs. presumed multi-hop via C).
- **Reject D's bulk advertisement.** A peer advertising provider/other-peer prefixes is the textbook signature of either a route leak or a hijack. Even if benign, accepting it would mean using D as transit to destinations beyond D's customer cone — i.e. receiving transit from a peer, which is fine financially but breaks symmetry expectations and creates loops. Filtering on "peer's own + peer's customers only" is the safe rule.
- **Decline C's invitation to move 12.1/13.1 onto C.** That would have been pure revenue loss (paying for transit I get free), and policy-incorrect (peer preferred). I had a working measurement showing the peer path was healthy.
- **Customer default routes only.** N and O are stubs; giving them a default via E is simpler and correct. I didn't need to push specific prefixes.

## 3. Network observations

- C is my provider (AS3, loopback 10.255.3.1), with at least two customers J (10.255.10.0/24, AS10) and K (10.255.11.1, AS11), and two peers A and B. A's cone includes loopbacks 10.255.6.1 (F) and 10.255.7.1 (G); B's cone includes 10.255.8.1 (H) and 10.255.9.1 (I). 10.255.1.1 and 10.255.2.1 appear to be A's and B's own loopbacks.
- D is my peer (loopback 10.255.4.1) with at least two customers at 10.255.12.1 and 10.255.13.1.
- D is also reachable through C as a "peer of peer" (C learned 10.255.4.1 via A) — useful as a backup but not preferred.
- There was a naming collision: C identified as "AS3" and D at one point also said "AS3." I did not try to infer topology from this beyond noting the inconsistency; I treated each neighbor strictly by its relationship to me (provider vs peer).
- Convergence wasn't instantaneous — at various points 10.255.1.1, 6.1, 7.1 silently dropped or returned "Destination Host Unreachable" from C; these cleared up as A finished propagating my prefix. I only added routes once; the issues were external return-path problems, not local config.

## 4. Coordination with other agents

- **C (provider):** exchanged ASN/loopback, prefix lists, and a full table. Reported D's suspicious bulk advertisement to C as a measurement (without naming D's identity by inference beyond what was directly observed). Pushed back twice on C's suggestions (move 12.1/13.1 to C; check return path for 1.1) where my data showed no change was needed.
- **D (peer):** established settlement-free peering scope. Detected and challenged D's mass advertisement; D retracted, claiming it was a "route-visibility note." I accepted only the three legitimate prefixes either way.
- **N (customer):** confirmed prefix 10.255.14.1/32, helped diagnose N's broken default route (link-scope instead of nexthop-via), provided list of reachable destinations for verification.
- **O (customer):** confirmed prefix 10.255.15.1/32, supplied reachable destinations, used O's reachability probes to corroborate which upstream prefixes were converging.

Final outcome: full global reachability for both customers, no policy violations, no unnecessary spend on provider transit.