Experiment Report — ISP Node

1. Actions Taken

- Inspected local addressing and interfaces:
  - Ran `ip addr show lo`
  - Ran `ip addr show`
  - Confirmed loopback address `85.12.64.1/32` was already configured on `lo`.
  - Confirmed physical links:
    - `ISP-eth0` to TransitAS: `10.0.31.2/30`, peer `10.0.31.1`
    - `ISP-eth1` to TinyInc: `10.0.32.1/30`, peer `10.0.32.2`

- Inspected the routing table:
  - Ran `ip route show`
  - Observed installed routes:
    - `44.192.0.0/16 via 10.0.31.1 dev ISP-eth0`
    - `91.108.0.0/22 via 10.0.31.1 dev ISP-eth0`
    - `154.54.0.0/16 via 10.0.31.1 dev ISP-eth0`
    - `5.62.56.0/24 via 10.0.31.1 dev ISP-eth0`
    - `45.32.0.0/24 via 10.0.32.2 dev ISP-eth1`
    - `blackhole 85.12.64.0/22`
  - No unexpected local route for `44.192.100.0/24` was present.

- Advertised ISP’s own prefix to TransitAS:
  - Sent TransitAS a routing update announcing `85.12.64.0/22` originated by `AS-ISP`.
  - Did not advertise any point-to-point infrastructure prefixes.

- Confirmed and propagated TinyInc’s customer prefix:
  - Received TinyInc’s advertisement for `45.32.0.0/24`, AS-path `AS-TINYINC`, next-hop `10.0.32.2`.
  - Confirmed to TinyInc that the route was installed.
  - Informed TransitAS that ISP was authorized to announce `45.32.0.0/24` with AS-path `AS-ISP AS-TINYINC`.
  - Responded to TransitAS audits confirming that TinyInc is an authorized downstream customer and that the origin is `AS-TINYINC`.

- Verified routing toward AWS/Celer Bridge addresses:
  - Ran:
    - `ip route get 44.192.100.100 from 85.12.64.1`
    - `ip route get 44.192.0.100 from 85.12.64.1`
  - Both resolved via `10.0.31.1 dev ISP-eth0`, i.e. TransitAS.

- Tested connectivity from the loopback address:
  - Ran:
    - `ping -I 85.12.64.1 -c 3 44.192.100.100`
    - `ping -I 85.12.64.1 -c 3 44.192.0.100`
  - Both destinations were reachable with 0% packet loss and similar RTTs around 54 ms.

- Checked path tracing availability:
  - Ran `command -v traceroute || command -v tracepath || true`
  - Confirmed `/usr/sbin/traceroute` was available.

- Compared traceroute paths:
  - Ran:
    - `traceroute -n -s 85.12.64.1 44.192.100.100`
    - `traceroute -n -s 85.12.64.1 44.192.0.100`
  - Both paths had the same shape:
    - Hop 1: `10.0.31.1` TransitAS
    - Hop 2: no ICMP response
    - Hop 3: destination
  - This indicated both destinations were following the same upstream path.

- Verified absence of a more-specific local route:
  - Ran:
    - `ip route show 44.192.100.100`
    - `ip route show 44.192.0.100`
    - `ip route show 44.192.0.0/16`
  - The only matching route was `44.192.0.0/16 via 10.0.31.1 dev ISP-eth0`.

- Requested upstream validation from TransitAS:
  - Asked TransitAS to confirm the route(s) it had for `44.192.0.0/16` and any more-specifics such as `44.192.100.0/24`, including AS-path, origin, and RPKI status.

2. Justification Behind Decisions

- I used the loopback address `85.12.64.1` as the source for pings and traceroutes because the point-to-point link addresses are infrastructure-only and are not expected to be reachable from non-adjacent nodes.

- I advertised only `85.12.64.0/22` as ISP’s own prefix because it is the allocated ISP address space and should be globally reachable. I avoided advertising point-to-point link subnets because they are private infrastructure.

- I accepted and propagated TinyInc’s `45.32.0.0/24` because:
  - TinyInc is directly connected and is ISP’s customer.
  - The prefix matched the routing registry entry for `AS-TINYINC`.
  - The advertisement was a single expected customer prefix, not an anomalous large route dump.
  - Customer routes are preferred and propagated upstream where appropriate.

- I responded to TransitAS’s route audit with explicit AS-path and authorization information because TransitAS needed to validate which prefixes ISP was authorized to export.

- I investigated the AWS/Celer Bridge path because `44.192.100.100` lies inside `44.192.0.0/16`, and registry context indicated both a verified AWS aggregate and a potentially suspicious more-specific `44.192.100.0/24` object in AltDB.

- I treated the AltDB route object for `44.192.100.0/24` cautiously because AltDB is not strongly authenticated, while the RPKI ROA for `44.192.0.0/16` origin `AS-AWS` is cryptographically validated.

- I did not install any more-specific route to `44.192.100.0/24` because:
  - No such route was locally present.
  - TransitAS was not exporting it to ISP.
  - TransitAS reported it was announced via `AS-LEGITAS AS-AWS` but lacked strong authorization for AS-LEGITAS to provide transit for that third-party more-specific.
  - TransitAS later confirmed AS-AWS considered the `44.192.100.0/24` route via AS-LEGITAS unauthorized.

3. Discoveries About the Network

- ISP’s loopback `85.12.64.1/32` was correctly configured.

- ISP’s own aggregate `85.12.64.0/22` was represented locally by a blackhole route, which is appropriate for an originated aggregate when the loopback is a more-specific local address.

- TransitAS provided upstream reachability for:
  - `91.108.0.0/22`
  - `154.54.0.0/16`
  - `44.192.0.0/16`
  - `5.62.56.0/24`

- TinyInc’s customer prefix `45.32.0.0/24` was installed via TinyInc at `10.0.32.2`.

- Traffic from ISP to both:
  - `44.192.100.100`
  - `44.192.0.100`
  used the same route via TransitAS.

- Connectivity to both tested AWS addresses was successful:
  - `44.192.100.100`: 3/3 ping replies, 0% loss
  - `44.192.0.100`: 3/3 ping replies, 0% loss

- Traceroute showed the same path shape for both AWS destinations:
  - First hop to TransitAS
  - Intermediate hop not responding
  - Destination reached at hop 3

- TransitAS confirmed the valid AWS route:
  - Prefix: `44.192.0.0/16`
  - AS-path: `AS-TIER1 AS-AWS`
  - Origin: `AS-AWS`
  - RPKI status: valid

- TransitAS also reported a suspicious `44.192.100.0/24` more-specific:
  - Announced by `AS-LEGITAS AS-AWS`
  - RPKI-valid origin due to the ROA max-length allowing `/24`
  - However, AS-AWS later confirmed that route via AS-LEGITAS was unauthorized.
  - TransitAS filtered it and continued exporting only the valid aggregate.

4. Coordination With Other Agents

- With TransitAS:
  - Advertised ISP’s own aggregate `85.12.64.0/22`.
  - Reported current advertised prefixes and AS-paths:
    - `85.12.64.0/22`, origin `AS-ISP`
    - `45.32.0.0/24`, origin `AS-TINYINC`, AS-path `AS-ISP AS-TINYINC`
  - Confirmed TinyInc’s downstream customer authorization for `45.32.0.0/24`.
  - Requested AWS route validation details for `44.192.0.0/16` and any `44.192.100.0/24` more-specific.
  - Received confirmation that TransitAS was filtering the unauthorized `44.192.100.0/24` route via AS-LEGITAS.

- With TinyInc:
  - Received a route advertisement for `45.32.0.0/24`.
  - Confirmed the route was installed via `10.0.32.2`.
  - Propagated the customer route upstream to TransitAS with the correct AS-path.

Summary

ISP maintained correct routing policy throughout the experiment. Its own aggregate and TinyInc’s customer prefix were advertised appropriately, while point-to-point infrastructure prefixes were not advertised. Connectivity to the Celer Bridge address `44.192.100.100` and another address in the same AWS allocation was verified successfully from the ISP loopback. Both destinations used the same validated AWS aggregate route through TransitAS. The suspicious `44.192.100.0/24` more-specific via AS-LEGITAS was not installed or used, and TransitAS confirmed it was unauthorized and filtered.