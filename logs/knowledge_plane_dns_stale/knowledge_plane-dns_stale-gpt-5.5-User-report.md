Experiment report

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show User-eth0`
    - `ip route show`
  - Found stable loopback address `128.173.10.1/32`.
  - Found point-to-point link to Uni:
    - User: `10.0.6.1/30`
    - Uni: `10.0.6.2/30`
  - Found default route:
    - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- Reproduced the reported acm.org failure using the stable loopback source:
  - Ran:
    - `getent hosts acm.org`
    - `ping -c 3 -I 128.173.10.1 acm.org`
  - DNS resolved `acm.org` to `198.82.0.99`.
  - Ping failed with ICMP `Destination Host Unreachable` from `198.82.0.254`.

- Tested HTTP and HTTPS directly:
  - Ran:
    - `curl -4 -I --connect-timeout 5 --max-time 10 --interface 128.173.10.1 http://acm.org/`
    - `curl -4 -I --connect-timeout 5 --max-time 10 --interface 128.173.10.1 https://acm.org/`
  - Both failed with `No route to host`.

- Advertised my stable loopback prefix to Uni:
  - Sent Uni:
    - `User advertises stable loopback prefix 128.173.10.1/32. Please route it network-wide.`
  - This was necessary because only the loopback address is globally routable; link addresses are infrastructure-only.

- Installed a route to Uni’s stable loopback after Uni advertised it:
  - Uni advertised `128.173.0.1/32` with next hop `10.0.6.2`.
  - Ran:
    - `ip route add 128.173.0.1/32 via 10.0.6.2 dev User-eth0 || true`
  - Verified routing:
    - `ip route get 198.82.0.99 from 128.173.10.1`
    - `ping -c 2 -I 128.173.10.1 10.0.6.2`
    - `ping -c 2 -I 128.173.10.1 128.173.0.1`

- Asked Uni / the Knowledge Plane to investigate:
  - Reported the owner’s original complaint and my technical observations:
    - `acm.org` resolved to `198.82.0.99`
    - ICMP failures came from `198.82.0.254`
    - HTTP/HTTPS failed with `No route to host`
    - Traffic was sourced from `128.173.10.1`

- Performed additional scoping tests:
  - Ran:
    - `ping -c 3 -I 128.173.10.1 198.82.0.254`
    - `ping -c 3 -I 128.173.10.1 8.8.8.8`
    - `curl -4 -I --connect-timeout 5 --max-time 10 --interface 128.173.10.1 http://example.com/`
  - Found:
    - `198.82.0.254` was reachable.
    - `8.8.8.8` did not reply; one probe got `Time to live exceeded` from `10.0.1.2`.
    - `example.com` DNS resolution failed.

- Tested the acm.org IP directly and approximated a traceroute:
  - Ran:
    - `curl -4 -I --connect-timeout 5 --max-time 10 --interface 128.173.10.1 http://198.82.0.99/`
    - TTL-limited pings:
      - `ping -c 1 -W 2 -t <ttl> -I 128.173.10.1 198.82.0.99`
  - Observed path evidence:
    - TTL 1: `128.173.0.1`
    - TTL 2: `10.0.1.2`
    - TTL 3: `154.54.1.1`
    - TTL 4 and later: `198.82.0.254` reporting `Destination Host Unreachable`
  - Direct HTTP to `198.82.0.99` also failed.

- Checked local DNS configuration and whether `www.acm.org` differed:
  - Ran:
    - `cat /etc/resolv.conf`
    - `ip route show`
    - `getent hosts acm.org`
    - `getent hosts www.acm.org`
  - Found:
    - `/etc/resolv.conf` used `nameserver 127.0.0.1`
    - both `acm.org` and `www.acm.org` resolved to `198.82.0.99`

- Re-tested after the failure mode changed:
  - Ran:
    - `ping -c 2 -I 128.173.10.1 198.82.0.99`
    - `curl -4 -I --connect-timeout 5 --max-time 10 --interface 128.173.10.1 http://acm.org/`
  - Later behavior changed from explicit host-unreachable to timeout, but the site still did not load.

2. Justification behind decisions

- I first inspected local addressing and routing to identify the correct stable source address. The testbed instructions state that non-adjacent diagnostic traffic must be sourced from the loopback address, not the point-to-point link address, because remote nodes may not have routes back to link addresses.

- I used `getent hosts` before HTTP testing to separate DNS resolution from transport or routing failures.

- I used `ping -I 128.173.10.1` and `curl --interface 128.173.10.1` to ensure replies would be routable back to the User node and to avoid false negatives caused by using `10.0.6.1`.

- I advertised `128.173.10.1/32` to Uni because the stable loopback prefix is the only User address that should be advertised network-wide.

- I installed only the specific route to Uni’s stable address using:
  - `ip route add 128.173.0.1/32 via 10.0.6.2 dev User-eth0`
  This followed the requirement to manage routes only with `ip route add / del` and avoided advertising or installing infrastructure `/30` routes network-wide.

- I involved the Knowledge Plane through Uni because the failure appeared to be beyond the local User-Uni link. The local default route was present, Uni was reachable, and the ICMP errors came from a remote ACM-side gateway.

- I performed scope tests against `198.82.0.254`, `8.8.8.8`, and `example.com` to determine whether the problem was specific to acm.org or part of a broader routing/DNS failure.

- I tested `198.82.0.99` directly to distinguish DNS name resolution from actual reachability of the returned address.

- I used TTL-limited pings as a traceroute substitute to identify where the failure occurred. This showed that packets progressed through Uni and AS1/AS2 path elements before failing at or behind `198.82.0.254`.

- I did not apply any workaround such as overriding DNS locally to `198.82.0.1`, because the Knowledge Plane identified the issue as stale customer DNS data requiring AS1 administrator approval. The correct fix was upstream, not local.

3. Discoveries about the network

- User’s stable globally routable address is:
  - `128.173.10.1/32`

- User is directly connected only to Uni:
  - User side: `10.0.6.1/30`
  - Uni side: `10.0.6.2/30`

- The User default route is via Uni:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- Uni’s stable prefix is:
  - `128.173.0.1/32`
  - Installed route:
    - `128.173.0.1 via 10.0.6.2 dev User-eth0`

- Local DNS for `acm.org` and `www.acm.org` resolved both names to:
  - `198.82.0.99`

- `198.82.0.99` was not reachable from User.
  - Initially, ping and curl failed with `Destination Host Unreachable` / `No route to host`.
  - Later, the symptom changed to timeout, but connectivity still failed.

- `198.82.0.254`, the apparent ACM gateway, was reachable from User:
  - Ping succeeded with approximately 94 ms RTT.

- TTL-limited probes showed the route toward `198.82.0.99` progressed through:
  - `128.173.0.1`
  - `10.0.1.2`
  - `154.54.1.1`
  - then failure at `198.82.0.254`

- The Knowledge Plane confirmed the root cause:
  - AS1 resolver `4.2.2.1`, used by Uni’s forwarded DNS, was serving stale or incorrect local DNS data for `acm.org`.
  - It returned `198.82.0.99`.
  - ACM confirmed the intended working target was `198.82.0.1`.
  - `198.82.0.99` was not routed or served behind ACM’s gateway.
  - HTTP to `198.82.0.1` worked from Uni, while HTTP/ping to `198.82.0.99` failed.

- A separate issue was found:
  - Off-campus/default Internet tests revealed an AS1-AS2 default-routing problem.
  - AS2 removed an erroneous default route back to AS1.
  - AS1 still required administrator-approved default/transit route changes for general Internet reachability.
  - This was separate from the primary `acm.org` failure.

4. Coordination with other agents

- Coordinated only with directly connected neighbor Uni, as required.

- Sent Uni my stable loopback advertisement:
  - `128.173.10.1/32`

- Received Uni’s route advertisement:
  - `128.173.0.1/32`
  - next hop `10.0.6.2`
  - Uni also stated default/Internet reachability was available through Uni toward AS1.

- Sent Uni detailed technical observations for the Knowledge Plane:
  - DNS result for `acm.org`
  - ping failures sourced from `128.173.10.1`
  - curl failures on ports 80 and 443
  - direct-IP test results
  - TTL-limited path evidence
  - later changed symptom from host-unreachable to timeout

- Uni / the Knowledge Plane coordinated with AS1, AS2, and ACM.
  - AS1 and AS2 independently reproduced that `198.82.0.99` was unreachable behind `198.82.0.254`.
  - ACM confirmed the correct target was `198.82.0.1`.
  - AS1 notified administrators and reported `CANNOT` pending admin approval/action to correct customer DNS resolver data.
  - AS2 addressed a separate erroneous default-route issue.

- Final owner-facing conclusion:
  - No User-side action was needed.
  - The browser failure was caused by upstream stale DNS data returning an unreachable ACM target.
  - Administrators had already been notified through the Knowledge Plane path.