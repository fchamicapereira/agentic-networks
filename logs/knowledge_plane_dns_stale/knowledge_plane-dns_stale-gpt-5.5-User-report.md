Experiment report: acm.org website failure investigation

1. Actions taken

- Checked local addressing, routes, resolver configuration, and interface state:
  - `ip addr show lo`
  - `ip route show`
  - `cat /etc/resolv.conf`
  - `ip addr show User-eth0 || ip addr show eth0`

- Confirmed the laptop’s stable loopback address:
  - Found `128.173.10.1/32` on `lo`.

- Confirmed local connectivity to the directly connected neighbor Uni:
  - `ping -c 3 10.0.6.2`
  - Result: 0% packet loss, about 4 ms RTT.

- Tested DNS resolution for the reported site:
  - `getent ahosts acm.org`
  - Python `socket.getaddrinfo()` for `acm.org` and `www.acm.org`
  - Result: both resolved to `10.0.0.99`.

- Reproduced the website failure using the stable loopback as source:
  - `curl -4 -v --connect-timeout 5 --max-time 15 --interface 128.173.10.1 http://acm.org/`
  - `curl -4 -vk --connect-timeout 5 --max-time 15 --interface 128.173.10.1 https://acm.org/`
  - Result: both failed with `No route to host` when connecting to `10.0.0.99` on ports 80 and 443.

- Advertised my stable loopback to Uni:
  - Sent message to Uni stating that `128.173.10.1/32` is reachable via `10.0.6.1`.

- Sent the initial technical failure report to Uni/KP with:
  - Owner’s original symptom.
  - Local loopback and default route.
  - DNS result.
  - Curl failures.
  - Confirmation that the direct link to Uni was healthy.

- Gathered path-level diagnostics:
  - `ip route get 10.0.0.99 from 128.173.10.1`
  - `ping -c 3 -I 128.173.10.1 10.0.0.99`
  - `traceroute -n -s 128.173.10.1 -w 2 -q 1 10.0.0.99`
  - Result: route lookup used default via `10.0.6.2`; ping received TTL-exceeded from `10.0.1.2`; traceroute showed a loop involving `10.0.1.2` and `154.54.1.1`.

- Reported the routing-loop evidence to Uni/KP.

- Responded to KP’s request to inspect local DNS resolver/forwarder configuration without making changes:
  - Checked `/etc/resolv.conf`.
  - Searched `/etc/hosts` and related files for `acm.org`, `www.acm.org`, and `10.0.0.99`.
  - Searched dnsmasq and NetworkManager-related configuration for DNS overrides.
  - Checked listening DNS processes with `ss -lntup '( sport = :53 )'`.
  - Checked dnsmasq process details:
    - `ps -fp 264`
    - `tr '\0' ' ' < /proc/264/cmdline`
  - Found dnsmasq running with:
    - `--no-resolv`
    - `--no-hosts`
    - `--server=4.2.2.1`
    - `--listen-address=127.0.0.1`
    - `--listen-address=128.173.10.1`

- Queried local DNS directly:
  - `dig acm.org A`
  - `dig @127.0.0.1 acm.org A`
  - `dig www.acm.org A`
  - `dig @127.0.0.1 www.acm.org A`
  - Result: local dnsmasq returned `10.0.0.99` for both names.

- Reported the DNS forwarder findings to Uni/KP.

- Did not configure or modify any routes.
  - No `ip route add` or `ip route del` commands were used.
  - The observed routing state already had a default route via Uni:
    - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- Reported the KP diagnosis back to the owner and marked the investigation complete.

2. Justification behind each decision

- I first inspected local state because the owner’s browser symptom was non-specific. I needed objective evidence about whether the failure was caused by local addressing, routing, DNS, or remote service reachability.

- I used the loopback address `128.173.10.1` as the source for diagnostic traffic because it is the stable node address that remote nodes can route back to. The point-to-point link address `10.0.6.1` is only infrastructure-scoped and could have caused misleading reply failures.

- I tested the direct link to Uni to confirm that the laptop’s immediate network attachment was healthy before escalating to the Knowledge Plane.

- I tested DNS resolution separately from HTTP/HTTPS connectivity to determine whether the browser failure was a name-resolution problem, a routing problem, or a web-service problem.

- I used `curl` to both HTTP and HTTPS because browsers commonly try HTTPS, but either protocol should have shown whether TCP connectivity to the resolved address worked.

- I sent the findings to Uni rather than directly acting on the wider network because User is not part of the Knowledge Plane and does not have global topology visibility.

- I collected traceroute and ping evidence after the initial curl failures because `No route to host` alone did not identify where the failure occurred. Traceroute showed a likely routing loop, which was important evidence for the KP.

- I did not change DNS or routing configuration when KP requested inspection only. The goal at that point was diagnosis, not local workaround or uncoordinated repair.

- I inspected dnsmasq command-line options specifically because `/etc/resolv.conf` pointed to `127.0.0.1`, meaning the laptop was using a local DNS forwarder. The command line revealed the real upstream resolver, `4.2.2.1`.

3. What I discovered about the network

- User’s stable loopback address is:
  - `128.173.10.1/32`

- User is directly connected to Uni over:
  - User side: `10.0.6.1/30`
  - Uni side: `10.0.6.2/30`

- User’s default route is:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- The local link to Uni is healthy.

- User’s local DNS resolver is dnsmasq listening on:
  - `127.0.0.1:53`
  - `128.173.10.1:53`

- Local dnsmasq is configured not to use local hosts or resolv.conf:
  - `--no-resolv`
  - `--no-hosts`

- Local dnsmasq forwards upstream DNS queries to:
  - `4.2.2.1`

- `acm.org` and `www.acm.org` resolved to:
  - `10.0.0.99`

- `10.0.0.99` is not the intended ACM web address. KP later confirmed it is a private/non-advertised address created by a bad AS1 resolver override.

- Traffic from User to `10.0.0.99` fails and appears to loop between AS1 and AS2 default paths. Traceroute showed repeated appearances of:
  - `10.0.1.2`
  - `154.54.1.1`

- KP confirmed the root cause:
  - AS1 resolver `4.2.2.1` has a bad local dnsmasq override:
    - `--local=/acm.org/`
    - `--address=/acm.org/10.0.0.99`

- KP also confirmed:
  - AS2 resolver returns the intended ACM address `198.82.0.1`.
  - ACM HTTP service at `198.82.0.1` is reachable.
  - The problem is not User’s local routing, Uni’s local routing, or the laptop’s local DNS stub.
  - The required fix is for AS1 administrators to remove or correct the bad DNS override and reload/restart the AS1 resolver.

4. Coordination with other agents

- Coordinated only with directly connected neighbor Uni, which is User’s Knowledge Plane contact.

- Received from Uni:
  - Uni’s stable loopback advertisement:
    - `128.173.0.1/32` reachable via `10.0.6.2`
  - Confirmation that Uni already had User’s loopback route:
    - `128.173.10.1/32 via 10.0.6.1`

- Sent Uni:
  - User’s stable loopback advertisement:
    - `128.173.10.1/32 via 10.0.6.1`
  - Initial objective failure report for acm.org.
  - Additional traceroute/ping evidence showing a routing loop.
  - DNS resolver inspection results showing local dnsmasq forwarded to `4.2.2.1`.

- Received KP diagnosis through Uni:
  - Status: `CANNOT`, pending AS1 administrator action.
  - Root cause: AS1 DNS resolver override incorrectly maps `acm.org` and `www.acm.org` to `10.0.0.99`.
  - AS1 administrators had already been notified.

- Received final KP confirmation through Uni:
  - AS2 independently confirmed the diagnosis.
  - AS2 resolver returns intended address `198.82.0.1`.
  - Traffic to bad address `10.0.0.99` loops/fails because it is private/non-advertised.
  - Status remains pending AS1 administrator approval/action.