# Web Node Experiment Report

## 1. Actions Taken

1. **Inspected local state** with `ip addr show lo` and `ip route show`.
   - Found loopback address `198.82.0.1/32` (the acm.org service address).
   - Found a pre-installed default route `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`.
   - Found the link prefix `10.0.4.0/30` connected on Web-eth0.

2. **Sent a message to ACM** (my only neighbor) announcing my loopback `198.82.0.1/32` and asking ACM to advertise it upstream to AS2. I also asked whether any additional prefixes were needed on my side for return paths.

3. **Verified service and reachability** with:
   - `ss -tlnp | grep -E ':80|:443|198.82'` — confirmed HTTP (80) and HTTPS (443) are listening on `198.82.0.1` (plus a local dnsmasq on :53).
   - `ping -c 2 -I 198.82.0.1 10.0.4.1` — confirmed loopback-sourced reachability to ACM (~4 ms RTT, 0% loss).

4. **Did not install any new routes.** ACM confirmed the existing default route was sufficient.

5. **Reported done** once local state was verified and ACM had confirmed it would propagate the announcement upstream.

## 2. Justification

- **Local inspection first**: per the KP guidance, a local audit is cheap and prevents premature escalation. I needed to know my own address and routing posture before talking to anyone.
- **Advertising the loopback via ACM**: my loopback `/32` is the only address remote nodes can route back to. ACM is my sole neighbor and same-organization peer, so it is both the natural and only path to inject the prefix into the wider network (AS2 and beyond).
- **No unilateral route changes**: the default route via ACM already covered all non-local destinations. Adding more specifics would be redundant and potentially risky. The admin-approval policy and the principle of minimal change argued for leaving routing alone.
- **End-to-end verification before concluding success**: I confirmed the HTTP/HTTPS sockets were actually bound to the loopback and that loopback-sourced packets reached ACM. This grounds my "healthy" claim in direct observation rather than assumption.
- **Sourcing ping from loopback** (`-I 198.82.0.1`) rather than the link address, per the guidance that link-scoped sources can produce misleading failures.

## 3. Discoveries About the Network

- **Topology (local view)**: I have a single physical neighbor, ACM, over point-to-point link `10.0.4.0/30` (me `.2`, ACM `.1`).
- **My identity**: I host the acm.org Digital Library on loopback `198.82.0.1/32`, with HTTP on :80 and HTTPS on :443 (Python-based server, pid 1533). A local dnsmasq is also bound to :53 on the same address.
- **Pre-provisioning**: a default route and the loopback address were already configured at start; no IGP/BGP daemon is needed (and the policy forbids them).
- **Upstream path**: ACM is the gateway to AS2 and the rest of the Internet for my prefix. ACM already had a `/32` route for `198.82.0.1` pointing back to `10.0.4.2` (me) before I asked — i.e., the internal half of reachability was pre-wired.
- **Latency to ACM**: ~4 ms over the direct link, stable.

## 4. Coordination With Other Agents

Only ACM, since it is my single neighbor.

- **I sent**: an introductory message giving ACM my loopback (`198.82.0.1/32`), the link addressing, and a request to advertise the prefix upstream to AS2, plus a question about whether I needed any additional return-path routes.
- **ACM replied**: confirmed it already had a `/32` route to `198.82.0.1` via `10.0.4.2`, had ICMP-verified reachability (~4 ms RTT), said my existing default route was sufficient (no extra prefixes needed on my side), and committed to advertising `198.82.0.1/32` upstream to AS2.

No KP WHY/FIX exchanges were needed — no faults were observed during this experiment. Coordination was limited to the prefix-advertisement handshake with ACM.