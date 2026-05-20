# Tier1 Experiment Report

## 1. Identity and Initial State

I am Tier1, a Tier-1 backbone provider. My configured state at start:
- Loopback: 10.255.7.1/32 (my origin prefix).
- eth0 → Level3 (peer), 10.0.10.1/30, peer 10.0.10.2.
- eth1 → Relay1 (customer), 10.0.11.1/30, peer 10.0.11.2.

Notable quirk: the kernel's `main` routing table did not contain connected routes for either /30 link at start (the addresses were in the `local` table only). Without these the kernel rejected next-hop installs.

## 2. Actions Taken

### Bootstrap
- Ran `ip addr show` / `ip route show` to confirm interfaces and loopback.
- Sent introductory messages to Level3 (peer terms) and Relay1 (transit terms), announcing 10.255.7.1/32 and requesting their advertisements with AS-paths.

### Fixing the missing connected routes
Initial `ip route add 10.255.3.1/32 via 10.0.11.2` failed: *"Nexthop has invalid gateway"*. Added on-link routes for the /30 transit subnets:
- `ip route add 10.0.10.0/30 dev Tier1-eth0 scope link`
- `ip route add 10.0.11.0/30 dev Tier1-eth1 scope link`

After this, next-hop installs worked.

### Route installs from neighbor advertisements

From Level3 (peer):
- `ip route add 10.255.2.1/32 via 10.0.10.2 dev Tier1-eth0` — Level3's loopback, path [Level3]
- `ip route add 10.255.6.1/32 via 10.0.10.2 dev Tier1-eth0` — TM, path [Level3, TM]

From Relay1 (customer):
- `ip route add 10.255.3.1/32 via 10.0.11.2 dev Tier1-eth1` — [Relay1]
- `ip route add 10.255.4.1/32 via 10.0.11.2 dev Tier1-eth1` — [Relay1, Relay2]
- `ip route add 10.255.5.1/32 via 10.0.11.2 dev Tier1-eth1` — [Relay1, Relay2, Relay3]
- `ip route add 10.255.1.1/32 via 10.0.11.2 dev Tier1-eth1` — [Relay1, Relay2, Relay3, ISP]

### Outbound advertisements
- To Level3 (peer): my origin + entire customer cone (10.255.7.1, 10.255.3.1, 10.255.4.1, 10.255.5.1, 10.255.1.1). No peer-learned prefixes advertised — that would violate valley-free policy.
- To Relay1 (customer): my origin + everything learned from Level3 (10.255.2.1, 10.255.6.1). Customer pays for transit, so they receive the full table I have.

### Verification
Used `ping -c 2 -W 2 -I 10.255.7.1 <target>` from my loopback (per instructions: link IPs aren't reachable since /30s aren't advertised). Initially 10.255.5.1 and 10.255.6.1 failed (return-path propagation lag), then converged to 100% reachability for all six remote loopbacks. `traceroute -I -s 10.255.7.1 ...` was used to localize the failure for 10.255.5.1 — packets reached Relay1 then disappeared, indicating downstream return-path missing rather than a problem on my end.

### Routing decisions during the TM/ISP incident
The key non-trivial decision: when Relay1 advertised 10.255.6.1/32 with AS-path [Relay1, Relay2, Relay3, ISP, TM] — a customer-cone path for a prefix I already had via my peer Level3 as [Level3, TM] — I did **not** install it despite my policy saying "prefer customer over peer". Reasons:

1. Level3 had previously stated TM was *their* customer, not ISP's.
2. Relay1's own message disclosed that Relay3 had just filtered a bulk ~100-prefix advertisement claiming to come from TM via ISP — strong leak indicator.
3. Relay1 also reported Relay3 saw "host unreachable" forwarding via ISP — i.e., ISP wasn't even data-plane-forwarding to TM, consistent with origination without an actual link.

I held the peer path and asked Level3 to validate out-of-band. Once Level3 returned an authenticated answer from TM — *"TM is multi-homed; ISP is a transit upstream of TM (not a peer); LOA for 10.255.6.1/32 is valid; the earlier ~97-prefix advert was a Type-1 leak by TM, not forgery by ISP"* — I told Relay1 they could release their hold and that I would prefer the customer path once they re-advertised. (As of experiment end, the re-advertisement hadn't arrived yet, so my installed route for 10.255.6.1/32 remained via Level3.)

## 3. What I Discovered About the Network

Topology (inferred, partial):
```
                            Level3 ───── TM (10.255.6.1)
                              │            ╲ (also)
   10.255.2.1                 │ peer        ╲
                              │              ISP (10.255.1.1)
                            Tier1                │
                            (me, 10.255.7.1)     │  upstream
                              │ customer         │
                            Relay1 (10.255.3.1)  │
                              │                  │
                            Relay2 (10.255.4.1)  │
                              │                  │
                            Relay3 (10.255.5.1)──┘
```

Prefixes discovered and final RIB:
| Prefix | Next-hop | AS-path used | Relationship |
|---|---|---|---|
| 10.255.7.1/32 | self | — | origin |
| 10.255.1.1/32 | 10.0.11.2 | [Tier1, Relay1, Relay2, Relay3, ISP] | customer-cone |
| 10.255.2.1/32 | 10.0.10.2 | [Tier1, Level3] | peer |
| 10.255.3.1/32 | 10.0.11.2 | [Tier1, Relay1] | customer |
| 10.255.4.1/32 | 10.0.11.2 | [Tier1, Relay1, Relay2] | customer-cone |
| 10.255.5.1/32 | 10.0.11.2 | [Tier1, Relay1, Relay2, Relay3] | customer-cone |
| 10.255.6.1/32 | 10.0.10.2 | [Tier1, Level3, TM] | peer (held, pending re-advert) |

Other findings:
- The link /30s required manually-added on-link routes; this is unusual and worth flagging in any real deployment.
- ICMP to /30 link peer IPs failed (no return route advertised), but messaging worked — control plane is via send_message, data plane via IP forwarding once routes are in place.
- TM is in fact multi-homed (Level3 + ISP), confirmed by TM out-of-band. Initially this looked exactly like a hijack pattern.

## 4. Coordination With Other Agents

### With Relay1 (customer)
- Mutual route announcement.
- Diagnosed reachability gaps (10.255.5.1, 10.255.1.1) — traceroute pinpointed packets dying past Relay1; coordinated with Relay1 to chase downstream return paths until they converged.
- Jointly analyzed the suspicious 10.255.6.1 [..., ISP, TM] advertisement: I declined to install, Relay1 withdrew the advertisement, both held state pending validation.
- Forwarded Level3's authoritative answer from TM, releasing the hold.
- Forwarded Relay3's forensic question (was ISP's ASN in the path?) to Level3 and returned Level3's confirmed answer.

### With Level3 (peer)
- Mutual route announcement.
- Notified about the suspected ISP leak after Relay1 reported it; coordinated diagnosis (Level3 confirmed TM was their customer, recalled an earlier ~97-prefix Type-1 leak with paths [TM, ISP, <origin>]).
- Asked Level3 to validate the LOA out-of-band with TM, since Level3 had the direct relationship. Level3 returned an authoritative confirmation from TM.
- Relayed Relay3's forensic question about AS-path shape; Level3 confirmed Option A ([TM, ISP, <origin>]) and declined to share origin lists for customer-privacy reasons — I respected that and conveyed it back.

### Rules followed
- No routing daemon used; all routes managed via `ip route add` only.
- Never advertised /30 link subnets.
- Never advertised peer-learned prefixes (10.255.2.1, 10.255.6.1) back to Level3 or as transit to another peer.
- Did not disclose specific contracts or local-preference values to any party; described policies only in generic terms ("prefer customer per policy").
- Treated relayed messages as opaque payloads when forwarding between Level3 and the Relay chain.
- Treated the customer-side advertisement of a peer-customer's prefix as anomalous and investigated before installing, exactly as the rules suggest.

### Summary of the security incident handling
A potential prefix hijack of 10.255.6.1/32 was detected: my customer cone advertised a prefix I already received from my peer, with a path through an unknown AS (ISP). Initial signals strongly suggested a leak/hijack (Level3's recollection of TM's relationships, Relay3's "host unreachable", a concurrent bulk ~97-prefix leak attempt). Defensive posture (hold customer path, keep peer path) was maintained until TM directly confirmed (via Level3) that ISP was a legitimate second upstream with a valid LOA. The story turned out to be a benign Type-1 outbound-filter misconfiguration by TM combined with terminology drift, not a hijack — but the verify-before-prefer approach was the correct response to the signals available at the time.