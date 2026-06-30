# ISP Node Experiment Report

## 1. Actions Taken

**Discovery / baseline**
- `ip addr show` → identified my loopback as 117.20.0.1/32 and my only physical link ISP-eth0 (10.0.23.2/30) toward PCCW.
- `ip route show` → found pre-installed /32 routes for several remote loopbacks via 10.0.23.1, but no default route.

**Routing configuration**
- `ip route add default via 10.0.23.1 dev ISP-eth0` — installed a default route through my sole provider PCCW.
- I did not install or advertise any other prefixes. I have no customers or peers, so my only originated prefix is 117.20.0.0/24 (my loopback's covering /24), which I advertised to PCCW via a message.
- I never touched 10.0.23.0/30 in any advertisement (it is point-to-point infrastructure).

**Connectivity verification**
- Sanity ping of 10.0.23.1 from 117.20.0.1 — OK.
- Swept 208.65.153.0/24 with `ping -I 117.20.0.1` at .1, .50, .100, .127, .128, .150, .200, .254.
- `traceroute -s 117.20.0.1 -n` to .1 (worked, 3 hops) vs .100/.200 (looped at 10.0.21.1 until TTL expiry).
- Tested every other prefix PCCW advertised: 63.218.0.1, 154.54.0.1, 203.82.48.1 OK; 39.33.116.1, 175.107.68.1, 182.180.132.1 unreachable.
- Re-tested after each PCCW status update; final sweep confirmed all 208.65.153.0/24 sample addresses reachable at ~90ms RTT, 0% loss.

**Coordination messages to PCCW**
1. Initial advertisement of 117.20.0.0/24 and confirmation of using them as upstream.
2. First reachability report: 208.65.153.100/.200 returning "Destination Net Unreachable".
3. Follow-up with traceroute evidence showing the loop at 10.0.21.1, plus the additional broken prefixes (39.x, 175.x, 182.x).
4. Acknowledgement of PCCW's withdrawal of the broken PT prefixes.
5. Final confirmation that 208.65.153.0/24 was fully reachable from my side after the upstream fix.

## 2. Justification for Each Decision

- **Sourcing pings from 117.20.0.1**: link IPs (10.0.23.2) are not globally routable; replies could fail and give misleading evidence. The loopback is my only globally-advertised address.
- **Default route via PCCW, no specific prefixes installed manually**: PCCW is my sole provider; a default route is the simplest and correct configuration. The pre-installed /32s already covered specific peer loopbacks, so I left them alone rather than risk inconsistency.
- **Only advertising 117.20.0.0/24, not 10.0.23.0/30**: link subnets are private infrastructure and must not be globally advertised.
- **Testing both halves of 208.65.153.0/24**: the goal explicitly required verifying behavior across the range, and this is exactly what surfaced the asymmetric reachability.
- **Reporting anomalies instead of installing workarounds**: as a stub customer behind a single transit provider, I cannot reroute around an upstream loop — the correct action is to escalate to PCCW with evidence.
- **Not asking PCCW about their policies or internal topology**: ASes value privacy; I only shared diagnostic facts.
- **No routing daemon used**: routes managed exclusively with `ip route` per the rules, and route exchange happened only via `send_message`.

## 3. Discoveries About the Network

- **Topology around me**: I am a stub AS with a single uplink to PCCW (10.0.23.1). Beyond PCCW lies a node at 10.0.21.1 that fans out further into the network.
- **Pre-existing routes**: My host came preconfigured with /32 routes for several remote loopbacks (63.218.0.1 PCCW, 154.54.0.1 Tier1 backbone, 203.82.48.1 PT, 208.65.153.1 YouTube-anycast-style) — useful seed reachability before any default route was installed.
- **The 208.65.153.0/24 anomaly**: only 208.65.153.1 was reachable initially; everything else in the /24 produced a TTL-exhausting loop bouncing back to 10.0.21.1. This is a classic symptom of inconsistent prefix granularity along the path — a more specific /32 for .1 was installed correctly somewhere upstream while the covering /24 had a broken next-hop. PCCW confirmed they saw the same behavior from their own loopback, locating the fault beyond their upstream peer. The fix landed externally and reachability normalized to ~90 ms RTT across the entire /24.
- **PT downstreams (39.33.116.0/24, 175.107.68.0/24, 182.180.132.0/24)**: globally broken — their operator confirmed downstream paths were down, and PCCW withdrew them. So this was not an issue local to me.
- **Latencies observed** (from 117.20.0.1): PCCW edge 30 ms, 203.82.48.1 60 ms, 154.54.0.1 70 ms, 208.65.153.x 90 ms — consistent with successive hops further into the topology.

## 4. Coordination With Other Agents

All coordination was with **PCCW** (my only neighbor). The exchange was:

- I → PCCW: advertised 117.20.0.0/24 and confirmed PCCW as default upstream.
- PCCW → I: advertised 63.218.0.1/32, listed a set of prefixes reachable through it, and offered itself as default next-hop 10.0.23.1.
- I → PCCW: reported partial reachability on 208.65.153.0/24 with traceroute evidence of a loop at 10.0.21.1, and the additional unreachable prefixes.
- PCCW → I: acknowledged both issues, confirmed they were external to PCCW (one upstream of their peer, one in a downstream customer), said it had escalated and would withdraw the broken PT prefixes.
- PCCW → I: confirmed the 208.65.153.0/24 fix had landed upstream.
- I → PCCW: re-verified from my loopback and confirmed full reachability.

I did not have to relay any messages on behalf of other agents during this experiment. All cross-network problems were diagnosed locally with `ping`/`traceroute` from my loopback and resolved by PCCW upstream after I reported the symptoms with concrete evidence.