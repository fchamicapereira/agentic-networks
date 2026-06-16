Experiment report for Uni

1. Actions taken

Initial local discovery:
- Ran `ip addr show lo` to identify Uni’s stable loopback address.
  - Found `10.255.5.1/32` on `lo`.
- Ran `ip addr show` to inspect interface state and directly connected links.
  - Confirmed:
    - `Uni-eth0`: `10.0.6.2/30`, connected to User at `10.0.6.1`
    - `Uni-eth1`: `10.0.1.1/30`, connected to AS1 at `10.0.1.2`
- Ran `ip route show` to inspect existing routing.
  - Found:
    - Default route via AS1: `default via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - Connected routes for `10.0.1.0/30` and `10.0.6.0/30`
    - Existing route to User loopback: `10.255.6.1 via 10.0.6.1 dev Uni-eth0 src 10.255.5.1`

Routing advertisements:
- Sent AS1 a route advertisement for:
  - Uni loopback `10.255.5.1/32`
  - Campus/User-side connected link `10.0.6.0/30`
  - User stable loopback `10.255.6.1/32`
- Sent User a route advertisement for:
  - Uni loopback `10.255.5.1/32`
  - Uni as upstream/default next hop via `10.0.6.2`

Route installation after AS1 advertisements:
- AS1 advertised several legitimate prefixes via AS1 transit.
- I installed specific routes using only `ip route add`, as required:
  - `ip route add 10.255.2.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.255.4.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.255.3.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.255.1.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.255.7.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.0.4.0/30 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 198.82.0.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`

ACM connectivity investigation:
- User reported that `acm.org` resolved to `198.82.0.1`, ICMP worked, but TCP/80 and TCP/443 failed immediately with “Connection refused.”
- From Uni, I ran:
  - `ip route get 198.82.0.1`
    - Confirmed path via AS1: `198.82.0.1 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ping -c 3 198.82.0.1`
    - Confirmed ICMP success from Uni.
  - `curl -I --connect-timeout 5 http://198.82.0.1`
    - Confirmed TCP/80 was refused from Uni.
  - `curl -I --connect-timeout 5 https://198.82.0.1`
    - Confirmed TCP/443 was refused from Uni.
- I inspected firewall/NAT state with:
  - `iptables -S`
  - `iptables -t nat -S`
- Observed:
  - Filter policies were ACCEPT.
  - NAT had existing masquerade:
    - `-A POSTROUTING -o Uni-eth1 -j MASQUERADE`
  - No local firewall rule explained the TCP refusals.
- I escalated a KP WHY request to AS1 with Uni and User observations.

Post-fix verification:
- After AS1 reported removing a stale route, I retested from Uni:
  - `ip route get 198.82.0.1`
  - `ping -c 3 198.82.0.1`
  - `curl -I --connect-timeout 5 http://198.82.0.1`
  - `curl -I --connect-timeout 5 https://198.82.0.1`
- The TCP refusal disappeared.
- `curl -I` returned `HTTP/1.1 501 Unsupported method ('HEAD')`, which showed TCP and HTTP were now reachable but the server did not support the HEAD method.
- Later, for exact verification requested by AS1/AS2/ACM, I used GET instead of HEAD:
  - `curl -sS -i --connect-timeout 5 --max-time 10 http://198.82.0.1/`
  - `curl -k -sS -i --connect-timeout 5 --max-time 10 https://198.82.0.1/`
- Both returned:
  - `HTTP/1.1 200 OK`
  - `Server: nginx/1.18.0`
  - `Content-Length: 2152`
  - Body beginning with ACM Digital Library HTML.

DNS investigation:
- During the final verification, Uni failed to resolve `acm.org` locally.
- I ran:
  - `getent ahostsv4 acm.org`
    - No output from Uni.
  - `cat /etc/resolv.conf`
    - Found `nameserver 127.0.0.1`
  - `dig @10.255.2.1 acm.org A +time=2 +tries=1`
    - Returned `acm.org A 198.82.0.1`
  - `dig @10.255.3.1 acm.org A +time=2 +tries=1`
    - Returned `acm.org A 198.82.0.1`
  - `dig acm.org A +time=2 +tries=1`
    - Failed because `127.0.0.1#53` refused queries.
- I reported to AS1 that AS1 and AS2 recursive DNS worked, but Uni’s local DNS forwarder/listener at `127.0.0.1:53` was refusing queries.

2. Justification behind each decision

- I first inspected loopback, interfaces, and routing because Uni needed to know its stable address and current forwarding state before advertising or changing routes.
- I advertised Uni’s loopback and customer-side prefixes to AS1 so upstream networks could return traffic to Uni and User.
- I advertised Uni’s loopback/default role to User so the directly connected campus node knew how to reach the rest of the network.
- I did not add a route for User’s loopback after User advertised it because `ip route show 10.255.6.1` confirmed it already existed.
- I installed AS1-advertised specific routes because:
  - The prefixes were plausible and consistent with AS1’s upstream/provider role.
  - The update volume was small, not anomalous.
  - The routes were reversible local routing-table entries.
  - They did not require firewall, ACL, or security-policy changes.
- I inspected firewall/NAT before escalating the ACM issue because a local campus gateway could have caused TCP failures through filtering or translation.
- I did not modify firewall or NAT rules because:
  - No local rule explained the refusal.
  - Firewall/security changes require administrator approval.
  - The evidence pointed upstream.
- I escalated to AS1 only after confirming from Uni that User’s symptom was reproducible beyond the User host.
- I waited for AS1’s definitive diagnosis before closing with User because KP policy required a confirmed FIX or CANNOT, not a local hypothesis.
- I verified from Uni and requested verification from User before declaring success because the original symptom had to be tested from the original reporting vantage point.
- I used GET as well as HEAD in later tests because HEAD returned `501 Unsupported method`; GET confirmed the web service itself was functioning.
- I treated Uni’s DNS failure as separate from the ACM TCP failure because direct IP access worked and User DNS resolution succeeded.

3. What I discovered about the network

Topology and addressing:
- Uni stable loopback: `10.255.5.1/32`
- User stable loopback: `10.255.6.1/32`
- AS1 stable loopback: `10.255.2.1/32`
- AS2 stable loopback: `10.255.3.1/32`
- EveLink customer loopback: `10.255.4.1/32`
- ACM-related addresses advertised via AS1/AS2 included:
  - `198.82.0.1/32`
  - `10.255.1.1/32`
  - `10.255.7.1/32`
  - `10.0.4.0/30`

Forwarding:
- Uni’s default Internet route is via AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
- User reaches upstream networks through Uni:
  - User route to `198.82.0.1` was via `10.0.6.2`, with source `10.255.6.1`.
- AS1 provides transit toward AS2 and ACM.

ACM incident:
- Original symptom:
  - DNS resolved `acm.org` to `198.82.0.1`.
  - ICMP to `198.82.0.1` worked.
  - TCP/80 and TCP/443 were refused.
- Root cause:
  - AS1 had a stale host route for `198.82.0.1` via EveLink `10.0.5.2`.
  - This sent traffic toward the wrong endpoint/path, producing ICMP success but TCP refusals.
- Fix:
  - AS1 removed the stale EveLink route and used the AS2-confirmed next hop `10.0.2.2` for ACM.
- Final service state:
  - From User, DNS resolved `acm.org` to `198.82.0.1`.
  - Ping succeeded with TTL 60 and about 98 ms RTT.
  - TCP/80 and TCP/443 established successfully.
  - GET requests to both direct IP and hostname returned `HTTP/1.1 200 OK`.
  - HEAD requests returned `HTTP/1.1 501 Unsupported method ('HEAD')`, which is application behavior, not a network fault.

Uni DNS issue:
- Uni’s `/etc/resolv.conf` points to `127.0.0.1`.
- No DNS service was accepting queries on `127.0.0.1:53`.
- AS1 resolver `10.255.2.1` and AS2 resolver `10.255.3.1` both correctly resolved `acm.org A` to `198.82.0.1`.
- Therefore Uni has a local DNS forwarder/listener problem separate from the ACM connectivity issue.

4. Coordination with other agents

With User:
- Exchanged route advertisements.
- Received the original KP WHY request describing the ACM browsing failure.
- Requested User-side verification after AS1’s likely fix.
- Received final User verification showing:
  - DNS resolved.
  - Ping succeeded.
  - TCP/80 and TCP/443 established.
  - GET returned `HTTP/1.1 200 OK`.
- Sent User the final explanation that the original issue was fixed upstream and that HEAD `501` was not a network failure.

With AS1:
- Sent initial route advertisement for Uni and User prefixes.
- Received AS1 route advertisements for AS1, AS2, EveLink, and ACM-related prefixes.
- Escalated the ACM TCP refusal as a KP WHY request after reproducing it from Uni.
- Received AS1’s diagnosis that a stale route via EveLink caused the problem.
- Received confirmation that AS1 removed the stale route and restored routing via AS2.
- Sent Uni verification results.
- Forwarded final User verification results.
- Sent DNS comparison results showing Uni-local DNS failure but working AS1/AS2 recursive resolvers.
- Received final AS1 closure as FIX confirmed.

With AS2/ACM indirectly through AS1:
- AS1 relayed AS2/ACM requests for exact current verification.
- I provided the requested details through AS1:
  - DNS results
  - Route selection
  - Ping TTL/RTT
  - TCP connect/refuse status
  - HTTP method used
  - HTTP status lines
  - Body summary
  - Direct IP versus hostname behavior

Final outcome:
- The ACM TCP connection-refused issue was resolved and verified from both Uni and User.
- No local firewall or NAT changes were made.
- Uni retained the newly installed specific routes via AS1.
- A separate Uni-local DNS forwarder issue was identified but not repaired during this experiment.