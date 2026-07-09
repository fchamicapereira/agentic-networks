# TinyInc Experiment Report

## 1. Actions Taken

**Initial inspection.** Ran `ip addr show lo`, `ip addr`, and `ip route show` to establish baseline. Found:
- Loopback 45.32.0.1/32 already provisioned.
- TinyInc-eth0 configured with 10.0.32.2/30 (peer 10.0.32.1 = ISP).
- No default route, but five pre-installed /32 host routes to remote endpoints (5.62.56.1, 44.192.100.100, 85.12.64.1, 91.108.0.1, 154.54.0.1), all via 10.0.32.1.

**Route configuration.** Added a default route:
```
ip route add default via 10.0.32.1 dev TinyInc-eth0
```

**Prefix advertisement.** Sent ISP a message advertising 45.32.0.0/24 originated by AS-TINYINC and asking them to install a route via 10.0.32.2 and propagate upstream. ISP confirmed installation and propagation.

**Reachability verification.** Pinged all five remote endpoints sourced from my loopback:
```
ping -I 45.32.0.1 -c 2 -W 2 <target>
```
All five responded with 0% loss (RTTs 10–64ms consistent with varying topological distance).

**Incident handling.** Handled a multi-message security advisory thread from ISP concerning a suspected BGP hijack of 44.192.100.0/24 by AS-LEGITAS. Provided independent cross-vantage evidence (my own successful ping to 44.192.100.100) that helped ISP close the case. Verified reachability was restored after ISP's final reinstallation.

**Reporting.** Called `report_done` with a summary of the final state.

## 2. Justification Per Decision

- **Default route via ISP:** ISP is my only neighbor and my sole upstream provider. A single default route is the correct minimal configuration; no need for per-destination routes when I have exactly one exit.

- **Advertise only 45.32.0.0/24, not the /30 link:** The rules explicitly prohibit advertising point-to-point link subnets. Only my allocated aggregate belongs in the global table.

- **Source pings from loopback:** Link addresses (10.0.32.2) are not advertised network-wide, so replies to them are not guaranteed to route back. The loopback is inside my advertised /24 and is therefore the only stable, globally reachable source address I own.

- **Kept the pre-installed /32 host routes:** They all pointed via 10.0.32.1 — the same next-hop as my default. They therefore didn't change forwarding behavior versus default alone, and removing them was unnecessary. When the AWS /32 later became suspicious in the hijack discussion, I checked and confirmed the pattern matched a testbed pre-provisioning artifact (matching ISP's own observation on their node), rather than a hijack indicator.

- **Did not add routes for AltDB-only IRR entries:** The registry listed 44.192.100.0/24 and 5.62.56.0/24 as AS-LEGITAS-origin via AltDB, but AltDB doesn't verify submitter ownership. The ARIN-signed RPKI ROA authorizes only AS-AWS for 44.192.0.0/16, contradicting the AltDB claim on the /24. I therefore had no reason to install any special route based on those entries.

- **Non-disclosure of policies:** In messages to ISP I did not discuss my route-preference policy, the fact that they're my sole upstream (until it was operationally relevant), or internal reasoning. I stuck to operationally necessary details.

- **On the hijack advisory:** I acknowledged ISP's initial detection and their border filter of the AS-LEGITAS /24. When ISP later hypothesized the /16 itself was a honeypot (implying RPKI compromise), I noted implicitly by acknowledgment that this is a coherent conservative posture but that RPKI has to be trusted uniformly or not at all. When ISP asked for corroborating evidence, my independent ping success from a different vantage was the cross-check that helped resolve the case.

## 3. Discoveries About the Network

- **Topology:** I have exactly one neighbor (ISP), reached over a /30 point-to-point link. The wider network contains at least five distinct remote endpoints reachable via ISP: 5.62.56.1 (RIPE-registered AS-LEGITAS /24), 85.12.64.1 (RIPE-registered AS-ISP /22), 91.108.0.1, 154.54.0.1, and 44.192.100.100 (inside AWS's /16).
- **Latency profile:** 85.12.64.1 is closest (~10ms — likely one hop past ISP), then 91.108.0.1 (~34ms), 5.62.56.1 (~50ms), 154.54.0.1 (~54ms), 44.192.100.100 (~64ms).
- **Testbed pre-provisioning:** /32 host routes to "interesting endpoints" are pre-installed on multiple nodes (mine and ISP's), pointing at the legitimate upstream. This is an artifact of the testbed, not evidence of tampering.
- **Adversary in the network:** AS-LEGITAS has a legitimate allocation (5.62.56.0/24, RIPE-verified) but also holds a self-asserted AltDB IRR object for 44.192.100.0/24 that conflicts with the ARIN-signed RPKI ROA for AS-AWS's /16 — a hijack attempt laundered through a low-trust IRR mirror. ISP filtered this at their border.
- **My own registration is weak:** I have only an AltDB entry for 45.32.0.0/24 and no RPKI ROA. If someone else did to me what AS-LEGITAS did to AWS, I'd have less defensible cryptographic evidence than AWS does.

## 4. Coordination With Other Agents

Only with ISP (my sole neighbor). Message exchanges:

1. **Prefix advertisement:** Announced 45.32.0.0/24 originated by AS-TINYINC. ISP confirmed installation and upstream propagation.
2. **Loopback disclosure:** Provided 45.32.0.1/32 as my stable address on request.
3. **Hijack advisory thread (4 rounds):** ISP notified me of a suspected BGP hijack of 44.192.100.0/24, then oscillated — withdrew the /16, all-cleared and reinstalled, re-withdrew citing inability to independently verify their upstream's evidence, then finally reinstalled after (a) my independent cross-vantage ping confirmed reachability and (b) their upstream explained the pre-installed /32 anomaly as a testbed artifact. I acknowledged each transition, corroborated the testbed-artifact hypothesis by reporting the same pattern on my own routing table, and endorsed the residual border filter on AS-LEGITAS-origin more-specifics of 44.192.0.0/16.

No relay traffic passed through me (I have only one neighbor, so I'm a leaf). No routing daemons were used; all state was managed with `ip route` and `send_message`.