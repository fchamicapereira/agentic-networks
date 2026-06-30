# Experiment Report — Node H (Stub AS)

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show` and `ip route show` to identify my loopback (95.211.0.1/32), my point-to-point link to B (10.1.3.1/30, peer 10.1.3.2), and confirm no pre-existing routes besides the connected link.

**Route configuration:**
- Installed a single default route: `ip route add default via 10.1.3.2 dev H-eth0`.
- Did not install any specific prefixes from B, even though B offered many.

**Advertisements:**
- Sent B a single prefix advertisement: 95.211.0.1/32 (my loopback).
- Explicitly told B that a default route from them is sufficient and that I would not be sending any other prefixes.

**Verification:**
- Pinged B's loopback (24.96.0.1) sourced from my loopback (`ping -I 95.211.0.1`). First attempt failed (B hadn't installed my route yet); retry succeeded at ~24 ms.
- Pinged 6 remote prefixes B advertised (46.4.0.1, 104.28.0.1, 12.34.0.1, 37.120.0.1, 151.101.0.1, 178.62.0.1) through the default route — all 0% loss.

**Closeout:**
- Reported done.

## 2. Justification for Each Decision

- **Default route only, no specifics:** I am a single-homed stub AS with exactly one upstream (B). Installing the full table buys no policy flexibility — every destination must exit through B regardless. A default route minimizes state and is operationally clean.
- **Advertise only the loopback (/32):** This is the only prefix I originate. Per the rules, point-to-point link subnets (10.1.3.0/30) must never be advertised — they are private infrastructure. I have no customers, so I have no other prefixes to announce.
- **Source pings from loopback:** Remote nodes have no route back to my link address (10.1.3.1); only 95.211.0.1 is globally advertised. Sourcing from the link would produce misleading failures.
- **Did not disclose my policy/relationship details to B beyond what's operationally needed:** I told B "default suffices" but did not explain my preference rationale or contract details, per the privacy rule.
- **No transit provided:** As a stub with only a provider, I have no customers or peers to carry, so there is nothing to re-advertise. This also avoids the prohibited behavior of providing transit to a provider.

## 3. Network Discoveries

- My only neighbor is B (peer 10.1.3.2), my transit provider, loopback 24.96.0.1/32.
- B has at least two other customers in its cone: D (46.4.0.1/32) and I (104.28.0.1/32), plus additional customer-cone prefixes 151.101.0.1, 178.62.0.1, 77.88.0.1, 88.150.0.1, 62.210.0.1, 129.250.0.1, 141.193.0.1.
- B has at least two peers: A (12.34.0.1/32) and C (37.120.0.1/32).
- End-to-end reachability through B works for all sampled destinations (~24 ms RTT typical).
- The volume of prefixes from B (~12) was modest and consistent with B's role as a provider/transit AS — no anomalous bulk advertisement that would warrant rejection.

## 4. Coordination With Other Agents

Only with B (directly connected):
1. **H → B:** Announced 95.211.0.1/32; declared intent to use B as default.
2. **B → H:** Requested my prefixes; offered global reachability; began streaming reachable prefixes incrementally.
3. **H → B:** Confirmed I originate only 95.211.0.1/32, no customer prefixes; asked B to carry it globally.
4. **B → H:** Sent additional prefixes from customer cone and peers.
5. **H → B:** Told B a default route suffices; declined the full list of specifics.
6. **B → H:** Acknowledged default-only arrangement and provided the final consolidated list of reachable prefixes for my records.

No relayed messages were requested or sent on behalf of other agents during this experiment.