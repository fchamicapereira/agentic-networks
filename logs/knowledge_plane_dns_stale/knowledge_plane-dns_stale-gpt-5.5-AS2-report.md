Experiment report for AS2

1. Actions taken

- Inspected local interface and routing state:
  - Ran:
    - `ip addr show`
    - `ip route show`
  - Identified AS2 loopback/stable address as `154.54.1.1/32`.
  - Confirmed physical interfaces:
    - `AS2-eth0` to AS1: AS2 `10.0.2.2/30`, AS1 `10.0.2.1/30`
    - `AS2-eth1` to ACM: AS2 `10.0.3.1/30`, ACM `10.0.3.2/30`
  - Initial routes included a default route via AS1 and several ACM-related routes, including later-withdrawn `198.82.0.99/32` and `10.0.4.0/30`.

- Verified direct neighbor connectivity:
  - Ran:
    - `ping -c 2 -W 1 10.0.2.1`
    - `ping -c 2 -W 1 10.0.3.2`
  - Both AS1 and ACM directly connected next hops were reachable.

- Exchanged routing information with AS1 and ACM:
  - Advertised AS2 stable loopback `154.54.1.1/32`.
  - Initially informed AS1 and ACM of locally known ACM-related routes.
  - Requested authoritative prefix advertisements from both neighbors.

- Installed AS1 route:
  - After AS1 advertised its loopback, ran:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - This allowed AS2 and ACM transit reachability to AS1’s stable address.

- Propagated confirmed ACM prefixes to AS1:
  - ACM authoritatively advertised:
    - `198.82.0.254/32` — ACM loopback
    - `198.82.0.1/32` — ACM Digital Library service
  - Sent AS1 a route update advertising these prefixes via AS2 next hop `10.0.2.2`.

- Propagated AS1/customer prefixes to ACM:
  - AS1 advertised:
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`
  - Installed routes via AS1:
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Confirmed routes with `ip route show`.
  - Advertised these AS1-side prefixes to ACM for customer transit.

- Withdrew non-authoritative ACM/internal prefixes:
  - ACM clarified that it only authoritatively advertised `198.82.0.254/32` and `198.82.0.1/32`.
  - ACM stated:
    - `198.82.0.99/32` was not a reachable ACM service prefix.
    - `10.0.4.0/30` was an internal point-to-point infrastructure link, not Internet-advertised.
  - Removed them locally:
    - `ip route del 198.82.0.99/32`
    - `ip route del 10.0.4.0/30`
  - Sent AS1 a route withdrawal for both prefixes.

- Verified ACM service reachability from AS2:
  - Ran from AS2 stable loopback source:
    - `ping -c 2 -W 1 -I 154.54.1.1 198.82.0.254`
    - `ping -c 2 -W 1 -I 154.54.1.1 198.82.0.1`
    - `curl -sS -o /dev/null -w '%{http_code}\n' --interface 154.54.1.1 --max-time 3 http://198.82.0.1/`
  - Results:
    - ICMP to ACM loopback succeeded.
    - ICMP to ACM web service succeeded.
    - HTTP to `http://198.82.0.1/` returned `200`.

- Requested AS1-side verification of ACM service:
  - Asked AS1 to test from stable source `4.2.2.1`:
    - ICMP to `198.82.0.254`
    - ICMP to `198.82.0.1`
    - HTTP to `http://198.82.0.1/`
  - AS1 later confirmed all tests succeeded and HTTP returned 200.

- Verified AS1-side reachability from AS2:
  - Ran:
    - `ping -c 2 -W 1 -I 154.54.1.1 4.2.2.1`
    - `ping -c 2 -W 1 -I 154.54.1.1 128.173.0.1`
    - `ping -c 2 -W 1 -I 154.54.1.1 128.173.10.1`
    - `ping -c 2 -W 1 -I 154.54.1.1 91.214.0.1`
  - All tested AS1/AS1-customer prefixes were reachable from AS2’s stable source.

- Investigated DNS inconsistency:
  - AS1 reported its resolver returned stale `acm.org A = 198.82.0.99`.
  - Checked AS2 resolver:
    - `dig +short @154.54.1.1 acm.org A`
  - AS2 resolver correctly returned:
    - `198.82.0.1`
  - Also checked AS1 resolver from AS2:
    - `dig +short @4.2.2.1 -b 154.54.1.1 acm.org A`
  - AS1 resolver returned:
    - `198.82.0.99`

- Investigated and fixed AS1/AS2 routing loop for withdrawn `198.82.0.99/32`:
  - AS1 reported traffic to withdrawn `198.82.0.99` was following AS1 default to AS2, then looping back toward AS1 via AS2’s default route.
  - Audited AS2 forwarding decision:
    - `ip route show 198.82.0.99/32`
    - `ip route get 198.82.0.99`
    - `ip route get 198.82.0.99 from 4.2.2.1 iif AS2-eth0`
  - Confirmed that without a specific route, traffic to `198.82.0.99` fell through to AS2’s default via AS1 `10.0.2.1`.
  - Installed a local blackhole route:
    - `ip route add blackhole 198.82.0.99/32`
  - Verified:
    - `ip route show 198.82.0.99/32`
    - `ping -c 1 -W 1 -I 154.54.1.1 198.82.0.99`
  - Result:
    - Route showed `blackhole 198.82.0.99`.
    - Ping failed locally as expected, preventing the route loop.

- Relayed ACM’s DNS FIX request to AS1:
  - ACM requested AS1 investigate/flush or correct stale resolver behavior.
  - Forwarded ACM’s request to AS1.
  - Continued follow-up with AS1 on resolver status.

- Reported status to ACM:
  - Informed ACM that:
    - AS2 resolver correctly returned `198.82.0.1`.
    - AS1 resolver still returned stale `198.82.0.99`.
    - Direct IP HTTP service at `198.82.0.1` remained healthy.
    - AS2 had blackholed `198.82.0.99/32` to stop loops.
    - AS1 could not autonomously change its customer-facing resolver configuration without administrator approval.

2. Justification behind decisions

- Used loopback source address for non-adjacent diagnostics:
  - AS2’s loopback `154.54.1.1/32` is the stable routable address.
  - Physical link addresses are point-to-point infrastructure addresses and may not be reachable from remote nodes.
  - Therefore diagnostic traffic to non-adjacent destinations was sourced from `154.54.1.1`.

- Installed only small, explicit, neighbor-advertised prefixes:
  - AS1 advertised a small set of prefixes consistent with its role.
  - ACM clarified its authoritative prefixes.
  - No large or suspicious bulk route update was accepted.

- Removed `198.82.0.99/32` and `10.0.4.0/30` after ACM clarification:
  - ACM is the customer and authoritative source for its own prefixes.
  - It explicitly stated those were not Internet-advertised service prefixes.
  - Continuing to propagate them would have created incorrect reachability and possible blackholing or loops.

- Propagated customer ACM routes to peer AS1:
  - ACM is AS2’s customer and pays AS2 for transit.
  - Advertising ACM’s legitimate service prefixes to AS1 supports customer reachability and AS2’s transit role.

- Propagated AS1 routes to ACM:
  - ACM is AS2’s customer and should receive transit to reachable external prefixes through AS2.
  - Providing these routes supports customer Internet access.

- Installed a blackhole for `198.82.0.99/32`:
  - After withdrawal, `198.82.0.99` was not owned or reachable via ACM.
  - AS2’s default route caused traffic for this withdrawn address to be sent back to AS1, producing a loop.
  - A host-specific blackhole was a local, low-risk, reversible routing fix using `ip route`.
  - It prevented AS2 from returning invalid traffic to AS1 while leaving the confirmed ACM service `198.82.0.1` unaffected.

- Did not modify AS1 DNS resolver:
  - AS1’s resolver behavior is outside AS2’s administrative authority.
  - AS1 later found a dnsmasq static override:
    - `--local=/acm.org/ --address=/acm.org/198.82.0.99`
  - Changing that would affect customer-facing recursive DNS behavior and cross an administrative/security boundary.
  - Per policy, this requires AS1 administrator approval and could not be applied by AS2 or autonomously by AS1’s KP agent.

3. Discoveries about the network

- AS2 local state:
  - Stable loopback/resolver address is `154.54.1.1/32`.
  - AS2 peers with AS1 over `10.0.2.0/30`.
  - AS2 serves customer ACM over `10.0.3.0/30`.
  - AS2 default route points to AS1 via `10.0.2.1`.

- ACM authoritative prefixes:
  - Valid ACM prefixes:
    - `198.82.0.254/32` — ACM loopback
    - `198.82.0.1/32` — ACM Digital Library service
  - Invalid/non-advertised ACM-related prefixes:
    - `198.82.0.99/32`
    - `10.0.4.0/30`

- AS1 and AS1-customer prefixes:
  - AS1 loopback:
    - `4.2.2.1/32`
  - AS1 customer prefixes:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`

- ACM service health:
  - `198.82.0.1` was reachable by ICMP from AS2 and AS1.
  - HTTP to `http://198.82.0.1/` returned status `200`.
  - ACM also reported local health checks as successful.

- DNS state:
  - AS2 resolver at `154.54.1.1` correctly returned:
    - `acm.org A = 198.82.0.1`
  - AS1 resolver at `4.2.2.1` incorrectly returned:
    - `acm.org A = 198.82.0.99`
  - AS1 determined the cause was not stale cache but a static dnsmasq override:
    - `--local=/acm.org/ --address=/acm.org/198.82.0.99`

- Routing loop:
  - After `198.82.0.99/32` was withdrawn, traffic from AS1/Uni to `198.82.0.99` followed AS1 default to AS2.
  - AS2, lacking a specific route, used its default route back to AS1.
  - This caused AS1/AS2 loop symptoms and ICMP redirects.
  - Installing `blackhole 198.82.0.99/32` at AS2 stopped the loop.

4. Coordination with other agents

- With ACM:
  - Received authoritative ACM prefix advertisement.
  - Received clarification that `198.82.0.99/32` and `10.0.4.0/30` should not be advertised.
  - Reported AS2-side and AS1-side verification results for ACM reachability and HTTP service.
  - Relayed AS1’s DNS findings and CANNOT status back to ACM.
  - Kept ACM informed that direct service health was good but name-based access through AS1 DNS remained degraded.

- With AS1:
  - Exchanged loopback and customer route advertisements.
  - Advertised confirmed ACM prefixes to AS1.
  - Withdrew invalid ACM-related prefixes from AS1.
  - Requested AS1 external-vantage verification of ACM reachability and HTTP service.
  - Received confirmation that AS1 could reach `198.82.0.1` and `198.82.0.254`.
  - Investigated AS1’s report of a loop involving withdrawn `198.82.0.99`.
  - Reported AS2’s blackhole fix and requested re-verification.
  - Received AS1 confirmation that the loop/redirect symptoms stopped.
  - Forwarded ACM’s DNS FIX request to AS1.
  - Received AS1’s diagnosis that the stale DNS answer came from a static dnsmasq override.
  - Received AS1’s final CANNOT response indicating administrator approval is required before changing the resolver behavior.

Final status

AS2 completed all safe local routing and DNS actions. Correct ACM reachability is established through AS2, and the invalid `198.82.0.99` route loop has been mitigated with a blackhole route. The only unresolved problem is AS1’s resolver `4.2.2.1`, which still returns stale `acm.org A = 198.82.0.99` due to an AS1-managed static dnsmasq override. That fix remains pending AS1 administrator approval.