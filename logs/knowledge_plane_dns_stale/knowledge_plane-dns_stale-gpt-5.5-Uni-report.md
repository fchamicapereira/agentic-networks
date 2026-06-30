Experiment report for Uni

1. Actions taken

- Inspected Uni’s local network state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Found Uni’s stable loopback address: `128.173.0.1/32`.
  - Confirmed physical links:
    - `Uni-eth0`: `10.0.6.2/30` to User at `10.0.6.1`
    - `Uni-eth1`: `10.0.1.1/30` to AS1 at `10.0.1.2`
  - Confirmed an existing default route:
    - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - Confirmed an existing route to User’s stable loopback:
    - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- Exchanged routing information with directly connected neighbors:
  - Asked AS1 and User to advertise their stable loopback prefixes and reachable stable prefixes.
  - Advertised to AS1:
    - Uni stable prefix: `128.173.0.1/32`
    - Customer/User stable prefix: `128.173.10.1/32`
    - Next hop toward Uni from AS1: `10.0.1.1`
  - Advertised to User:
    - Uni stable prefix: `128.173.0.1/32`
    - Default/Internet reachability via Uni at `10.0.6.2`
  - Did not advertise infrastructure `/30` link prefixes network-wide.

- Installed verified route advertisements from AS1:
  - AS1 advertised:
    - `4.2.2.1/32`, AS1 loopback
    - `91.214.0.1/32`, reachable via EveLink
    - `154.54.1.1/32`, AS2 loopback
    - `198.82.0.1/32`, ACM web/service address
  - Configured routes:
    - `ip route add 4.2.2.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 91.214.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 154.54.1.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 198.82.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - These were small, specific, expected advertisements from the upstream, so they were safe to install.

- Investigated the reported `acm.org` outage locally before escalating:
  - Checked the route toward `198.82.0.99`:
    - `ip route get 198.82.0.99 from 128.173.0.1`
    - Result: traffic used AS1 via `10.0.1.2` on `Uni-eth1`.
  - Checked forwarding:
    - `sysctl net.ipv4.ip_forward`
    - Result: `net.ipv4.ip_forward = 1`
  - Audited firewall/NAT:
    - `iptables -S`
    - `iptables -t nat -S`
    - `nft list ruleset`
  - Found:
    - Filter policies were `ACCEPT`.
    - NAT had:
      - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`
    - `nft` was not installed.
  - Tested reachability from Uni’s stable loopback:
    - `ping -c 3 -I 128.173.0.1 198.82.0.99`
    - Result: ICMP Destination Host Unreachable from `198.82.0.254`.

- Escalated the `acm.org` failure to AS1 through the Knowledge Plane:
  - Sent AS1 the User’s observations:
    - User source: `128.173.10.1`
    - DNS result: `acm.org = 198.82.0.99`
    - Ping and curl failed with Host Unreachable from `198.82.0.254`
  - Included Uni’s local audit:
    - route to `198.82.0.99` goes via AS1
    - forwarding enabled
    - firewall not blocking
    - Uni’s own ping from `128.173.0.1` reproduced Host Unreachable from `198.82.0.254`

- Investigated broader scope symptoms:
  - User reported:
    - `198.82.0.254` reachable
    - `198.82.0.99` unreachable
    - `8.8.8.8` produced TTL exceeded from AS1
    - `example.com` DNS failed
  - Locally tested:
    - `ip route get 8.8.8.8 from 128.173.0.1`
    - `ping -c 3 -I 128.173.0.1 8.8.8.8`
    - `ping -c 3 -I 128.173.0.1 198.82.0.254`
    - `getent ahostsv4 example.com`
    - `cat /etc/resolv.conf`
    - `ss -lunpt | grep ':53'`
  - Found:
    - `8.8.8.8` used default route through AS1.
    - Ping to `8.8.8.8` produced redirect/loop evidence involving `4.2.2.1` and `154.54.1.1`.
    - `198.82.0.254` was reachable.
    - Local resolver listened on `127.0.0.1:53` and `128.173.0.1:53`.
    - `/etc/resolv.conf` used `nameserver 127.0.0.1`.

- Audited DNS forwarding on Uni:
  - Ran:
    - `ps -ef | grep '[d]nsmasq'`
    - `find /etc -maxdepth 3 \( -name '*dnsmasq*' -o -path '/etc/dnsmasq.d/*' \) -print`
    - inspected `/etc/dnsmasq.conf` and `/etc/dnsmasq.d/*`
    - `nslookup example.com 127.0.0.1`
    - `nslookup acm.org 127.0.0.1`
    - `traceroute -n -s 128.173.0.1 8.8.8.8`
  - Found Uni’s DNS forwarder was forwarding to AS1 resolver `4.2.2.1`.
  - Uni’s resolver returned:
    - `acm.org = 198.82.0.99`
  - `example.com` was refused.
  - Traceroute to `8.8.8.8` showed looping behavior between AS1 and AS2-related addresses.

- Verified AS1/ACM final findings from Uni:
  - Ran:
    - `nslookup acm.org 127.0.0.1`
    - `nslookup acm.org 4.2.2.1`
    - `curl -4 -I --interface 128.173.0.1 --max-time 5 http://198.82.0.1/`
    - `curl -4 -I --interface 128.173.0.1 --max-time 5 http://198.82.0.99/`
    - `ping -c 2 -I 128.173.0.1 198.82.0.99`
  - Confirmed:
    - Uni and AS1 resolver still returned `acm.org = 198.82.0.99`.
    - HTTP to intended target `198.82.0.1` reached a web server.
    - HTTP and ping to stale target `198.82.0.99` failed with Host Unreachable from `198.82.0.254`.

- Reported final result to User:
  - Diagnosis: CANNOT pending AS1 administrator action.
  - Explained that no User-side fix was needed.
  - Explained the required fix was AS1 DNS correction for `acm.org` from `198.82.0.99` to `198.82.0.1`.

2. Justification behind decisions

- I inspected local state first because Uni is the campus gateway, and the KP instructions require local investigation before escalating.
- I used loopback source addresses for diagnostic traffic because remote nodes only route back to stable loopbacks; link-local infrastructure addresses are not valid evidence for end-to-end reachability.
- I advertised only stable loopback/customer prefixes and did not advertise `/30` infrastructure links, because link prefixes are scoped to directly connected neighbors.
- I installed only small, specific, expected route advertisements from AS1. There was no anomalously large prefix set, so no route-advertisement anomaly response was needed.
- I did not change firewall, NAT, DNS, or AS1 routing policy because those affect security boundaries or other customers and require administrator approval.
- I escalated to AS1 only after confirming:
  - Uni had a route toward the destination.
  - IP forwarding was enabled.
  - Uni firewall policy was not blocking the traffic.
  - Uni itself reproduced the same failure.
- I did not reply to User with an interim hypothesis while the KP investigation was pending. I waited until AS1 provided a definitive CANNOT status.
- When User reported the symptom changed from Host Unreachable to timeout, I re-verified from Uni and informed User that the root cause remained the stale DNS target, since AS1 DNS still returned `198.82.0.99` and that address remained unreachable.

3. Discoveries about the network

- Uni’s stable address is `128.173.0.1/32`.
- User’s stable address is `128.173.10.1/32`.
- AS1’s stable resolver/loopback is `4.2.2.1/32`.
- AS2’s stable address is `154.54.1.1/32`.
- ACM has reachable addresses:
  - `198.82.0.254`, ACM gateway/loopback
  - `198.82.0.1`, intended working web target for `acm.org`
- The broken DNS target was:
  - `198.82.0.99`
- Uni forwarding and packet filtering were not the cause of the `acm.org` outage:
  - `ip_forward` was enabled.
  - Filter policies were ACCEPT.
  - Route to `198.82.0.99` went correctly toward AS1.
- The primary `acm.org` outage was caused by stale or incorrect AS1 DNS resolver data:
  - AS1 resolver `4.2.2.1` was configured to answer `acm.org A 198.82.0.99`.
  - ACM confirmed the intended target was `198.82.0.1`.
  - `198.82.0.1` was reachable and served HTTP.
  - `198.82.0.99` was not routed/served.
- The ICMP Host Unreachable from `198.82.0.254` was expected because ACM’s gateway could not reach or route the stale target `198.82.0.99`.
- There was a separate default/Internet routing issue:
  - User and Uni tests to `8.8.8.8` showed looping/redirect behavior involving AS1 and AS2.
  - AS2 confirmed it had an erroneous default route back to AS1 and removed it.
  - AS1 also needed to remove or replace its default route via AS2, but that required AS1 administrator approval.
- DNS for general names such as `example.com` was also affected, likely due to the broader DNS/default-routing situation. This was separate from the `acm.org` stale-target problem.

4. Coordination with other agents

- Coordinated with User:
  - Received User’s stable prefix advertisement `128.173.10.1/32`.
  - Received the original report that `acm.org` would not load.
  - Received User’s test results for:
    - DNS resolution
    - ping to `198.82.0.99`
    - HTTP/HTTPS curl to `acm.org`
    - reachability to `198.82.0.254`
    - off-campus tests to `8.8.8.8` and `example.com`
    - direct HTTP to `198.82.0.99`
    - TTL-limited probes
  - Reported the final CANNOT diagnosis and later sent extra verification from Uni.

- Coordinated with AS1:
  - Exchanged routing advertisements.
  - Sent AS1 Uni’s and User’s diagnostic observations.
  - Asked AS1 to investigate upstream/AS2/ACM reachability.
  - Forwarded additional scope-test evidence from User.
  - Provided Uni DNS audit results showing Uni was merely forwarding to AS1 resolver `4.2.2.1`.
  - Received AS1’s findings:
    - AS1 reproduced the failure to `198.82.0.99`.
    - AS1 could reach `198.82.0.254` and `198.82.0.1`.
    - AS1 resolver was locally/authoritatively configured for stale `acm.org = 198.82.0.99`.
    - AS1 could not change DNS service without administrator approval.
    - AS1 identified the separate AS1-AS2 default-routing issue.

- AS1 coordinated further with AS2 and ACM:
  - AS2 confirmed the same failure to `198.82.0.99`.
  - AS2 resolver answered `acm.org = 198.82.0.1`.
  - ACM confirmed `198.82.0.1` was the intended working target and `198.82.0.99` was not routed/served.
  - AS2 confirmed and removed an erroneous default route back to AS1.
  - AS1 administrators were notified for the remaining DNS and default-routing changes.