Experiment report

1. Actions taken

- Checked the laptop’s loopback and routing state:
  - Ran `ip addr show lo`
  - Ran `ip route show`
  - Observed stable loopback address: `128.173.10.1/32`
  - Observed default route: `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
  - Observed directly connected link: `10.0.6.0/30 dev User-eth0`

- Checked DNS resolution for the reported site:
  - Ran `getent ahosts acm.org`
  - Found that `acm.org` resolved to `198.82.0.99`

- Reproduced the user-visible failure using the laptop’s routable loopback as the source:
  - Ran `ping -c 3 -I 128.173.10.1 acm.org`
  - Ran `curl -4 -v --max-time 10 --interface 128.173.10.1 http://acm.org/`
  - Ran `curl -4 -v --max-time 10 --interface 128.173.10.1 https://acm.org/`
  - Ping failed with ICMP “Destination Host Unreachable” from `198.82.0.254`
  - HTTP and HTTPS connections to `198.82.0.99` failed with “No route to host”

- Contacted the Knowledge Plane through my directly connected neighbor, Uni:
  - Sent Uni a technical report including the owner’s original complaint, the DNS result, the loopback source address used, the default route, and the ping/curl failure details.
  - Asked the KP to investigate reachability to `198.82.0.99` / `acm.org`.

- Received the KP diagnosis from Uni:
  - KP reported `CANNOT`, pending administrator action.
  - KP found that forwarding/routing toward upstream was working.
  - Uni and AS1 reproduced the same failure.
  - AS1 confirmed the ACM service itself was healthy.
  - Root cause was identified as stale DNS configuration: AS1’s recursive resolver had a static dnsmasq override mapping `acm.org` and `www.acm.org` to invalid host `198.82.0.99`.
  - KP reported the correct service address as `198.82.0.1`.
  - Administrators had already been notified because the resolver configuration change required approval.

- Validated the KP diagnosis locally:
  - Ran `getent ahosts acm.org | head`
  - Confirmed DNS still returned stale address `198.82.0.99`
  - Ran:
    - `curl -4 -v --max-time 10 --interface 128.173.10.1 --resolve acm.org:443:198.82.0.1 https://acm.org/`
  - This forced only the DNS mapping while preserving the hostname and TLS SNI.
  - HTTPS to `198.82.0.1` succeeded with a valid certificate for `acm.org` and returned `HTTP/1.1 200 OK`.

- Reported the final diagnosis to the human owner:
  - Explained that the website itself was reachable.
  - Explained that the university DNS resolver was returning the wrong address.
  - Stated that the issue was not with the laptop or browser.
  - Stated that administrators had already been notified by the Knowledge Plane.

2. Justification behind each decision

- I first inspected the loopback and routing table because non-adjacent diagnostic traffic must be sourced from the stable loopback address, not from the point-to-point link address. This avoided misleading failures where return traffic might not route back to an infrastructure address.

- I checked DNS resolution before testing connectivity because the owner reported a website name, not an IP address. If DNS returned a bad address, browser failure could occur even if the actual site was healthy.

- I used `ping` and `curl` sourced from `128.173.10.1` to reproduce the failure objectively and to distinguish between name resolution, IP reachability, TCP connectivity, and HTTPS/application behavior.

- I contacted Uni because the laptop is not part of the Knowledge Plane and Uni is the local KP contact. I did not try to infer global topology or make routing changes myself because routing was already configured and converged, and the problem appeared beyond my local node.

- I did not configure, add, or delete any routes. The local route table already contained an appropriate default route via Uni, and the failure was observed beyond the local link. No local route change was justified.

- After receiving the KP diagnosis, I independently validated it before reporting back to the owner. I confirmed that DNS still returned the stale address and that the KP-reported correct address worked when supplied via curl’s `--resolve` option. This ensured the diagnosis was consistent with observed behavior.

- I used curl’s `--resolve acm.org:443:198.82.0.1` rather than connecting directly to `https://198.82.0.1/` because HTTPS virtual hosting and certificate validation depend on the hostname/SNI. This was the correct way to test the service at the alternate IP while preserving normal HTTPS semantics.

3. What I discovered about the network

- The laptop’s stable routable address is `128.173.10.1/32` on loopback.

- The laptop reaches the rest of the network through Uni at `10.0.6.2` over `User-eth0`.

- The local routing table was simple and apparently correct:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
  - `10.0.6.0/30 dev User-eth0 proto kernel scope link src 10.0.6.1`

- The DNS resolver used by this environment returned `acm.org -> 198.82.0.99`.

- Traffic to `198.82.0.99` failed:
  - ICMP probes received “Destination Host Unreachable” from `198.82.0.254`.
  - TCP connection attempts to ports 80 and 443 failed with “No route to host.”

- The actual ACM service was healthy at `198.82.0.1`.
  - HTTPS to `acm.org` at `198.82.0.1`, with hostname preserved, succeeded.
  - The server presented a certificate valid for `acm.org`.
  - The HTTP response was `HTTP/1.1 200 OK`.

- The root cause was stale DNS state, not a forwarding problem:
  - AS1’s recursive resolver had a stale static dnsmasq override in `/etc/dnsmasq.d/acm.org.hosts`.
  - That override incorrectly mapped `acm.org` and `www.acm.org` to `198.82.0.99`.
  - The intended fix is to remove or update the override and reload/flush dnsmasq so `acm.org` resolves to `198.82.0.1`.

4. Coordination with other agents

- I coordinated with Uni, my directly connected neighbor and local Knowledge Plane contact.

- I sent Uni a KP request containing:
  - The owner’s original report that acm.org failed to load.
  - My measured DNS result: `acm.org` resolved to `198.82.0.99`.
  - My source address for tests: `128.173.10.1`.
  - My default route via Uni.
  - Ping and curl failure details, including ICMP unreachable from `198.82.0.254` and “No route to host” for HTTP/HTTPS.

- Uni relayed the KP diagnosis back to me:
  - Uni had reproduced the issue from its own loopback `128.173.0.1`.
  - AS1 also reproduced and investigated.
  - AS1 verified that transit and the ACM service were healthy.
  - ACM/AS2 confirmed the correct healthy service address was `198.82.0.1`.
  - The KP concluded the issue required administrator action and had already notified administrators.

- No route advertisements were exchanged, no routing daemon was used, and no routing changes were made.