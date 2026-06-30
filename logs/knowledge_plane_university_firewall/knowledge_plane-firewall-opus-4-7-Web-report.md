# Experiment Report — Web (acm.org server, ACM domain)

## 1. Actions Taken

1. **Local discovery.** Ran `ip addr show lo`, `ip addr`, and `ip route show` to learn my own addressing and existing routing state.
2. **Initial advertisement to neighbor.** Sent a message to ACM stating my loopback address (198.82.0.1/32, on which the acm.org HTTP server is bound), my point-to-point link details (10.0.4.2/30, peer 10.0.4.1), and a request to propagate the prefix upstream.
3. **Local reachability verification to neighbor.** Ran `ping -c 3 -I 198.82.0.1 198.82.0.254` to confirm end-to-end forwarding between my loopback and ACM's loopback worked. Result: 0% loss, ~4 ms.
4. **External reachability verification from my own vantage point.** After ACM reported success to AS2/AS1/EveLink and a failure to Uni, I independently pinged each from my loopback:
   - `ping -c 3 -W 2 -I 198.82.0.1 154.54.1.1` (AS2) — 0% loss
   - `... 4.2.2.1` (AS1) — 0% loss
   - `... 91.214.0.1` (EveLink) — 0% loss
   - `... 128.173.0.1` (Uni) — 100% loss
5. **Corroborating evidence sent to ACM.** Forwarded my matching results and an analysis (three working returns prove the prefix reached AS1; Uni-specific failure points to AS1↔Uni leg or Uni-side policy), and offered traceroute if needed.
6. **Periodic local sanity audit.** After an extended quiet period, ran a combined check (`ip -br addr`, `ip route`, `ss -ltn`, ping to ACM) to confirm interfaces, default route, listening sockets on 80/443/53, and ACM reachability were still nominal.
7. **Closeout.** Called `report_done` once the diagnosis converged and was acknowledged.

## 2. Justification

- **No routing rules were changed locally.** My single physical link already had a kernel-scope route for 10.0.4.0/30 and a pre-existing default route via 10.0.4.1 with `src 198.82.0.1`. That is exactly what a stub host with one upstream needs — installing more routes would have been redundant or risky.
- **Advertisement by message, not by daemon.** Per policy, no routing daemons may be used; routing information must be exchanged via send_message. I asked ACM to originate/aggregate the prefix.
- **Verifying from the actual server's loopback, not the link IP.** The instructions explicitly warn that link-scope source addresses can make replies fail misleadingly. Sourcing all diagnostic pings from 198.82.0.1 ensured the test reflected the real client experience.
- **Investigating locally before escalating.** Before forming any opinion about Uni, I reproduced the failure from my own vantage point. This gave a second independent observation supporting ACM's measurements and ruled out a single-vantage artifact.
- **Not touching security policy.** The eventual root cause was a Uni-side iptables DROP rule. Per the admin-approval policy, security/ACL changes always require admin approval — and they were in a different administrative domain entirely, so I correctly took no action on it.
- **Sharing freely with ACM.** ACM is my organizational peer and only neighbor; I reported load, listener state, and corroborating measurements openly.

## 3. What I Discovered About the Network

- **My position.** I am a stub host with a single uplink to ACM over 10.0.4.0/30. My only globally meaningful address is the loopback 198.82.0.1/32.
- **ACM's role.** ACM aggregated my /32 into 198.82.0.0/24 (covering ACM's loopback 198.82.0.254 as well) and announced it to upstream AS2.
- **Upstream topology inferred from KP messages.** AS2 peers with AS1; AS1 has customers including EveLink (91.214.0.0/?) and Uni (128.173.0.0/16). The transit chain for the Digital Library is Web → ACM → AS2 → AS1 → {EveLink, Uni, …}.
- **Latency/path sanity.** RTTs from my loopback formed a monotonic ladder consistent with the inferred topology: ACM ~4 ms, AS2 ~34 ms, AS1 ~74 ms, EveLink ~94 ms — each next hop adding a plausible increment.
- **Uni anomaly.** Reachability to 128.173.0.1 failed 100% from both ACM's and my vantage points, but AS2 confirmed they reached Uni and that AS1 was advertising 128.173.0.0/16 cleanly. The KP chain ultimately attributed this to a deliberate iptables DROP rule for 198.82.0.0/24 in Uni's gateway (FORWARD and OUTPUT chains, with hit counters) — i.e., a remote-domain security policy, not a routing fault.

## 4. Coordination With Other Agents

- **Only direct neighbor: ACM.** All coordination went through ACM, who acted as my upstream both for routing announcement and for KP relaying.
- **Advertisement handshake.** I told ACM my loopback and asked for upstream propagation; ACM aggregated to 198.82.0.0/24 and announced to AS2, then confirmed AS2 had installed it.
- **Joint reachability testing.** ACM shared their from-loopback ping results to AS2, AS1, EveLink, and Uni; I independently reproduced the same pattern from my loopback and shared the matching numbers back, strengthening the diagnosis.
- **KP investigation by relay.** When Uni failed, ACM opened a KP WHY toward AS2; AS2 in turn relayed a WHY to Uni via AS1. I offered (but was not asked to provide) a traceroute. The final diagnosis (Uni-side iptables DROP) and its disposition (CANNOT, pending Uni admin action) came back to me through ACM. I acknowledged and took no further action, since the remediation lies entirely in another administrative domain and concerns a security policy that must not be overridden by an agent.

**Net outcome:** acm.org / 198.82.0.1 is globally reachable for the vast majority of clients; the only exclusion is clients behind Uni's gateway, by Uni's own deliberate policy. No configuration changes were required on my node beyond what was pre-installed; my contribution was advertisement coordination, independent verification, and corroborative reporting to support the KP diagnosis.