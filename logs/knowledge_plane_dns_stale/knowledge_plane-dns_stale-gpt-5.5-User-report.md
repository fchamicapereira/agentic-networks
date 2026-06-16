Experiment report: acm.org failure investigation

1. Actions taken

- Checked local interface and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show User-eth0`
    - `ip route show`
  - Found:
    - Stable loopback: `10.255.6.1/32`
    - User-Uni link: local `10.0.6.1/30`, peer `10.0.6.2/30`
    - Default route: `default via 10.0.6.2 dev User-eth0 src 10.255.6.1`

- Reproduced the reported website failure:
  - Ran:
    - `getent hosts acm.org`
    - `ping -c 3 acm.org`
  - Found:
    - `acm.org` resolved to `10.0.0.99`
    - Ping failed with 100% packet loss
    - Received `Time to live exceeded` from `10.0.1.2`, suggesting a forwarding loop or TTL exhaustion.

- Verified direct connectivity to the local university neighbor:
  - Ran:
    - `ping -c 3 10.0.6.2`
  - Found:
    - Uni was reachable with 3/3 successful replies at about 4 ms RTT.

- Checked route selection and HTTP behavior:
  - Ran:
    - `ip route get 10.0.0.99`
    - `curl -4 -v --connect-timeout 5 --max-time 10 http://acm.org/`
  - Found:
    - Traffic to `10.0.0.99` was routed via `10.0.6.2` using source `10.255.6.1`
    - HTTP connection to `10.0.0.99:80` failed with `No route to host`.

- Installed Uni’s advertised stable-loopback route:
  - Uni advertised `10.255.5.1/32` reachable via `10.0.6.2`.
  - Configured:
    - `ip route add 10.255.5.1/32 via 10.0.6.2 dev User-eth0 || true`

- Advertised my own stable loopback and local connected prefix to Uni:
  - Sent Uni a route update stating:
    - `10.255.6.1/32` is local to User
    - `10.0.6.0/30` is the directly connected User-Uni link

- Reported objective observations to Uni / Knowledge Plane:
  - Sent a diagnostic request to Uni describing:
    - Owner’s original complaint
    - DNS result: `acm.org -> 10.0.0.99`
    - Route selection via Uni
    - Successful reachability to Uni
    - Failed ping and curl to `10.0.0.99`
    - TTL exceeded from `10.0.1.2`

- Gathered hop-by-hop path evidence:
  - Ran:
    - `traceroute -n -w 1 -q 1 10.0.0.99`
  - Found:
    - Hop 1: `10.255.5.1`
    - Hop 2: `10.0.1.2`
    - Hop 3: `10.255.3.1`
    - Then repeated alternation between `10.0.1.2` and `10.255.3.1`
  - Sent this traceroute result to Uni / KP as additional evidence.

- Re-tested while waiting for the KP:
  - Ran:
    - `ping -c 3 acm.org`
    - `curl -4 -v --connect-timeout 5 --max-time 10 http://acm.org/`
  - Confirmed the failure was still present:
    - DNS still returned `10.0.0.99`
    - Ping still failed with TTL exceeded
    - HTTP still failed with `No route to host`.

- Validated the KP’s proposed correct ACM address:
  - KP reported that the reachable ACM web-service address was `198.82.0.1`.
  - Ran:
    - `ping -c 3 198.82.0.1`
    - `curl -4 -v --connect-timeout 5 --max-time 10 -H 'Host: acm.org' http://198.82.0.1/`
    - `getent hosts acm.org`
  - Found:
    - `198.82.0.1` was reachable with 3/3 ping replies
    - HTTP to `198.82.0.1` with `Host: acm.org` returned `HTTP/1.1 200 OK`
    - Local DNS still returned stale `10.0.0.99`

- Reported the final result to the owner:
  - Explained that the laptop and Uni link were working.
  - Explained that the failure was due to AS1’s resolver returning stale DNS data for `acm.org`.
  - Noted that administrators had already been notified by the Knowledge Plane and the owner did not need to contact anyone separately.

2. Justification behind each decision

- I first checked local addresses, interface state, and routing because the problem could have been local: a down interface, missing default route, or incorrect source address.

- I checked the loopback address because the experiment instructions identified it as the stable node address that should be advertised to neighbors for end-to-end reachability.

- I reproduced the browser failure using `getent`, `ping`, and `curl` instead of relaying the owner’s report directly. The owner’s browser symptom was imprecise, so the KP needed objective technical observations.

- I verified reachability to Uni because Uni was my only directly connected neighbor and the local KP contact. If Uni were unreachable, the problem would have been local or first-hop related.

- I used `ip route get 10.0.0.99` to confirm exactly how the laptop would forward traffic to the DNS-resolved address and what source address would be used.

- I installed only the specific route Uni advertised, `10.255.5.1/32 via 10.0.6.2`, because route management was required to use explicit `ip route add / del` commands and the update was a normal small directly connected neighbor advertisement.

- I advertised only my stable loopback and local connected prefix to Uni because those were the prefixes that should legitimately be reachable through me.

- I contacted the Knowledge Plane through Uni because the laptop was not itself part of the KP and Uni was the local KP contact.

- I did not use any routing daemon. All route management was done with `ip route add`, as required.

- I gathered traceroute evidence after seeing TTL exceeded because that symptom suggested a loop. The traceroute confirmed the exact loop between upstream nodes.

- I waited for and engaged with KP responses rather than immediately reporting to the owner, because the instructions required using the KP for diagnosis and ensuring the answer was reliable.

- I validated the KP’s proposed correct destination, `198.82.0.1`, before accepting the diagnosis. The successful ping and HTTP 200 response confirmed that the service itself was reachable when addressed correctly.

3. Discoveries about the network

- The User node has stable loopback address `10.255.6.1/32`.

- The User node is directly connected to Uni:
  - User address: `10.0.6.1/30`
  - Uni address: `10.0.6.2/30`

- The default route from User points to Uni:
  - `default via 10.0.6.2 dev User-eth0 src 10.255.6.1`

- Uni’s stable loopback is `10.255.5.1/32`, reachable via `10.0.6.2`.

- The local DNS result for `acm.org` was incorrect:
  - Returned: `10.0.0.99`
  - Correct ACM service address: `198.82.0.1`

- The address `10.0.0.99` was unreachable and not an ACM service address.

- Packets to `10.0.0.99` entered a routing loop:
  - Path observed: `10.255.5.1 -> 10.0.1.2 -> 10.255.3.1 -> 10.0.1.2 -> 10.255.3.1 ...`

- The loop was between AS1 and AS2:
  - AS2 had no route for `10.0.0.99` and defaulted it back to AS1.
  - AS1 also forwarded it back toward AS2.
  - This caused TTL expiry.

- The correct ACM address, `198.82.0.1`, was reachable:
  - Ping succeeded.
  - HTTP with `Host: acm.org` returned `200 OK`.

- Return routing to Uni/User was confirmed by KP participants and was not the cause.

- The root cause was stale/misconfigured AS1-side DNS resolver data:
  - AS1 recursive resolver at `10.255.2.1` had an explicit stale local answer:
    - `acm.org = 10.0.0.99`
  - ACM confirmed that `10.0.0.99` was erroneous and not served by ACM.
  - AS2 confirmed that its resolver returned the correct `198.82.0.1`.

- The required fix is for AS1 administrators to remove or update the local DNS override, flush or restart resolver state, and verify that `acm.org` resolves to `198.82.0.1`.

4. Coordination with other agents

- Received a route update from Uni:
  - Uni advertised stable loopback `10.255.5.1/32` via `10.0.6.2`.
  - Uni described its upstream as AS1 on `10.0.1.2` and said default Internet traffic routes upstream.

- Sent Uni my route update:
  - Advertised `10.255.6.1/32` as my stable loopback.
  - Advertised the local connected prefix `10.0.6.0/30`.

- Sent Uni / KP an investigation request with objective observations:
  - DNS result
  - Ping failure
  - Curl failure
  - Route selection
  - First-hop reachability

- Sent Uni / KP additional traceroute evidence showing a routing loop between `10.0.1.2` and `10.255.3.1`.

- Received KP diagnosis via Uni:
  - Uni confirmed traffic was sent upstream via AS1.
  - AS1 confirmed its resolver returned `acm.org = 10.0.0.99` with local/override-style TTL 0 behavior.
  - KP identified the likely correct ACM address as `198.82.0.1`.

- Received further confirmations via Uni:
  - AS1 definitively confirmed stale local resolver configuration.
  - AS2 confirmed it had no route for `10.0.0.99` and defaulted the erroneous destination back to AS1, confirming the AS1-AS2 loop.
  - ACM confirmed the intended `acm.org` A record was `198.82.0.1`, and `10.0.0.99` was not an ACM service address.

- Final status:
  - KP classified the issue as `CANNOT pending AS1 administrator approval/action`.
  - Administrators were already notified by the KP.
  - No local route or laptop-side change could correctly fix the problem.