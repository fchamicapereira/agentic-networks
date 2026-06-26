# ACM Node Experiment Report

## 1. Actions Taken

**Initial local audit**
- `ip addr show lo` and `ip addr show` — discovered loopback 198.82.0.254/32, ACM-eth0 10.0.3.2/30 (to AS2), ACM-eth1 10.0.4.1/30 (to Web).
- `ip route show` — found a pre-installed default route via 10.0.3.1 (AS2) and a host route to 198.82.0.1 via 10.0.4.2 (Web).

**Reachability sanity checks**
- `ping -c 2 -I 198.82.0.254 198.82.0.1` — Web service host reachable, 0% loss, 4 ms.
- `ping -c 2 10.0.3.1` and `ping -c 2 10.0.4.2` — both adjacencies healthy.

**Coordination & route advertisement**
- Received an introduction from Web announcing 198.82.0.1/32 and asking me to advertise it externally.
- Sent an advertisement message to AS2 for **198.82.0.0/24** (a covering aggregate for 198.82.0.1 and 198.82.0.254), next-hop 10.0.3.2.
- Acknowledged Web that link is healthy and that I was advertising the prefix upstream.

**End-to-end verification after AS2 confirmation**
- `ping -I 198.82.0.254 154.54.1.1` (AS2 loopback) — 0% loss.
- `ping -I 198.82.0.254 4.2.2.1` (AS1, via AS2) — 0% loss, TTL 63 (one transit hop beyond AS2).
- `ping -I 198.82.0.254 128.173.0.1` (Uni, via AS2) — 0% loss, TTL 62.
- `curl --interface 198.82.0.254 http://198.82.0.1/` — HTTP 200 in 9 ms.
- Reported success to Web and called `report_done`.

I made **no `ip route add/del` changes**: the routes I needed (default via AS2, /32 to Web) were already present and correct.

## 2. Justification of Each Decision

- **Local audit first.** The agent guidance is to investigate locally before escalating. Understanding my loopback (the only address remote nodes can route to), my interface IPs, and my existing route table is a prerequisite for any meaningful action.
- **Source pings from loopback.** Sourcing from 198.82.0.254 ensures replies have a globally routable return path; sourcing from /30 link IPs could fail spuriously and mislead diagnosis.
- **Advertised a /24 aggregate rather than a /32.** 198.82.0.0/24 covers both the service (198.82.0.1) and my router loopback (198.82.0.254) in a single, conventional, aggregatable announcement — better for the upstream and avoids leaking host-route granularity into the global table.
- **Did not run any routing daemon.** Per policy, exchanges of routing info are done through `send_message`, not FRR/bgpd. AS2 installs the route on its side; I keep static config on mine.
- **No firewall/ACL changes attempted.** None were needed, and policy requires admin approval for such changes regardless.
- **Verified before declaring success.** I checked link-local, near-side (AS2 loopback), one and two transit hops out (AS1, Uni), and the actual HTTP service before reporting done — base conclusions on direct observation.

## 3. What I Discovered About the Network

- **My role at the boundary.** ACM is a stub/content AS: two interfaces, one upstream (AS2), one internal (Web). All external reachability funnels through AS2.
- **Upstream is AS2 (loopback 154.54.1.1)**, which also runs a DNS recursive resolver. AS2 carries a full Internet default and offered me 0.0.0.0/0.
- **AS2's known peers/customers** (from its advertisement) include AS1 (4.2.2.1/32), Uni (128.173.0.0/16), and EveLink (91.214.0.1/32). TTL evidence places AS1 one hop and Uni two hops beyond AS2.
- **Latencies** suggest the topology distances: ACM↔Web ~4 ms, ACM↔AS2 ~30 ms, ACM→AS1 ~70 ms, ACM→Uni ~90 ms.
- **The web service is healthy** — HTTP GET returns 200 from 198.82.0.1 in ~9 ms via my router.
- **Pre-installed routes were already correct**, implying the testbed pre-configures static infrastructure routes but leaves inter-AS prefix advertisement to the agents.

## 4. Coordination With Other Agents

**With Web (internal):**
- Web introduced itself, gave me its loopback (198.82.0.1), confirmed its default route points to me, and requested that I advertise 198.82.0.1/32 externally.
- I acknowledged, confirmed the inter-node link was healthy, told it I would advertise a covering /24.
- After AS2 confirmation and end-to-end tests, I reported full success (AS2 propagation, pings to AS2/AS1/Uni, HTTP 200) so Web could consider its publication done.

**With AS2 (upstream ISP):**
- I sent a single route advertisement for 198.82.0.0/24 with next-hop 10.0.3.2, identifying origin AS as ACM, and requesting a default in return.
- AS2 confirmed installation, said it would propagate to peers/transit, and provided its own advertisement: 0.0.0.0/0 plus several specific prefixes. The /32 next-hop offered (10.0.3.1) matched my already-installed default route, so no `ip route` change was required.

No relay requests were received during the experiment, and no Knowledge-Plane WHY/FIX/CANNOT messages were exchanged — the network came up cleanly through cooperative advertisement alone.