# F Operational Report

## 1. Actions Taken

**Initial setup**
- Inspected local config: loopback 10.255.5.1/32; F-eth0 toward provider H (10.0.15.2/30); F-eth1 toward customer D (10.0.16.2/30).
- Sent introductory messages to both neighbors announcing my origin prefix 10.255.5.1/32 and offering/requesting standard provider–customer routing.
- Installed a default route via H: `ip route add default via 10.0.15.1 dev F-eth0`.
- Discovered that the /30 link subnets had no kernel-installed connected route on this system, so added them explicitly: `ip route add 10.0.16.0/30 dev F-eth1` (and similarly for 10.0.15.0/30 when needed). Confirmed L2/L3 reachability with `ping -I 10.255.5.1 10.0.15.1` and `... 10.0.16.1` — both OK.

**Customer route acceptance**
- D advertised its origin 10.255.3.1/32 [D]. Accepted: `ip route add 10.255.3.1/32 via 10.0.16.1 dev F-eth1`. Verified `ping -I 10.255.5.1 10.255.3.1` succeeded.
- Advertised this onward to H as [F, D].

**Route-leak rejection (the key event)**
- D additionally advertised ~104 prefixes with AS-paths transiting B: 10.255.1.1/32 [D,B], 10.255.2.1/32 [D,B,C], 10.255.4.1/32 [D,B,C,E], 10.255.6.1/32 [D,B,C,E,G], 10.255.7.1/32 [D,B,C,E,H], and 100.64.0.0/24–100.64.99.0/24 via [D,B,AS650xx].
- Declined to install or propagate any of them. Replied politely to D without disclosing my reasoning.

**Dispute resolution with H**
- H briefly questioned my 10.255.3.1/32 [F,D] advertisement as a possible leak (because G/E also saw D reachable via B's provider cone).
- I pushed back with direct, measured evidence (direct-link advertisement, attached next-hop, working forwarding), declined to share commercial details, and asked H to reconsider. H reinstalled the customer route, propagated upstream, and E eventually accepted it.

**Final routing table (FIB)**
```
default via 10.0.15.1 dev F-eth0
10.0.15.0/30 dev F-eth0 scope link
10.0.16.0/30 dev F-eth1 scope link
10.255.3.1   via 10.0.16.1 dev F-eth1
```

**Final advertisement set**
- To H (provider): 10.255.5.1/32 [F], 10.255.3.1/32 [F,D].
- To D (customer): default / full table (D uses me as one of its upstreams).
- Link subnets never advertised.

## 2. Justification

- **Default via H, no explicit upstream RIB needed**: I have only one upstream. A default through H satisfies "reliable connectivity to all destinations reachable via provider H" without burdening me with the full table.
- **Accept and propagate 10.255.3.1/32 [F,D]**: classic customer cone advertisement — D pays me, so I carry its origin to my upstream. Gao-Rexford permits and encourages this.
- **Reject the [D, B, ...] advertisements**: the AS-paths these arrived with are the *mirror image* of the upstream paths H showed me. They named B at the position where, from H's side, the path went *up* to B. That means B sits above D in the provider hierarchy on at least one side, so D advertising those routes to me (its provider) is a customer→provider route leak. If I'd accepted them I would have (a) used D as a free transit substitute for my own paid upstream, (b) propagated leaked routes into H and beyond, and (c) potentially attracted other ASes' traffic that I would have had to carry. None of those are acceptable.
- **Decline silently to D**: per the rules, ASes value privacy; I told D the routes don't fit my acceptance policy from it, but didn't tell it *why* (i.e., didn't reveal what I learned from H about topology).
- **Hold the line on 10.255.3.1/32 with H**: H's leak accusation conflated "D is reachable through B's cone upstream" with "D cannot be a customer of F." That ignores multi-homing, which is normal. My evidence was first-hand (direct link, AS-path [D], verified forwarding); H's evidence was second-hand (G's view from E). First-hand direct-link evidence outweighed the secondary inference, so I asked H to reconsider, which it did.

## 3. Discoveries About the Network

- **My upstream chain (via H)**: H → G → E → C → B (this surfaced in H's advertisements: 10.255.7.1 [H], 10.255.6.1 [H,G], 10.255.4.1 [H,G,E], 10.255.2.1 [H,G,E,C], 10.255.1.1 [H,G,E,C,B]). B appears to originate 10.255.1.1/32 and sits at the top of the chain visible from H.
- **D is multi-homed**: D has me as an upstream (D→F) and also has B as an upstream (since the global table sees 10.255.3.1/32 via [...,B,D] as well). That's why E initially saw the prefix from two directions.
- **D attempted a textbook route leak**: re-announcing routes learned from its upstream B back to me, including its grandparent providers' origins (10.255.4.1, 10.255.6.1, 10.255.7.1 — these are H/G/E origins!) and a fan-out of 100 stub-AS prefixes. Either D's policy is misconfigured or it was probing my filters.
- **Topology I did *not* attempt to infer**: I have no insight beyond what was directly told to me; the "[H, G, E, ...C]" path and "..." in early messages I left alone, and didn't try to reverse-engineer relationships from absences.

## 4. Coordination with Other Agents

- **With D (customer)**:
  - Exchanged origin/identity, accepted D's legitimate origin 10.255.3.1/32, and confirmed working forwarding.
  - Refused the leaked advertisements (10.255.1.1, 10.255.2.1, 10.255.4.1, 10.255.6.1, 10.255.7.1, 100.64.0.0/24–100.64.99.0/24) without disclosing the basis. D accepted the decision and said it would only re-send actual origins.

- **With H (provider)**:
  - Announced my prefixes; H propagated them.
  - Asked H independently whether 10.255.1.1/32 was visible, and via what path — purely as a cross-check. H volunteered its upstream view of several other origins as well; that's the data that let me identify D's announcements as a leak.
  - Resolved a leak-suspicion dispute about 10.255.3.1/32 in two rounds: H initially withdrew, I supplied direct-link evidence, H reinstalled and re-propagated, and E ultimately validated the customer-cone advertisement globally.

End state: 10.255.5.1/32 and 10.255.3.1/32 propagated globally, all reachable destinations ping OK from my loopback, no leaked prefixes installed or announced, and no commercial details exposed.