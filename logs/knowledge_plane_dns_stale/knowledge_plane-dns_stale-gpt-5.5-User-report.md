Experiment report

1. Actions taken

- Inspected the laptop’s local addressing and routing:
  - Ran `ip addr show lo`
    - Found stable loopback address: `128.173.10.1/32`
  - Ran `ip route show`
    - Found default route: `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
    - Found directly connected link: `10.0.6.0/30 dev User-eth0 src 10.0.6.1`
  - Ran `ip addr show User-eth0`
    - Confirmed physical link address `10.0.6.1/30` and peer `10.0.6.2`.

- Advertised the laptop’s stable loopback to Uni:
  - Sent Uni a route advertisement for `128.173.10.1/32`, reachable via User on the User-Uni link.
  - I did not add any new route locally because the default route via Uni was already present and correct.

- Verified local adjacency to Uni:
  - Ran `ping -c 3 10.0.6.2`
  - Result: 3/3 replies, approximately 4 ms, confirming the direct link to Uni was healthy.

- Reproduced the reported acm.org failure using the stable loopback as source:
  - Ran `getent hosts acm.org`
    - Result: `acm.org` resolved to `198.82.0.99`.
  - Ran `ping -c 3 -I 128.173.10.1 acm.org`
    - Result: 100% packet loss, with ICMP “Destination Host Unreachable” from `198.82.0.254`.
  - Ran:
    - `curl -4 -v --connect-timeout 5 --max-time 15 --interface 128.173.10.1 http://acm.org/`
    - `curl -4 -v --connect-timeout 5 --max-time 15 --interface 128.173.10.1 https://acm.org/`
    - Both failed with `No route to host` while trying to reach `198.82.0.99`.

- Confirmed route selection and compared against other destinations:
  - Ran `ip route get 198.82.0.99 from 128.173.10.1`
    - Result: traffic selected `via 10.0.6.2 dev User-eth0`.
  - Ran `ping -c 3 -I 128.173.10.1 128.173.0.1`
    - Result: Uni loopback reachable, 3/3 replies.
  - Ran `getent hosts example.org`, `ping`, and `curl` tests for example.org
    - DNS lookup failed locally with temporary name resolution failure, so this was not useful as a generic web comparison.

- Tested upstream reachability after Uni advertised AS1/default availability:
  - Ran `ping -c 3 -I 128.173.10.1 4.2.2.1`
    - Result: AS1 loopback reachable, 3/3 replies, about 24 ms.
  - Ran `ping -c 3 -I 128.173.10.1 198.82.0.254`
    - Result: reachable, 3/3 replies, about 94 ms.
  - Checked `/etc/resolv.conf`
    - Resolver was local: `nameserver 127.0.0.1`.
  - Rechecked `getent hosts acm.org` and `getent ahostsv4 acm.org`
    - Both confirmed `198.82.0.99`.

- Collected path evidence:
  - Ran `traceroute -4 -n -s 128.173.10.1 -w 2 -q 1 198.82.0.99`
    - Observed path through Uni and then a loop between `10.0.1.2` and `154.54.1.1`.
  - Ran a TCP connect test:
    - `nc -4 -s 128.173.10.1 -v -w 5 198.82.0.99 443`
    - Result: `No route to host`.
  - Re-ran `ping -c 3 -I 128.173.10.1 198.82.0.99`
    - Later result changed to ICMP `Time to live exceeded` from `10.0.1.2`, consistent with a routing loop.

- Repeated validation before accepting the final diagnosis:
  - Confirmed `4.2.2.1` remained reachable from `128.173.10.1`.
  - Confirmed `198.82.0.99` remained unreachable.
  - Confirmed HTTPS to `acm.org` still failed with `No route to host`.

- Validated the Knowledge Plane’s workaround:
  - Ran `ping -c 3 -I 128.173.10.1 198.82.0.1`
    - Result: 3/3 replies, about 98 ms.
  - Ran `curl -4 -I --connect-timeout 5 --max-time 10 --interface 128.173.10.1 http://198.82.0.1/`
    - Result: server responded, though HEAD returned `501 Unsupported method ('HEAD')`, confirming the host was reachable and serving HTTP.
  - Re-ran `getent hosts acm.org`
    - Still returned stale/wrong address `198.82.0.99`.

2. Justification behind decisions

- I checked loopback addressing first because the stable loopback address is the only address remote nodes can reliably route back to. All non-adjacent diagnostics were sourced from `128.173.10.1` to avoid misleading failures from using the point-to-point link address.

- I confirmed the direct User-Uni link before escalating, because if `10.0.6.2` were unreachable, the failure could have been local to the laptop’s physical connection.

- I advertised `128.173.10.1/32` to Uni because remote return routing to the laptop required Uni and upstream nodes to know the laptop’s stable prefix.

- I did not install additional local routes because the default route via Uni was already present:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
  This matched the expected configuration, so changing routes locally would not have been justified.

- I tested DNS, ICMP, HTTP, and HTTPS separately because a browser failure could be caused by name resolution, routing, transport connectivity, or web-service behavior. The tests showed that DNS resolved, but to an unreachable address.

- I asked the Knowledge Plane through Uni because the failure involved upstream reachability and resolver behavior outside the laptop’s local view.

- I continued pushing for a diagnosis after initial tests because local connectivity and upstream reachability were working, yet acm.org failed. The traceroute evidence indicated the problem was not simply “website down” but involved incorrect routing or an invalid destination address.

- I validated the proposed workaround before reporting it to the owner because the KP claimed `198.82.0.1` was the valid ACM service address. Direct tests showed that address was reachable, supporting the diagnosis.

3. Discoveries about the network

- The laptop’s stable address is `128.173.10.1/32`.

- The directly connected Uni peer is reachable at `10.0.6.2`, and Uni’s stable loopback `128.173.0.1/32` is reachable.

- The laptop’s default route via Uni was correctly configured:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- General upstream connectivity was functional:
  - AS1 loopback `4.2.2.1` was reachable from `128.173.10.1`.

- The local DNS path resolved `acm.org` to `198.82.0.99`.

- `198.82.0.99` was not a valid reachable ACM web-service address. Traffic to it initially produced unreachable errors and later showed a routing loop between:
  - AS1: `10.0.1.2`
  - AS2: `154.54.1.1`

- The valid ACM web-service address was confirmed to be `198.82.0.1`.

- The root cause of the browser failure was not a laptop, Uni, or local routing problem. It was stale/wrong DNS behavior at AS1:
  - AS1 resolver `4.2.2.1` had a static dnsmasq override forcing `acm.org` to `198.82.0.99`.
  - AS2/ACM confirmed `acm.org` should resolve to `198.82.0.1`.
  - `198.82.0.99` had been withdrawn and was not served.

- AS2 later installed a local blackhole for `198.82.0.99/32` to stop the AS1-AS2 forwarding loop. This fixed the loop symptom but did not fix the user’s browser problem, because DNS still pointed acm.org at the bad address.

- The remaining required fix is for AS1 administrators to update the dnsmasq override to `198.82.0.1` and restart or flush dnsmasq. The KP classified this as `CANNOT` because it changes customer-facing DNS behavior and requires AS1 administrator approval.

4. Coordination with other agents

- Coordinated directly with Uni, the laptop’s local Knowledge Plane contact.

- Sent Uni my route advertisement:
  - `128.173.10.1/32` reachable via User on the User-Uni link.

- Received Uni’s route advertisement:
  - Uni loopback `128.173.0.1/32` reachable via `10.0.6.2`.
  - Later, AS1 loopback `4.2.2.1/32` and upstream/default reachability were advertised via Uni.

- Reported objective failure observations to Uni/KP rather than relaying the owner’s browser complaint directly. These included:
  - Local default route state.
  - Healthy User-Uni adjacency.
  - DNS result for `acm.org`.
  - ICMP unreachable and TTL exceeded behavior.
  - HTTP/HTTPS failures.
  - Traceroute loop evidence.
  - Successful reachability to Uni and AS1 loopbacks.
  - Successful reachability to the alternate ACM service address `198.82.0.1`.

- Uni/KP investigated beyond my local view and reported:
  - Uni forwarding was correct.
  - AS1 and AS2 were involved in a loop for `198.82.0.99`.
  - AS2 blackholed `198.82.0.99/32` to stop the loop.
  - AS1 resolver `4.2.2.1` had a static dnsmasq override returning the stale address.
  - The permanent DNS fix requires AS1 administrator approval.

- I reported the final outcome to the laptop owner:
  - The problem is not on the laptop.
  - The DNS answer for `acm.org` is wrong.
  - Administrators have already been notified.
  - The workaround is to use `http://198.82.0.1/` directly or a resolver that returns `198.82.0.1` for `acm.org`.