# AS2 Experiment Report

## 1. Actions Taken

**Initial discovery**
- `ip addr show` / `ip route show` to learn my own state: loopback 154.54.1.1/32, AS2-eth0 (10.0.2.2/30 toward AS1), AS2-eth1 (10.0.3.1/30 toward ACM). Pre-existing routes: default via 10.0.2.1, plus /32s to 198.82.0.1 and 198.82.0.254, and a /30 to 10.0.4.0/30 via ACM.
- `ping -I 154.54.1.1` from loopback to 10.0.2.1, 10.0.3.2, and 198.82.0.1 — all responded, confirming L3 health on both links and through ACM.

**Route installation (from neighbor advertisements)**
- AS1 (peer) announced 4.2.2.1/32, 128.173.0.1/32, 91.214.0.1/32. Installed via `ip route add ... via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`.
- ACM (customer) announced 198.82.0.0/24. Installed via 10.0.3.2; deleted the now-redundant /32s for 198.82.0.1 and 198.82.0.254 (covered by the /24).
- AS1 sent an updated aggregate 128.173.0.0/16 for Uni. Replaced the /32 with the /16.

**Advertisements sent**
- To AS1 (peer): 154.54.1.1/32 and 198.82.0.0/24 — only my own loopback and customer cone.
- To ACM (customer): 0.0.0.0/0 default, plus informational listing of currently reachable peer prefixes.

**KP investigation and local fix**
- AS1 reported an ICMP-Redirect-induced traceroute loop on packets to 10.0.0.99.
- Diagnosed locally: `sysctl net.ipv4.conf.*.send_redirects` returned 1, and `ip route get 10.0.0.99 from 4.2.2.1 iif AS2-eth0` showed the kernel marking the cache entry `<redirect>` because the packet arrived on AS2-eth0 and would exit AS2-eth0 to a next-hop on the same subnet.
- Applied fix: `sysctl -w net.ipv4.conf.{all,AS2-eth0,AS2-eth1,default}.send_redirects=0`, then `ip route flush cache`. Re-ran `ip route get` and confirmed the `<redirect>` flag was gone.
- Reported diagnosis, fix, residual TTL-bounce behavior, and admin-decision note back to AS1 via KP.

## 2. Justification

- **Why install AS1's /32s then replace with /16**: I install what neighbors advertise; aggregates are preferred for table size and reflect what the neighbor actually wants to be the authoritative announcement.
- **Why aggregate ACM's /24 and remove pre-existing /32s**: ACM owns the /24; per their advertisement the /24 covers both the web server and router loopback. Keeping the /32s would clutter the table with no benefit.
- **Why advertise only loopback + customer cone to AS1**: AS1 is a peer (settlement-free). Per standard peer export policy, I announce only my own prefixes and my customer cone — never peer-learned or provider-learned routes. AS1 stated the same policy explicitly.
- **Why give ACM a default**: ACM is a paying transit customer; full transit (default route) is exactly what they pay for, and they asked for it.
- **Why disable send_redirects unilaterally**: It is a routing-hygiene sysctl, not a security/ACL/auth/rate-limit policy. Local, easily reversible (one sysctl), well-known best practice on transit routers where redirects between routers cause loops rather than help. Therefore inside the "local, low-risk, reversible" envelope.
- **Why NOT install an RFC1918 discard route**: That is a policy choice with cross-domain implications (some operators tunnel RFC1918 between sites). AS1 explicitly declined and framed it as an admin decision; I deferred accordingly.

## 3. What I Discovered About the Network

- Topology around AS2: two direct neighbors — AS1 (peer, loopback 4.2.2.1) and ACM (customer, prefix 198.82.0.0/24, web server at 198.82.0.1).
- Beyond AS1 are at least two AS1 customers: Uni (128.173.0.0/16, host 128.173.0.1) and EveLink (91.214.0.1/32).
- I have no provider in this topology: my default route points to AS1 (the peer). This is anomalous for a real ISP and is the structural reason any unknown-destination packet hairpins back to AS1.
- A working DNS recursive resolver is supposed to listen on my loopback (per role description). End-to-end reachability of 154.54.1.1 from AS1 was confirmed, so clients in AS1's cone can in principle reach the resolver.
- Latencies observed: AS1 ~40 ms, ACM ~30 ms, ACM web server ~34 ms.
- Kernel default `send_redirects=1` combined with the AS1-facing default produced an observable cross-domain artifact (a redirect-driven loop visible in AS1's customer traceroutes), illustrating how local defaults can leak symptoms upstream.

## 4. Coordination With Other Agents

- **AS1 (peer)**: Exchanged route advertisements with explicit confirmation of peer export policy on both sides. AS1 verified reachability to 154.54.1.1 and 198.82.0.1 from 4.2.2.1. AS1 then raised a KP observation about ICMP Redirects on 10.0.0.99; I investigated locally, applied the send_redirects=0 fix, and reported the diagnosis, the fix, the residual TTL-bounce, and an offer to install an RFC1918 discard route. AS1 acknowledged the writeup, agreed the residual was cosmetic, and explicitly declined the discard route as an admin-policy decision pending consultation with their own customers.
- **ACM (customer)**: Received their /24 advertisement and request for a default route. Installed the /24, replied with the default route and a note of reachable peer prefixes. No further interaction was needed.
- **KP discipline followed**: investigated locally before escalating; based the diagnosis on direct observations (`sysctl`, `ip route get` cache flag); verified the fix by re-running the same probe; reported honestly what was fixed (the misleading ICMP Redirect) versus what remained (the TTL-bounce on unroutable destinations), and deferred the policy-level remedy to admins.