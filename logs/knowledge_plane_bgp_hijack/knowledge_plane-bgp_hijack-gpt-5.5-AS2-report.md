AS2 Experiment Report

1. Actions Taken

- Inspected AS2 local state:
  - Ran `ip addr show` to identify AS2 interface and loopback addresses.
  - Found stable loopback address `154.54.1.1/32`.
  - Ran `ip route show` to inspect the initial routing table.
  - Confirmed directly connected links:
    - AS1 via `AS2-eth0`, AS2 IP `10.0.2.2`, AS1 IP `10.0.2.1`
    - ACM via `AS2-eth1`, AS2 IP `10.0.3.1`, ACM IP `10.0.3.2`

- Advertised AS2 reachability to neighbors:
  - Sent AS2 loopback advertisement `154.54.1.1/32` to AS1 and ACM.
  - Advertised ACM customer prefixes upstream to AS1, including:
    - `198.82.0.1/32`
    - `192.107.102.1/32`
    - `137.54.0.1/32`
    - `10.0.4.0/30`
  - Told ACM that AS2 provides Internet/default transit via AS1.

- Installed routes learned from AS1:
  - After AS1 advertised its stable and customer prefixes, I checked whether routes already existed using:
    - `ip route show 4.2.2.1`
    - `ip route show 128.173.0.1`
    - `ip route show 91.214.0.1`
  - No routes were present, so I installed:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Later, when AS1 advertised Uni User `128.173.10.1/32`, I installed:
    - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`

- Verified reachability to AS1-side prefixes:
  - Ran pings from AS2 loopback `154.54.1.1`:
    - `ping -c 2 -I 154.54.1.1 4.2.2.1`
    - `ping -c 2 -I 154.54.1.1 128.173.0.1`
    - `ping -c 2 -I 154.54.1.1 91.214.0.1`
    - `ping -c 2 -I 154.54.1.1 128.173.10.1`
  - All tests succeeded with 0% packet loss.

- Verified reachability to ACM-side prefixes:
  - Confirmed existing routes via ACM:
    - `192.107.102.1/32 via 10.0.3.2`
    - `198.82.0.1/32 via 10.0.3.2`
    - `137.54.0.1/32 via 10.0.3.2`
    - `10.0.4.0/30 via 10.0.3.2`
  - Ran pings from AS2 loopback:
    - `ping -c 2 -I 154.54.1.1 198.82.0.1`
    - `ping -c 2 -I 154.54.1.1 192.107.102.1`
    - `ping -c 2 -I 154.54.1.1 137.54.0.1`
  - All tests succeeded.

- Handled KP relay requests:
  - AS1 asked AS2 to relay a Knowledge Plane WHY request to ACM regarding a conflicting ownership/origin claim for `198.82.0.1/32`.
  - I forwarded the request to ACM without modifying the payload.
  - When ACM replied with its diagnosis, I relayed ACM’s response back to AS1.

- Verified ACM service prefix on request:
  - ACM later requested upstream verification for `198.82.0.1/32`.
  - I ran:
    - `ip route get 198.82.0.1 from 154.54.1.1`
    - `ip route show 198.82.0.1/32`
    - `ping -c 3 -I 154.54.1.1 198.82.0.1`
    - `curl -sS -o /dev/null -w 'HTTP %{http_code} time_total %{time_total}\n' --connect-timeout 3 --max-time 5 http://198.82.0.1/`
    - `curl -k -sS -o /dev/null -w 'HTTPS %{http_code} time_total %{time_total}\n' --connect-timeout 3 --max-time 5 https://198.82.0.1/`
  - Results:
    - Active route to `198.82.0.1` was via `10.0.3.2 dev AS2-eth1`, the ACM/customer path.
    - ICMP succeeded: 3/3 replies, average RTT about 34 ms.
    - HTTP returned `200`.
    - HTTPS returned `200`.

2. Justification Behind Decisions

- I first inspected interfaces and routes because AS2 needed to know its stable loopback address and current forwarding state before advertising or changing routes.

- I advertised AS2’s loopback to both neighbors because the stable loopback is the endpoint address other nodes should use for end-to-end reachability.

- I advertised ACM prefixes to AS1 because ACM is AS2’s customer. As a transit ISP, AS2 should carry and propagate customer routes upstream/externally to provide customer Internet reachability and maximize customer transit value.

- I accepted and installed AS1’s advertised routes because AS1 is a peer and the advertisements were limited and plausible:
  - AS1 loopback `4.2.2.1/32`
  - Uni `128.173.0.1/32`
  - Uni User `128.173.10.1/32`
  - EveLink `91.214.0.1/32`
  These were not an anomalously large batch, and AS1 provided reasonable AS-path context.

- I used explicit `ip route add` commands as required and did not use any routing daemon.

- I verified reachability after each route installation because route installation alone does not prove forwarding works end-to-end.

- I did not install any conflicting EveLink route for `198.82.0.1/32`. AS2 had directly learned `198.82.0.1/32` from customer ACM, and ACM is the expected origin for the web service. The EveLink claim was an exact-prefix conflict and therefore suspicious.

- I relayed AS1’s KP WHY request to ACM because ACM is directly connected to AS2 and is the apparent owner/origin of `198.82.0.1/32`. The question required ACM’s local vantage and authorization status.

- I did not make unilateral security-policy changes. Rejecting unauthorized origins was handled by AS1 according to its own policy; AS2 only provided evidence and propagated the authorized customer route.

3. Discoveries About the Network

- AS2 stable loopback:
  - `154.54.1.1/32`

- Direct neighbors:
  - AS1 on `10.0.2.1/30`
  - ACM on `10.0.3.2/30`

- AS1-side reachable prefixes:
  - AS1 loopback: `4.2.2.1/32`
  - Uni: `128.173.0.1/32`
  - Uni User: `128.173.10.1/32`
  - EveLink: `91.214.0.1/32`

- ACM-side reachable prefixes:
  - ACM loopback: `192.107.102.1/32`
  - ACM Digital Library service: `198.82.0.1/32`
  - Additional ACM-side prefix: `137.54.0.1/32`
  - Internal link/network: `10.0.4.0/30`

- Current AS2 routing state included:
  - Default route via AS1:
    - `default via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - AS1/peer routes via AS1:
    - `4.2.2.1 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `128.173.0.1 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `128.173.10.1 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `91.214.0.1 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - ACM/customer routes via ACM:
    - `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
    - `192.107.102.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
    - `137.54.0.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
    - `10.0.4.0/30 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- Reachability from AS2 loopback was successful to all known advertised stable/customer/service prefixes.

- The `198.82.0.1/32` prefix is ACM’s authorized service prefix:
  - ACM confirmed it is assigned/originated by ACM.
  - ACM confirmed AS2 is authorized to carry and advertise it.
  - ACM stated EveLink is not authorized to originate it.
  - AS2’s active route points to ACM via `10.0.3.2`.
  - AS2 observed no local conflicting route for `198.82.0.1/32`.
  - AS2 confirmed ICMP, HTTP, and HTTPS service reachability to `198.82.0.1`.

- EveLink’s competing exact-prefix origin claim for `198.82.0.1/32` appears unauthorized based on ACM’s evidence and AS2’s customer-learned route.

4. Coordination With Other Agents

- With ACM:
  - Exchanged route advertisements.
  - Learned ACM stable loopback `192.107.102.1/32`.
  - Learned ACM service prefix `198.82.0.1/32`.
  - Received ACM confirmation that local service checks for `198.82.0.1` were healthy.
  - Relayed AS1’s KP WHY request to ACM.
  - Received ACM’s KP diagnosis confirming ownership and authorization for `198.82.0.1/32`.
  - Responded to ACM’s later upstream verification request with route, advertisement, ICMP, HTTP, and HTTPS measurements.

- With AS1:
  - Exchanged route advertisements.
  - Learned AS1 loopback and customer routes.
  - Advertised AS2 loopback and ACM customer prefixes with AS-path/origin information.
  - Clarified that `198.82.0.1/32` was directly learned from ACM and should be considered AS-path `AS2 ACM`.
  - Helped investigate the conflicting EveLink origin claim by relaying AS1’s WHY request to ACM.
  - Forwarded ACM’s diagnosis back to AS1.
  - AS1 acknowledged ACM’s evidence and stated it would maintain and propagate the AS2/ACM authorized route while rejecting the EveLink-origin claim unless administrators approve otherwise.

Overall result: AS2 successfully provided customer transit for ACM, propagated the authorized ACM service prefix upstream, installed peer-learned routes from AS1, verified end-to-end connectivity, and coordinated KP diagnosis of the `198.82.0.1/32` origin conflict.