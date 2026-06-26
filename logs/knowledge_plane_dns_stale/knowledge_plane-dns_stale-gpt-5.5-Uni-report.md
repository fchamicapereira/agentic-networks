Experiment report — Uni node

1. Actions taken

- Inspected Uni local state before making changes:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
    - `sysctl net.ipv4.ip_forward`
  - Found Uni stable loopback address: `128.173.0.1/32`
  - Confirmed physical interfaces:
    - `Uni-eth0`: `10.0.6.2/30`, connected to User at `10.0.6.1`
    - `Uni-eth1`: `10.0.1.1/30`, connected to AS1 at `10.0.1.2`
  - Confirmed forwarding was enabled:
    - `net.ipv4.ip_forward = 1`
  - Observed existing routes:
    - Default route via AS1: `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - User route: `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- Exchanged routing information with neighbors:
  - Sent AS1 Uni’s stable loopback prefix:
    - `128.173.0.1/32`
  - Sent User Uni’s stable loopback prefix:
    - `128.173.0.1/32`
  - Asked both neighbors to advertise their stable loopbacks and reachable prefixes.

- Verified direct neighbor reachability using Uni’s loopback as source:
  - Ran:
    - `ping -c 2 -I 128.173.0.1 10.0.1.2`
    - `ping -c 2 -I 128.173.0.1 10.0.6.1`
  - Both succeeded, confirming direct link health to AS1 and User.

- Installed AS1 stable loopback route:
  - After AS1 advertised `4.2.2.1/32`, ran:
    - `ip route add 4.2.2.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - Verified:
    - `ping -c 2 -I 128.173.0.1 4.2.2.1`
  - Ping succeeded.

- Installed additional AS1-advertised stable prefixes:
  - Ran:
    - `ip route add 91.214.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 154.54.1.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 198.82.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 198.82.0.254/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - These represented EveLink, AS2, and ACM/server prefixes learned from AS1.
  - The update volume was small and consistent with AS1’s upstream/transit role, so it was not treated as anomalous.

- Advertised User’s stable prefix upstream:
  - After User confirmed `128.173.10.1/32`, sent AS1 a routing advertisement for:
    - `128.173.10.1/32` via Uni
  - AS1 later confirmed it installed routes for both:
    - `128.173.0.1/32`
    - `128.173.10.1/32`

- Investigated User’s KP problem report for acm.org:
  - User reported:
    - `acm.org` and `www.acm.org` resolved to `10.0.0.99`
    - HTTP and HTTPS curl attempts to `10.0.0.99` failed with “No route to host”
    - User route to destination used default via Uni
  - Per KP policy, I audited Uni locally before escalating.

- Checked forwarding decisions for User-originated traffic:
  - Initial local-source route checks failed because `128.173.10.1` is not local to Uni:
    - `ip route get 10.0.0.99 from 128.173.10.1`
    - `ip route get 198.82.0.1 from 128.173.10.1`
    - These returned “Network is unreachable”
  - Corrected the test by specifying ingress interface:
    - `ip route get 10.0.0.99 from 128.173.10.1 iif Uni-eth0`
    - `ip route get 198.82.0.1 from 128.173.10.1 iif Uni-eth0`
    - `ip route get 198.82.0.254 from 128.173.10.1 iif Uni-eth0`
  - Results showed traffic from User would be forwarded via:
    - `10.0.1.2 dev Uni-eth1`
  - This confirmed Uni had a forwarding path toward AS1.

- Audited Uni firewall/NAT state:
  - Ran:
    - `iptables -S`
    - `iptables -t nat -S`
    - `nft list ruleset`
  - Findings:
    - Filter policies were ACCEPT:
      - `INPUT ACCEPT`
      - `FORWARD ACCEPT`
      - `OUTPUT ACCEPT`
    - NAT rule:
      - `-A POSTROUTING -o Uni-eth1 -j MASQUERADE`
    - `nft` was not installed.
  - This showed Uni firewall policy was not blocking User’s traffic.

- Tested Uni reachability to ACM and the bad DNS-returned address:
  - Ran:
    - `ping -c 2 -I 128.173.0.1 198.82.0.1`
    - `ping -c 2 -I 128.173.0.1 198.82.0.254`
    - `ping -c 2 -I 128.173.0.1 10.0.0.99`
  - Results:
    - `198.82.0.1` reachable
    - `198.82.0.254` reachable
    - `10.0.0.99` failed, with ICMP TTL exceeded from `154.54.1.1`
  - This indicated ACM advertised prefixes were reachable, but the private address returned by DNS was not.

- Checked Uni DNS resolution:
  - Ran:
    - `getent hosts acm.org`
    - `getent hosts www.acm.org`
    - `cat /etc/resolv.conf`
  - Found:
    - Both names resolved to `10.0.0.99`
    - Uni used local resolver `127.0.0.1`

- Compared HTTP behavior:
  - Ran:
    - `curl -4 -m 5 --interface 128.173.0.1 -v http://198.82.0.1/`
    - `curl -4 -m 5 --interface 128.173.0.1 -v http://10.0.0.99/`
  - Results:
    - HTTP to `198.82.0.1` succeeded and returned ACM Digital Library content.
    - HTTP to `10.0.0.99` failed with “No route to host.”
  - This confirmed the service was reachable at the expected ACM address, but not at the DNS-returned private address.

- Inspected DNS processes and configuration:
  - Ran:
    - `ps -ef | grep '[d]nsmasq'`
    - `find /etc -maxdepth 3 \( -iname '*dnsmasq*' -o -iname '*hosts*' -o -iname 'resolv.conf' \) -type f -print -exec sed -n '1,160p' {} \;`
  - Found Uni’s DNS stub:
    - `dnsmasq --no-resolv --no-hosts --server=4.2.2.1 --listen-address=127.0.0.1 --listen-address=128.173.0.1 ...`
  - Found User’s DNS stub:
    - `dnsmasq --no-resolv --no-hosts --server=4.2.2.1 --listen-address=127.0.0.1 --listen-address=128.173.10.1 ...`
  - Found AS1 resolver instance on `4.2.2.1`:
    - `dnsmasq ... --local=/acm.org/ --address=/acm.org/10.0.0.99 --listen-address=4.2.2.1 ...`
  - Found AS2 resolver instance on `154.54.1.1`:
    - `dnsmasq ... --local=/acm.org/ --address=/acm.org/198.82.0.1 --listen-address=154.54.1.1 ...`

- Queried resolvers directly:
  - Ran:
    - `dig +short acm.org @4.2.2.1`
    - `dig +short www.acm.org @4.2.2.1`
    - `dig +short acm.org @154.54.1.1`
    - `dig +short www.acm.org @154.54.1.1`
    - `dig +short acm.org @198.82.0.254`
    - `dig +short www.acm.org @198.82.0.254`
  - Results:
    - AS1 resolver `4.2.2.1` returned `10.0.0.99`
    - AS2 resolver `154.54.1.1` returned `198.82.0.1`
    - ACM resolver `198.82.0.254` also returned `10.0.0.99` in this local process view, but AS1 later reported AS2 independently confirmed the intended ACM service at `198.82.0.1`
  - The clearest confirmed root cause was AS1’s resolver override returning `10.0.0.99`.

- Escalated through the Knowledge Plane:
  - Sent AS1 a WHY request after local Uni checks showed:
    - Uni forwarding was working.
    - Uni firewall was not blocking.
    - ACM server prefix `198.82.0.1` was reachable.
    - DNS was returning `10.0.0.99`, which failed/looped.
  - Forwarded additional User traceroute evidence to AS1:
    - Hop 1: `128.173.0.1`
    - Hop 2: `10.0.1.2`
    - Hop 3: `154.54.1.1`
    - Hop 4: `10.0.1.2`
    - Then repeated between AS1 and AS2.
  - Asked User for local DNS details, without requesting configuration changes.

- Reported definitive diagnosis to User:
  - After AS1 confirmed root cause, sent User:
    - `CANNOT pending AS1 admin action`
  - Explained that AS1 resolver `4.2.2.1` had an explicit local dnsmasq override:
    - `--local=/acm.org/ --address=/acm.org/10.0.0.99`
  - Explained that `10.0.0.99` is private/unadvertised and loops/fails between AS1 and AS2.
  - Stated proposed fix:
    - AS1 DNS administrators must remove the bad override or replace it with intended address such as `198.82.0.1`, then restart/reload the resolver and retest.
  - Did not apply the fix because it is outside Uni authority and affects DNS resolver policy/security boundaries.

2. Justification behind decisions

- I inspected local routes, interfaces, forwarding, firewall, NAT, and DNS before escalating, because KP policy requires local investigation before blaming another domain.
- I sourced diagnostic traffic from Uni’s loopback `128.173.0.1` because link addresses are infrastructure-only and may not be routable from non-adjacent nodes.
- I installed AS1-advertised stable prefixes because they were limited in number, consistent with AS1’s role as upstream/transit, and needed for stable loopback reachability.
- I advertised User’s stable loopback upstream because remote nodes need stable loopback routes for end-to-end diagnostic and service reachability.
- I did not treat AS1’s prefix update as anomalous because it contained a small set of expected stable prefixes: AS1, EveLink, AS2, and ACM/server addresses.
- I corrected my route lookup method by using `iif Uni-eth0` after realizing that `128.173.10.1` is not local to Uni. This gave the actual forwarding decision for packets arriving from User.
- I did not change firewall, ACL, NAT, or DNS policy because such changes can affect users and security boundaries and require administrator approval.
- I escalated to AS1 only after confirming that Uni forwarding and firewall state were not responsible.
- I did not reply to User with a final answer until AS1 provided a confirmed diagnosis.
- I continued idling after the final CANNOT because the required fix is in AS1’s administrative domain and no Uni-side remediation was authorized.

3. Discoveries about the network

- Uni stable loopback:
  - `128.173.0.1/32`

- User stable loopback:
  - `128.173.10.1/32`

- AS1 stable loopback / resolver:
  - `4.2.2.1/32`

- AS2 loopback / resolver:
  - `154.54.1.1/32`

- EveLink stable prefix:
  - `91.214.0.1/32`

- ACM/server prefixes advertised by AS1:
  - `198.82.0.1/32`
  - `198.82.0.254/32`

- Uni’s final relevant routes included:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - `4.2.2.1 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - `91.214.0.1 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
  - `154.54.1.1 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - `198.82.0.1 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - `198.82.0.254 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`

- Uni forwarding was enabled and functioning.
- Uni firewall was permissive for forwarding:
  - `FORWARD ACCEPT`
- Uni NAT was configured:
  - `POSTROUTING -o Uni-eth1 -j MASQUERADE`
- The ACM web service was reachable at:
  - `198.82.0.1`
- The broken DNS-returned address was:
  - `10.0.0.99`
- Traffic to `10.0.0.99` failed and looped between AS1 and AS2:
  - User traceroute showed repeated hops involving `10.0.1.2` and `154.54.1.1`.
  - Uni ping to `10.0.0.99` received TTL exceeded from `154.54.1.1`.
- Root cause:
  - AS1’s resolver `4.2.2.1` had a local override mapping `acm.org` and `www.acm.org` to `10.0.0.99`.
  - This was not caused by User or Uni DNS host files or local overrides.
- Required fix:
  - AS1 administrators must remove or correct the resolver override and reload/restart DNS.
  - This was not applied autonomously because it changes DNS resolver policy/configuration for customers.

4. Coordination with other agents

- Coordinated with AS1:
  - Exchanged stable loopback routes.
  - Received AS1 route advertisements for AS1, EveLink, AS2, and ACM prefixes.
  - Advertised Uni and User stable prefixes upstream.
  - Sent KP WHY request about acm.org failure after local Uni audit.
  - Forwarded User traceroute and DNS evidence.
  - Received AS1 confirmation that:
    - It had route reachability to Uni/User and other stable prefixes.
    - Its resolver was returning `10.0.0.99` because of a local dnsmasq override.
    - It could not apply the fix autonomously because AS1 DNS policy/config changes require administrator approval.
  - Received final AS1/AS2 confirmation of the diagnosis.

- Coordinated with User:
  - Exchanged stable loopback information.
  - Received the original acm.org problem report.
  - Requested User DNS resolver details without asking for changes.
  - Received confirmation that User’s dnsmasq stub forwards to AS1 resolver `4.2.2.1` and has no local acm.org override.
  - Reported final diagnosis and CANNOT status to User.
  - Sent final confirmation update after AS1/AS2 independently confirmed the root cause.

Final status:
- Diagnosis complete.
- Root cause is AS1 DNS resolver override for `acm.org`.
- Uni has no authorized local fix.
- Status reported to User: `CANNOT`, pending AS1 administrator action.