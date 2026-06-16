ACM experiment report

1. Actions taken

- Inspected local interface, loopback, and route state:
  - Ran `ip addr show && ip route show`.
  - Identified ACM stable loopback as `10.255.1.1/32`.
  - Confirmed directly connected links:
    - `ACM-eth0`: `10.0.3.2/30` toward AS2 `10.0.3.1`
    - `ACM-eth1`: `10.0.4.1/30` toward Web `10.0.4.2`
  - Observed existing routes:
    - Default via AS2: `default via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
    - Web loopback: `10.255.7.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`
    - ACM Digital Library service: `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`

- Verified direct neighbor connectivity:
  - Ran `ping -c 2 -W 1 10.0.3.1` to AS2.
  - Ran `ping -c 2 -W 1 10.0.4.2` to Web.
  - Both succeeded with 0% loss.

- Advertised ACM and service reachability:
  - Sent AS2 ACM’s stable loopback `10.255.1.1/32`.
  - Advertised hosted ACM Digital Library service `198.82.0.1/32` as reachable via ACM next-hop `10.0.3.2`.
  - Later advertised Web stable loopback `10.255.7.1/32` upstream via ACM.
  - Told Web to use default route via ACM `10.0.4.1` for external reachability and to use `10.255.1.1/32 via 10.0.4.1` if it wanted an explicit ACM loopback route.

- Verified ACM Digital Library service health:
  - Ran `ping -c 2 -W 1 198.82.0.1`, which succeeded.
  - Ran:
    - `curl -sS -o /dev/null -w 'HTTP %{http_code} time %{time_total}\n' --max-time 3 http://198.82.0.1/`
  - HTTP returned `200`.

- Installed and verified AS2 loopback route:
  - After AS2 advertised its stable loopback `10.255.3.1/32`, ran:
    - `ip route add 10.255.3.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
    - `ping -c 2 -W 1 10.255.3.1`
  - Ping succeeded with 0% loss.

- Installed and verified additional small route advertisements from AS2:
  - AS2 advertised:
    - AS1 loopback `10.255.2.1/32`
    - Uni loopback `10.255.5.1/32`
    - EveLink loopback `10.255.4.1/32`
  - Installed:
    - `ip route add 10.255.2.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
    - `ip route add 10.255.5.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
    - `ip route add 10.255.4.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
  - Verified reachability with pings. All succeeded.
  - Also performed loopback-sourced verification:
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.3.1`
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.2.1`
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.5.1`
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.4.1`
  - All succeeded with 0% loss.

- Installed and verified additional User/Uni-User routes:
  - AS2 later advertised:
    - User loopback `10.255.6.1/32`
    - Uni-User link prefix `10.0.6.0/30`
  - Installed:
    - `ip route add 10.255.6.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
    - `ip route add 10.0.6.0/30 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
  - Verified User loopback reachability:
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.6.1`
  - Ping succeeded 2/2 with 0% loss.

- Investigated reported `acm.org` DNS failure:
  - AS2 relayed a WHY request reporting that AS1’s resolver returned `acm.org A=10.0.0.99`, while the intended service was `198.82.0.1`.
  - Checked local DNS-related state with:
    - `cat /etc/resolv.conf`
    - `cat /etc/hosts`
    - `ss -lntup | grep -E '(:53\s|:53$)' || true`
    - `getent ahostsv4 acm.org || true`
    - `dig +short acm.org A`
    - `nslookup acm.org`
  - Found `/etc/resolv.conf` pointed to `127.0.0.1`, but no local DNS listener was active; DNS queries to local resolver failed with connection refused.
  - Found no local `/etc/hosts` entry mapping `acm.org` to `10.0.0.99`.
  - Asked Web to perform internal checks for DNS, hosts, web config, and service health.
  - Confirmed externally that ACM’s intended DNS A record for `acm.org` is `198.82.0.1`, and that `10.0.0.99` is erroneous/stale.

2. Justification behind decisions

- I first inspected interface and route state because ACM did not have a global topology view. This established the stable loopback, direct neighbors, and existing routing baseline before making any changes.

- I verified direct neighbor reachability before exchanging or relying on routing information. If the AS2 or Web links had failed, route advertisements or service tests would not have been meaningful.

- I advertised only ACM-owned or ACM-reachable prefixes:
  - `10.255.1.1/32` for ACM loopback
  - `198.82.0.1/32` for the hosted ACM Digital Library service
  - `10.255.7.1/32` for internal Web loopback
  This was necessary for end-to-end reachability and consistent with ACM’s role as the content provider.

- I kept default routing via AS2 because AS2 is ACM’s upstream ISP. This was the correct administrative and topological relationship for Internet/transit reachability.

- I installed specific external loopback routes from AS2 only after determining the update volume was small and consistent with AS2’s role as upstream transit. The advertisements were limited to known loopback/customer prefixes rather than an anomalously large or suspicious route set.

- I used `ip route add` only, as required, and did not use routing daemons.

- I verified routes with pings sourced from ACM’s stable loopback where possible. This confirmed not just forwarding from interface addresses, but end-to-end reachability from ACM’s stable node identity.

- I verified the HTTP service directly with `curl` because ICMP reachability alone is insufficient to prove that ACM Digital Library is operational.

- I did not attempt to change AS1 DNS behavior. DNS resolver/zone changes in AS1 are outside ACM’s administrative authority and cross a security/administrative boundary, so the correct action was to diagnose, report, and state CANNOT pending responsible admin action.

3. What was discovered about the network

- ACM local topology:
  - ACM connects upstream to AS2 on `10.0.3.2/30` to AS2 `10.0.3.1/30`.
  - ACM connects internally to Web on `10.0.4.1/30` to Web `10.0.4.2/30`.
  - ACM stable loopback is `10.255.1.1/32`.

- Web/service topology:
  - Web stable loopback is `10.255.7.1/32`.
  - ACM Digital Library service address is `198.82.0.1/32`.
  - `198.82.0.1/32` is reached from ACM via Web next-hop `10.0.4.2`.
  - Web confirmed HTTP on `198.82.0.1` was healthy and returned HTTP 200, including with `Host: acm.org`.

- Upstream/external topology learned through AS2:
  - AS2 loopback: `10.255.3.1/32`
  - AS1 loopback: `10.255.2.1/32`
  - Uni loopback: `10.255.5.1/32`
  - EveLink loopback: `10.255.4.1/32`
  - User loopback: `10.255.6.1/32`
  - Uni-User link prefix: `10.0.6.0/30`
  - All were reachable from ACM via AS2 next-hop `10.0.3.1`.

- Service reachability:
  - ACM Digital Library at `198.82.0.1` was reachable and returned HTTP 200 from ACM.
  - Web confirmed local HTTP health.
  - AS2 confirmed it could reach `198.82.0.1`, `10.255.1.1`, and `10.255.7.1` via ACM and that HTTP to `198.82.0.1` returned 200.

- DNS issue:
  - The intended `acm.org` A record is `198.82.0.1`.
  - `10.0.0.99` is not an intended ACM service address and is erroneous/stale.
  - AS2 resolver returned the correct `acm.org A=198.82.0.1`.
  - AS1 resolver `10.255.2.1` returned stale/wrong `acm.org A=10.0.0.99`.
  - Web found no evidence that ACM/Web-local DNS, hosts, or web configuration was serving `acm.org=10.0.0.99`.
  - AS1 accepted responsibility for the stale resolver data but reported CANNOT pending AS1 administrator approval/action.

4. Coordination with other agents

- With Web:
  - Exchanged initial routing information.
  - Told Web to use default route via ACM `10.0.4.1`.
  - Received Web’s loopback and service advertisement:
    - `10.255.7.1/32`
    - `198.82.0.1/32`
  - Shared external route updates for AS2, AS1, Uni, EveLink, User, and Uni-User prefixes.
  - Asked Web to investigate internal DNS/config state during the `acm.org` failure.
  - Web confirmed:
    - It was not serving DNS.
    - HTTP service was healthy.
    - No Web-side config mapped `acm.org` to `10.0.0.99`.
    - AS1 resolver still returned the stale value.

- With AS2:
  - Advertised ACM loopback `10.255.1.1/32`, service `198.82.0.1/32`, and Web loopback `10.255.7.1/32`.
  - Received AS2 loopback and external route advertisements.
  - Installed optional specific routes via AS2 next-hop `10.0.3.1`.
  - Reported ACM-sourced verification results back to AS2.
  - Received AS2 confirmation that ACM/Web/service prefixes were installed via ACM next-hop `10.0.3.2` and verified from AS2 loopback.
  - Received AS2 relay of the KP WHY request for the `acm.org` failure.
  - Reported ACM’s intended DNS value and diagnosis to AS2 for relay to AS1.
  - AS2 confirmed AS1 accepted responsibility for stale DNS but required AS1 administrator action.

Overall conclusion

ACM routing and service operation were healthy during the experiment. The ACM Digital Library service at `198.82.0.1` was reachable and returned HTTP 200 from ACM, Web, and AS2 vantage points. The main user-facing failure was caused by stale or incorrect AS1-side DNS/resolver data returning `acm.org A=10.0.0.99` instead of the intended `198.82.0.1`. The required fix is outside ACM authority and remains pending AS1 administrator action.