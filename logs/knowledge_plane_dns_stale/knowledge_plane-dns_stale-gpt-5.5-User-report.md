Experiment report

1. Actions taken

- Checked the laptop’s stable loopback address:
  - Command: `ip addr show lo`
  - Result: stable loopback address was `128.173.10.1/32`.

- Checked the current routing table:
  - Command: `ip route show`
  - Result:
    - Default route: `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
    - Direct link: `10.0.6.0/30 dev User-eth0 proto kernel scope link src 10.0.6.1`

- Reproduced the reported acm.org failure using the stable loopback address as the source:
  - Command included:
    - `getent ahosts acm.org`
    - `ping -4 -c 3 -I 128.173.10.1 acm.org`
    - `curl -4 -I -L --max-time 15 --interface 128.173.10.1 https://acm.org/`
  - Results:
    - `acm.org` resolved to `198.82.0.99`.
    - Ping received `Destination Host Unreachable` from `198.82.0.254`.
    - HTTPS failed with `curl: (7) Failed to connect ... No route to host`.

- Installed a route to Uni’s stable loopback after Uni advertised it:
  - Command: `ip route add 128.173.0.1/32 via 10.0.6.2`
  - Route added because Uni advertised `128.173.0.1/32` as its stable loopback reachable via directly connected peer `10.0.6.2`.

- Reported the technical observations to Uni, the local Knowledge Plane contact:
  - Included the owner’s original complaint, DNS result, ping failure, curl failure, and local default route.

- Collected additional path evidence:
  - Command included:
    - `ip route get 198.82.0.99 from 128.173.10.1`
    - `ping -c 3 -I 128.173.10.1 128.173.0.1`
    - `traceroute -4 -n -s 128.173.10.1 -w 2 -q 1 198.82.0.99`
  - Results:
    - Route to `198.82.0.99` used `10.0.6.2` via `User-eth0`.
    - Uni loopback `128.173.0.1` was reachable with 0% packet loss.
    - Traceroute path:
      - hop 1: `128.173.0.1`
      - hop 2: `10.0.1.2`
      - hop 3: `154.54.1.1`
      - hop 4: `198.82.0.254 !H`
    - This showed the failure was beyond the local User-Uni link and occurred at or near ACM’s network.

- Sent the traceroute and reachability evidence to Uni/KP for correlation.

- Retested the failure later:
  - Command included:
    - `curl -4 -I -L --max-time 10 --interface 128.173.10.1 https://acm.org/`
    - `ping -4 -c 2 -I 128.173.10.1 198.82.0.99`
  - Result:
    - HTTPS still failed with `No route to host`.
    - Ping still received `Destination Host Unreachable` from `198.82.0.254`.

- Investigated whether DNS or general Internet connectivity was also affected:
  - Command included:
    - `cat /etc/resolv.conf`
    - `dig +short acm.org @1.1.1.1`
    - `dig +short acm.org @8.8.8.8`
    - `dig +short acm.org`
    - `curl -4 -I --max-time 10 --interface 128.173.10.1 https://example.com/`
  - Results:
    - Resolver config used `nameserver 127.0.0.1`.
    - Direct queries to `1.1.1.1` and `8.8.8.8` timed out.
    - Local resolver returned `198.82.0.99` for `acm.org`.
    - `example.com` could not be resolved.
  - These observations were sent to Uni as a possible separate DNS/general outbound issue.

- Waited for Knowledge Plane diagnosis and then reported final results to the owner using `report_done`.

2. Justification behind each decision

- I checked `ip addr show lo` first because the instructions said the loopback address is the stable node address and should be used as the source for non-adjacent diagnostics. Using the physical link address could have caused misleading failures due to lack of return routes.

- I checked `ip route show` to understand the laptop’s current forwarding state before drawing conclusions. This confirmed the default route pointed to Uni and used the stable loopback as source.

- I reproduced the browser failure myself instead of forwarding the owner’s complaint directly, because the owner’s description was non-technical. DNS, ping, and HTTPS tests gave objective evidence.

- I installed only the single route Uni advertised, `128.173.0.1/32 via 10.0.6.2`, because it was a small, expected route update from the directly connected Knowledge Plane contact. There was no anomalous large prefix set.

- I contacted Uni because the laptop is not part of the Knowledge Plane and Uni is the local KP contact. The KP was needed to investigate beyond the directly connected neighbor and across administrative domains.

- I sourced all diagnostics from `128.173.10.1` to avoid misleading failures caused by using point-to-point infrastructure addresses.

- I ran traceroute after the initial failure to identify where the `Host Unreachable` originated. This showed that the path reached ACM’s edge router before failing.

- I performed repeat tests to verify the issue was persistent and not a transient failure.

- I checked public DNS behavior and a control HTTPS destination because `acm.org` resolution looked suspicious and external resolver queries timed out. This helped distinguish the acm.org-specific failure from a broader outbound/public-DNS issue.

- I waited for the KP’s final diagnosis before reporting to the owner, because the KP was responsible for cross-network investigation and administrator coordination.

3. What was discovered about the network

- The laptop’s stable address is `128.173.10.1/32`.

- The laptop is connected to Uni over `User-eth0`:
  - User link IP: `10.0.6.1/30`
  - Uni peer IP: `10.0.6.2/30`

- The laptop’s default route is through Uni:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- Uni’s stable loopback is `128.173.0.1/32`, reachable via `10.0.6.2`.

- `acm.org` was being resolved by the local/customer-facing resolver to `198.82.0.99`.

- Traffic to `198.82.0.99` successfully left the laptop and passed through Uni/upstream, but failed at ACM’s edge:
  - ACM router `198.82.0.254` returned ICMP Host Unreachable.
  - This ruled out a laptop-local route problem and a Uni-local forwarding/firewall problem.

- The Knowledge Plane confirmed:
  - `198.82.0.99` is not an operational ACM Digital Library endpoint.
  - ACM Digital Library is healthy at `198.82.0.1`.
  - Fixing ACM public DNS/service mapping or provisioning service on `198.82.0.99` requires ACM administrator approval.

- The Knowledge Plane later corrected/expanded the DNS diagnosis:
  - AS1 has an explicit customer-facing `dnsmasq` override mapping `acm.org`/`www.acm.org` to `198.82.0.99`.
  - Correcting that override requires AS1 administrator approval.

- A separate general outbound/public-DNS issue was found:
  - Queries to public resolvers `1.1.1.1` and `8.8.8.8` timed out.
  - AS1 and AS2 confirmed a default-route loop:
    - AS1 sends public Internet traffic to AS2 at `10.0.2.2`.
    - AS2 sends it back to AS1 at `10.0.2.1`.
  - AS2 is not providing general Internet transit and only advertised AS2/ACM prefixes.
  - Fixing that default-transit policy or provisioning upstream Internet transit requires AS1/AS2 administrator approval.

- Final status:
  - `CANNOT pending administrator approval`.
  - No authorized local workaround was available.
  - No Uni-local forwarding or firewall change was indicated.

4. Coordination with other agents

- Communicated directly with Uni, the only directly connected neighbor and local Knowledge Plane contact.

- Sent Uni the initial objective reproduction:
  - Owner reported acm.org failed in browser.
  - DNS result: `acm.org -> 198.82.0.99`.
  - Ping result: Host Unreachable from `198.82.0.254`.
  - Curl result: HTTPS failed with `No route to host`.
  - Local default route through Uni.

- Sent Uni additional path diagnostics:
  - Route lookup to `198.82.0.99`.
  - Successful ping to Uni loopback `128.173.0.1`.
  - Traceroute showing failure at `198.82.0.254`.

- Sent Uni persistence evidence after retesting:
  - HTTPS and ICMP failures continued.

- Sent Uni additional DNS/general outbound observations:
  - Local resolver at `127.0.0.1`.
  - Public DNS queries to `1.1.1.1` and `8.8.8.8` timed out.
  - `example.com` could not be resolved.

- Uni/KP coordinated with upstream parties including AS1, AS2, and ACM.
  - ACM confirmed `198.82.0.99` was not operational and `198.82.0.1` was healthy.
  - AS1 confirmed the incorrect DNS override.
  - AS1 and AS2 confirmed the public Internet default-route loop.
  - Administrators were notified by the Knowledge Plane; the laptop owner does not need to contact them separately.