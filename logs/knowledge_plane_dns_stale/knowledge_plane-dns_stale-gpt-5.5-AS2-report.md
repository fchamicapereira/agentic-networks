Experiment report for AS2

1. Actions taken

- Performed a local AS2 audit before escalating the KP WHY request.
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Confirmed AS2 loopback address was `154.54.1.1/32`.
  - Confirmed interfaces were up:
    - `AS2-eth0` to AS1: `10.0.2.2/30`
    - `AS2-eth1` to ACM: `10.0.3.1/30`
  - Confirmed AS2 had a route for ACM’s prefix:
    - `198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- Tested direct connectivity from AS2 to ACM’s adjacent router.
  - Ran:
    - `ping -c 3 -I 10.0.3.1 10.0.3.2`
  - Result: successful, 0% packet loss.

- Tested reachability to ACM service addresses from AS2’s stable loopback address.
  - Ran:
    - `ping -c 3 -I 154.54.1.1 198.82.0.1`
    - `ping -c 3 -I 154.54.1.1 198.82.0.99`
  - Result:
    - `198.82.0.1` was reachable.
    - `198.82.0.99` returned ICMP Destination Host Unreachable from `198.82.0.254`.

- Sent a KP WHY request to ACM.
  - Asked ACM to audit whether `198.82.0.99` was an expected service address and whether there was any local routing, host, ARP, or service issue.

- Audited AS2’s recursive DNS resolver for `acm.org`.
  - Ran:
    - `dig +short @154.54.1.1 acm.org A`
    - Fallbacks were included but not needed:
      - `dig +short @127.0.0.1 acm.org A`
      - `nslookup acm.org 154.54.1.1`
    - Also checked DNS listeners with:
      - `ss -lunpt | grep ':53' || true`
  - Result:
    - AS2 resolver returned `198.82.0.1`.
    - DNS service was listening on `154.54.1.1:53` and `127.0.0.1:53`.

- Reported the final diagnosis back to AS1.
  - Informed AS1 that AS2 transit was healthy, ACM’s valid service endpoint was healthy, and the failure was due to use of an invalid or stale destination address, `198.82.0.99`.

2. Justification behind each decision

- I first audited AS2 locally because KP policy requires local investigation before escalating. The symptoms could have been caused by an AS2 route, interface, or forwarding issue, so I checked local addresses, interface state, and routing table.

- I sourced non-adjacent diagnostic traffic from AS2’s loopback address `154.54.1.1` because the testbed policy states that loopback addresses are the stable routable addresses. Using point-to-point link addresses for remote diagnostics could have caused misleading reply failures.

- I tested the direct AS2-to-ACM link before asking ACM to investigate because a broken customer-facing link would have been AS2’s responsibility or at least visible from AS2.

- I compared reachability to `198.82.0.1` and `198.82.0.99` because AS1 had already reported that `198.82.0.1` worked while `198.82.0.99` failed. Reproducing both from AS2 helped distinguish a general ACM prefix reachability problem from a host-specific issue.

- I escalated to ACM only after confirming AS2 could route to the ACM prefix and reproduce the host-unreachable response. Since `198.82.0.99` lies inside ACM’s prefix, only ACM could definitively confirm whether the host was expected to exist.

- I checked AS2’s recursive DNS resolver because AS2 operates a resolver and the reported symptom involved `acm.org` resolving or being used as `198.82.0.99`. It was important to verify whether AS2 was serving stale DNS data.

- I did not configure or modify any routes. The routing table was already consistent with the expected topology, and the issue was not a routing failure.

3. What was discovered about the network

- AS2’s loopback address is `154.54.1.1/32`.

- AS2’s physical links were healthy:
  - AS2 to AS1 over `10.0.2.0/30`
  - AS2 to ACM over `10.0.3.0/30`

- AS2 had correct routing toward ACM:
  - `198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- AS2 could reach ACM’s valid web service address:
  - `198.82.0.1` was reachable from AS2 loopback.

- AS2 and AS1 both observed the same failure for:
  - `198.82.0.99`
  - The failure was ICMP Destination Host Unreachable from `198.82.0.254`.

- ACM confirmed:
  - `198.82.0.1` is the valid and healthy ACM Digital Library service address.
  - `198.82.0.99` is not an expected or configured ACM service address.
  - There is no reachable ACM host at `198.82.0.99`.

- AS2’s DNS resolver returned the correct address for `acm.org`:
  - `198.82.0.1`
  - It was not returning the stale or invalid address `198.82.0.99`.

- Final diagnosis:
  - There was no AS2 transit fault.
  - There was no ACM routing or service fault for the valid endpoint.
  - The reported failure was caused by AS1, Uni, or the client using a wrong or stale address for `acm.org`: `198.82.0.99` instead of `198.82.0.1`.

4. Coordination with other agents

- Received a KP WHY request from AS1.
  - AS1 reported that Uni customer `128.173.10.1` could not reach `acm.org / 198.82.0.99`.
  - AS1 also reported that it could reach `198.82.0.1` but not `198.82.0.99`.

- Sent a KP WHY request to ACM.
  - Asked ACM to confirm whether `198.82.0.99` was a valid service endpoint and to check local host/routing state.

- Received ACM’s diagnosis.
  - ACM confirmed that `198.82.0.99` was not valid and that the actual ACM service was healthy at `198.82.0.1`.

- Sent final KP diagnosis back to AS1.
  - Reported that AS2 and ACM were healthy.
  - Recommended that AS1, Uni, or the affected client audit DNS cache or local configuration and correct stale use of `198.82.0.99` to `198.82.0.1`.

No routing rules were added or deleted during the experiment. No firewall, ACL, or security policy changes were made.