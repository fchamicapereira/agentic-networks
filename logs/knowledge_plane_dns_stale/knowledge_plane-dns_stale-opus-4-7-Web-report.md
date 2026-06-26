# Web Node Experiment Report

## 1. Actions Taken

1. **Inspected loopback address**: `ip addr show lo` — found 198.82.0.1/32 assigned (in addition to 127.0.0.1).
2. **Inspected routing table**: `ip route show` — found a pre-installed default route via 10.0.4.1 (ACM) on Web-eth0, with src 198.82.0.1, plus the connected /30 link.
3. **Verified neighbor reachability**: `ping -c 2 -I 198.82.0.1 10.0.4.1` — 0% loss, ~4 ms RTT, confirming the point-to-point link to ACM works and that ACM can reply to my loopback source.
4. **Notified ACM** via send_message: declared my service address 198.82.0.1/32, requested upstream advertisement, and confirmed my default route points at them.
5. **Verified local services**: `ss -tlnp` — confirmed HTTP (port 80) and HTTPS (port 443) python3 listeners bound to 198.82.0.1, plus dnsmasq on port 53.
6. **Reported done**: no additional routes were installed; the pre-existing default route was sufficient.

## 2. Justification

- I started with a local audit (loopback, routes, neighbor ping) before contacting anyone, per the "investigate locally first" guidance. This is cheap and avoids escalating unconfirmed state to peers.
- I did not add any new `ip route` entries because the default route via ACM already covers all non-local destinations, and ACM is my only neighbor — there is no alternative next-hop to choose. Adding routes would have been redundant.
- I sourced the ping from 198.82.0.1, not 10.0.4.2, to test the exact source address my services will use, since link addresses aren't generally routable end-to-end.
- I told ACM to advertise on my behalf rather than trying to do it myself: I have no other neighbors and no BGP relationship to AS2; ACM is the legitimate origin point for the 198.82.0.0/24 prefix.
- I made no firewall or ACL changes — none were needed, and any such change would have required admin approval per policy.

## 3. Network Discoveries

- I am a single-homed host inside ACM's network. My only physical neighbor is ACM via Web-eth0 (10.0.4.0/30, me .2, ACM .1).
- My stable, globally significant address is 198.82.0.1/32 — the address bound to the acm.org HTTP/HTTPS server.
- ACM advertises the covering prefix 198.82.0.0/24 to AS2, which propagates it to the wider Internet. External clients reach me via: client → AS2 → ACM → Web.
- ACM has a specific /32 route to 198.82.0.1 via 10.0.4.2 installed internally (confirmed by ACM and by successful ping from ACM's loopback per their reply).
- Listening services on my loopback: HTTP/80, HTTPS/443 (python3), and DNS/53 (dnsmasq, also bound to 127.0.0.1).

## 4. Coordination with Other Agents

- **ACM** (only neighbor): I sent one informational message announcing my loopback prefix and requesting upstream advertisement.
- **ACM's reply**: confirmed (a) they installed/verified a route to 198.82.0.1/32 via 10.0.4.2, (b) they are advertising 198.82.0.0/24 to AS2 for external propagation, and (c) that my default route via 10.0.4.1 should remain as-is.
- No relay requests were issued or received; no other agents were contacted, since ACM is my only neighbor and external reachability is entirely their responsibility to advertise.

## Final State

Local config unchanged from boot (default route via ACM was already correct). End-to-end reachability path established and confirmed at the control-plane level with ACM. HTTP/HTTPS services confirmed listening on the advertised address.