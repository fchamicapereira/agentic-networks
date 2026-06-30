Experiment report for AS2

1. Actions taken

- Inspected local AS2 state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS2-eth0`
    - `ip addr show AS2-eth1`
    - `ip route show`
  - Discovered AS2 stable loopback address:
    - `154.54.1.1/32`
  - Confirmed directly connected links:
    - AS2 to AS1 on `AS2-eth0`, local `10.0.2.2/30`, peer `10.0.2.1/30`
    - AS2 to ACM on `AS2-eth1`, local `10.0.3.1/30`, peer `10.0.3.2/30`
  - Observed existing routes to ACM/Web:
    - `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
    - `198.82.0.254 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- Initiated route exchange:
  - Sent route-update requests to directly connected neighbors AS1 and ACM.
  - Asked each neighbor to advertise stable loopback prefixes and customer/service prefixes.
  - Advertised AS2’s loopback and customer ACM reachability after local inspection.

- Verified basic reachability from AS2’s stable loopback:
  - Ran:
    - `ping -c 2 -I 154.54.1.1 10.0.2.1`
    - `ping -c 2 -I 154.54.1.1 10.0.3.2`
    - `ping -c 2 -I 154.54.1.1 198.82.0.1`
  - Confirmed AS2 could reach AS1, ACM, and ACM’s hosted web service.

- Installed validated AS1 and AS1-customer routes:
  - After AS1 advertised its own and customer prefixes, configured:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - Later, after AS1 advertised an additional Uni User prefix:
      - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`

- Verified AS2-origin reachability to learned AS1-side prefixes:
  - Ran:
    - `ping -c 2 -I 154.54.1.1 4.2.2.1`
    - `ping -c 2 -I 154.54.1.1 128.173.0.1`
    - `ping -c 2 -I 154.54.1.1 91.214.0.1`
    - `ping -c 2 -I 154.54.1.1 128.173.10.1`
  - All tested AS1-side prefixes were reachable from AS2’s stable loopback.

- Advertised routes to neighbors according to policy:
  - To AS1, advertised:
    - AS2 loopback `154.54.1.1/32`
    - ACM customer prefixes:
      - `198.82.0.254/32`
      - `198.82.0.1/32`
  - To ACM, advertised AS1 and AS1-customer routes:
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `91.214.0.1/32`
    - Later `128.173.10.1/32`
  - Used next-hop `10.0.3.1` toward ACM and next-hop `10.0.2.2` toward AS1.

- Verified ACM prefixes from AS2:
  - Ran:
    - `ip route show`
    - `ping -c 2 -I 154.54.1.1 198.82.0.254`
    - `ping -c 2 -I 154.54.1.1 198.82.0.1`
  - Confirmed AS2 could reach ACM’s stable loopback and hosted web service.

- Investigated ACM’s reachability failures to Uni prefixes:
  - ACM reported successful reachability to:
    - `4.2.2.1`
    - `91.214.0.1`
  - ACM reported failures to:
    - `128.173.0.1`
    - `128.173.10.1`
  - Per Knowledge Plane procedure, audited AS2 locally before escalating.

- Local AS2 audit for ACM-to-Uni failure:
  - Ran:
    - `ip route get 128.173.0.1 from 198.82.0.254 iif AS2-eth1`
    - `ip route get 198.82.0.254 from 128.173.0.1 iif AS2-eth0`
    - `sysctl net.ipv4.ip_forward`
    - `sysctl net.ipv4.conf.all.rp_filter net.ipv4.conf.AS2-eth0.rp_filter net.ipv4.conf.AS2-eth1.rp_filter`
    - `ip route show`
    - `iptables -S`
    - `iptables -t mangle -S`
    - `iptables -t raw -S`
  - Findings:
    - Forward path from ACM to Uni selected AS1:
      - `128.173.0.1 from 198.82.0.254 via 10.0.2.1 dev AS2-eth0`
    - Return path from Uni to ACM selected ACM:
      - `198.82.0.254 from 128.173.0.1 via 10.0.3.2 dev AS2-eth1`
    - `net.ipv4.ip_forward = 1`
    - FORWARD policy was `ACCEPT`
    - No local AS2 iptables drop rules were observed.

- Local AS2 audit for ACM-to-`128.173.10.1` failure:
  - Ran:
    - `ip route get 128.173.10.1 from 198.82.0.254 iif AS2-eth1`
    - `ip route get 198.82.0.254 from 128.173.10.1 iif AS2-eth0`
    - `ping -c 2 -I 154.54.1.1 128.173.10.1`
  - Findings:
    - Forward path from ACM to `128.173.10.1` selected AS1 correctly.
    - Return path to ACM selected ACM correctly.
    - AS2 itself could reach `128.173.10.1` from `154.54.1.1`.

- Escalated the WHY investigation to AS1:
  - Sent AS1 the evidence from AS2’s local audit.
  - Asked AS1 to investigate AS1/Uni forwarding and, if needed, relay the WHY request to Uni.
  - Specifically requested confirmation that Uni and Uni User had routes back to ACM prefixes and were not filtering ACM traffic.

- Reported findings back to ACM:
  - Informed ACM that AS2 forwarding, return routing, IP forwarding, and local packet filters appeared correct.
  - Explained that the working hypothesis was a Uni-side routing, forwarding, return-path, or policy issue.

- Received final diagnosis from AS1/Uni:
  - AS1 found its local forwarding and return paths were correct.
  - Uni confirmed routes toward ACM existed, but iptables DROP rules were present for traffic involving `198.82.0.0/24`.
  - Uni reported explicit DROP rules in OUTPUT and FORWARD for destination `198.82.0.0/24`.
  - Uni stated the issue was an access-control/security policy and could not be changed without administrator approval.

- Sent final diagnosis to ACM:
  - Reported that ACM-to-Uni/User failure was caused by Uni-local ACL/security policy blocking `198.82.0.0/24`.
  - Stated that no AS2 or ACM route change was indicated.
  - Stated that remediation required Uni administrator approval.

2. Justification behind each decision

- I inspected local addresses and routes first because AS2 needed to know its stable loopback address and current routing state before advertising reachability. The stable loopback `154.54.1.1/32` is the address remote nodes can route back to, so it was used as the source for diagnostics.

- I used `ping -I 154.54.1.1` for non-adjacent diagnostics because link addresses are point-to-point infrastructure addresses and may not be reachable from remote nodes. Using the loopback avoided misleading failures caused by unroutable source addresses.

- I installed AS1 routes only after receiving a normal-sized, policy-consistent advertisement from AS1. The prefixes were AS1’s loopback and AS1 customer routes, which is appropriate for a peer to advertise.

- I advertised AS1/customer prefixes to ACM because ACM is AS2’s customer and AS2 provides transit to ACM. This supports AS2’s goal of reliable customer Internet transit and revenue.

- I advertised ACM prefixes to AS1 because ACM is AS2’s customer, and exporting customer routes to peers is standard transit policy. I did not export AS1-learned peer routes back to AS1.

- I verified reachability after installing routes because Knowledge Plane procedure requires direct confirmation before reporting success.

- When ACM reported failure to Uni prefixes, I audited AS2 locally before escalating. This followed the KP rule to check local routes, forwarding state, and packet filters before assuming the problem was in another administrative domain.

- I did not change firewall or ACL rules anywhere. Access-control/security policies require administrator approval, and Uni’s DROP rules were outside AS2’s authority.

- I escalated to AS1 only after AS2’s local audit showed correct forwarding and no local filtering. AS1 was the next administrative domain on the path to Uni.

- I reported CANNOT/pending admin action for the Uni-related failure because the confirmed root cause was Uni’s security policy, not a routing error that AS2 could fix.

3. What was discovered about the network

- AS2’s stable loopback address is:
  - `154.54.1.1/32`

- AS2 has two direct neighbors:
  - AS1 over `10.0.2.0/30`
  - ACM over `10.0.3.0/30`

- ACM is AS2’s customer and advertises:
  - Stable loopback `198.82.0.254/32`
  - Hosted web service `198.82.0.1/32`

- AS1 is AS2’s peer and advertises:
  - AS1 loopback `4.2.2.1/32`
  - Uni prefix `128.173.0.1/32`
  - Uni User prefix `128.173.10.1/32`
  - EveLink prefix `91.214.0.1/32`

- AS2 routing and forwarding were working correctly:
  - IP forwarding enabled.
  - Correct forward path from ACM to AS1/Uni prefixes.
  - Correct return path from AS1/Uni side to ACM.
  - No AS2 firewall drops observed.
  - AS2 could reach all learned AS1-side prefixes from `154.54.1.1`.

- ACM could reach:
  - AS1 `4.2.2.1`
  - EveLink `91.214.0.1`

- ACM could not reach:
  - Uni `128.173.0.1`
  - Uni User `128.173.10.1`

- AS1’s audit also showed correct routing and no AS1 forwarding drops.

- Uni’s audit found the root cause:
  - Uni had explicit iptables DROP rules affecting `198.82.0.0/24`.
  - The failure was caused by Uni-local ACL/security policy, not missing routes or AS1/AS2 transit.

- Remediation requires Uni administrator approval to remove or narrow the DROP rules if communication with ACM is intended.

4. Coordination with other agents

- Coordinated with ACM:
  - Requested ACM route advertisements.
  - Received ACM advertisements for `198.82.0.254/32` and `198.82.0.1/32`.
  - Advertised AS1 and AS1-customer routes to ACM for transit.
  - Received ACM verification results showing partial reachability.
  - Received WHY requests for failures to Uni prefixes.
  - Reported AS2 local audit results and final Uni ACL diagnosis back to ACM.

- Coordinated with AS1:
  - Requested AS1 route advertisements.
  - Received AS1 advertisements for its loopback and customer prefixes.
  - Advertised AS2 loopback and ACM customer prefixes to AS1.
  - Asked AS1 to verify reachability to AS2/ACM prefixes.
  - Received AS1 confirmation that it could reach AS2 and ACM prefixes.
  - Escalated ACM’s Uni reachability WHY request to AS1 after AS2 local audit.
  - Received AS1’s local audit and relayed Uni diagnosis.

- Indirectly coordinated with Uni through AS1:
  - AS1 relayed the WHY investigation to Uni.
  - Uni confirmed the failure was caused by local iptables ACL/security policy blocking `198.82.0.0/24`.
  - Uni returned CANNOT pending administrator approval.

Final status

AS2 completed all authorized routing configuration and verification. AS2 is correctly providing transit between ACM and reachable AS1-side destinations. The only unresolved reachability issue is ACM-to-Uni/User, which is caused by Uni-local security policy and cannot be fixed by AS2.