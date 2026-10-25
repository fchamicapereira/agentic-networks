Experiment report — AS1 KP investigation for Uni reachability to acm.org / 198.82.0.99

1. Actions taken

- Performed a local AS1 audit before escalating:
  - Ran:
    - `ip addr show lo`
    - `ip route show`
    - `ip link show AS1-eth0`
    - `ip link show AS1-eth1`
    - `ip link show AS1-eth2`
  - Confirmed AS1 loopback stable address is `4.2.2.1/32`.
  - Confirmed AS1 routes included:
    - `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `128.173.0.1 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - `91.214.0.1 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`
  - Confirmed AS1 interfaces to Uni, AS2, and EveLink were up.

- Tested reachability to the reported destination from AS1:
  - Ran:
    - `ping -c 3 -I 4.2.2.1 198.82.0.99`
  - Result:
    - Failed with `Destination Host Unreachable` from `198.82.0.254`.

- Tested AS1’s direct peer connectivity to AS2:
  - Ran:
    - `ping -c 3 10.0.2.2`
  - Result:
    - Successful replies from AS2 peer address `10.0.2.2`.

- Tested reachability to the known valid ACM web server:
  - Ran:
    - `ping -c 3 -I 4.2.2.1 198.82.0.1`
  - Result:
    - Successful replies from `198.82.0.1`.

- Escalated the issue to AS2 using a KP WHY request:
  - Asked AS2 to investigate ACM-facing reachability to `198.82.0.99`.
  - Included AS1 findings: AS1 local routes and interfaces were healthy, AS2 was reachable, and `198.82.0.1` worked while `198.82.0.99` failed.

- Audited AS1 DNS resolver behavior after AS2’s response:
  - Ran:
    - `dig +short @4.2.2.1 acm.org A || nslookup acm.org 4.2.2.1`
  - Result:
    - AS1 recursive resolver returned `198.82.0.99`.

- Identified the DNS resolver process:
  - Ran:
    - `ss -lunpt | grep ':53\\b' || true`
  - Found dnsmasq listening on:
    - `4.2.2.1:53`
    - `127.0.0.1:53`

- Investigated dnsmasq configuration:
  - Ran:
    - `ps -ef | grep '[d]nsmasq'`
    - `grep -R "198\\.82\\.0\\.99\\|acm\\.org\\|address=/\\|host-record" -n /etc /run /var 2>/dev/null | head -100`
  - Found AS1 dnsmasq was launched with:
    - `--addn-hosts=/etc/dnsmasq.d/acm.org.hosts`
  - Found stale static DNS override:
    - `/etc/dnsmasq.d/acm.org.hosts:1:# Pin acm.org to the DL frontend during ACM's migration (2025-11). Temporary.`
    - `/etc/dnsmasq.d/acm.org.hosts:2:198.82.0.99 acm.org www.acm.org`

- Reported the diagnosis back to Uni:
  - Explained that the root cause was AS1’s DNS resolver statically mapping `acm.org` and `www.acm.org` to stale/unreachable address `198.82.0.99`.
  - Reported that the valid ACM service address is `198.82.0.1`.
  - Returned `CANNOT` for the fix because changing resolver configuration affects customer DNS resolution and requires administrator approval.

2. Justification behind each decision

- I audited AS1 locally first because KP policy requires investigating local routing, interface state, and services before escalating to another domain.
- I sourced non-adjacent diagnostic traffic from AS1 loopback `4.2.2.1`, not from link addresses, because only loopback addresses are stable and routable back across the network.
- I tested `198.82.0.99` from AS1 to determine whether Uni’s symptom was reproducible upstream of Uni.
- I tested AS2 peer connectivity to verify that AS1’s direct upstream/peer path was functional.
- I tested `198.82.0.1` to distinguish between a general ACM reachability problem and a host-specific failure for `198.82.0.99`.
- I escalated to AS2 only after AS1 local routing and peer reachability appeared healthy and the failure seemed to be beyond AS1’s transit forwarding path.
- I audited AS1 DNS after AS2 reported that `198.82.0.99` was not a valid ACM service address and that AS2’s resolver returned `198.82.0.1`. This made a stale DNS mapping at AS1, Uni, or the client the likely cause.
- I did not modify `/etc/dnsmasq.d/acm.org.hosts` or reload dnsmasq because DNS resolver configuration affects customers and name-resolution policy. Under the admin approval policy, such a change requires administrator approval.

3. What was discovered about the network

- AS1’s loopback address is `4.2.2.1/32`.
- AS1’s interfaces to Uni, AS2, and EveLink were up.
- AS1’s default route points to AS2:
  - `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
- AS1 had working peer connectivity to AS2 at `10.0.2.2`.
- AS1 could reach the valid ACM service endpoint `198.82.0.1`.
- AS1 and Uni both experienced failure reaching `198.82.0.99`, receiving ICMP Destination Host Unreachable from `198.82.0.254`.
- AS2 and ACM confirmed that:
  - The ACM-facing route to `198.82.0.0/24` was healthy.
  - `198.82.0.1` was reachable and was the valid ACM service address.
  - `198.82.0.99` was not an expected or configured ACM Digital Library service address.
- The root cause was AS1’s recursive DNS resolver serving a stale static override:
  - `198.82.0.99 acm.org www.acm.org`
- No routing changes were made.
- No `ip route add` or `ip route del` commands were run because the routing table was already converged and the issue was not caused by forwarding or route reachability.

4. Coordination with other agents

- Received the original KP WHY request from Uni.
  - Uni had already audited its own local interfaces, forwarding, default route, and packet filter.
  - Uni reported that its user and loopback-sourced tests to `198.82.0.99` failed with ICMP Destination Host Unreachable from `198.82.0.254`.

- Sent a KP WHY request to AS2.
  - Asked AS2 to investigate reachability to `198.82.0.99` from the AS2/ACM-facing side.
  - Included AS1’s local observations and test results.

- Received AS2’s KP WHY response.
  - AS2 confirmed its interfaces and route to ACM were healthy.
  - AS2 confirmed `198.82.0.1` was reachable.
  - AS2 and ACM confirmed `198.82.0.99` was not a valid ACM service host.
  - AS2 recommended auditing AS1/Uni/client DNS cache or local configuration.

- Sent final diagnosis to Uni.
  - Reported that the failure was caused by AS1 DNS returning the stale address `198.82.0.99`.
  - Proposed correcting/removing the AS1 resolver override so `acm.org` resolves to `198.82.0.1`.
  - Reported `CANNOT` pending administrator approval because changing DNS resolver configuration affects customers.