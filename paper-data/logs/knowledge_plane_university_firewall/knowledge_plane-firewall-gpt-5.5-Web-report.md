Experiment Report — Web Node

1. Actions Taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Web-eth0`
    - `ip route show`
  - Found Web’s stable loopback/service address:
    - `198.82.0.1/32` on `lo`
  - Found directly connected ACM link:
    - Web: `10.0.4.2/30`
    - ACM peer: `10.0.4.1/30`
  - Found existing default route:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- Advertised Web’s service prefix to ACM:
  - Sent ACM a message stating that Web’s stable loopback/service address is `198.82.0.1/32`.
  - Asked ACM to advertise it upstream and provide any routing information needed for end-to-end tests.

- Verified direct ACM connectivity:
  - Ran:
    - `ping -c 3 -I 198.82.0.1 10.0.4.1`
  - Result: successful, 0% packet loss.

- Tested reachability to ACM and upstream stable loopbacks:
  - After ACM reported that it advertised Web upstream and provided reachable stable prefixes, ran:
    - `ping -c 3 -I 198.82.0.1 198.82.0.254`
    - `ping -c 3 -I 198.82.0.1 154.54.1.1`
  - Results:
    - ACM loopback `198.82.0.254`: reachable
    - AS2 loopback `154.54.1.1`: reachable

- Tested additional upstream advertised prefixes:
  - Ran:
    - `ping -c 3 -I 198.82.0.1 4.2.2.1`
    - `ping -c 3 -I 198.82.0.1 128.173.0.1`
  - Result:
    - AS1 prefix `4.2.2.1`: reachable
    - Uni prefix `128.173.0.1`: unreachable, 100% packet loss
  - Because the command sequence stopped after the failed ping, I later tested the remaining advertised prefix:
    - `ping -c 3 -I 198.82.0.1 91.214.0.1`
  - Result:
    - EveLink prefix `91.214.0.1`: reachable

- Checked local route selection for the failed Uni prefix:
  - Ran:
    - `ip route get 128.173.0.1 from 198.82.0.1`
  - Result:
    - Route selected correctly via `10.0.4.1 dev Web-eth0`

- Performed a local audit before escalating:
  - Ran:
    - `ip route show`
    - `ip rule show`
    - `iptables -S || true`
    - `nft list ruleset || true`
  - Findings:
    - Default route remained via ACM:
      - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - Policy routing was standard:
      - local, main, default tables only
    - iptables policies were ACCEPT:
      - `INPUT ACCEPT`
      - `FORWARD ACCEPT`
      - `OUTPUT ACCEPT`
    - `nft` was not installed
  - No local Web-side packet filter or route problem was found.

- Escalated a WHY request to ACM:
  - Reported that `128.173.0.1/32` was unreachable from Web when sourced from `198.82.0.1`.
  - Included evidence that other prefixes were reachable and that local Web routing/filtering appeared correct.
  - Asked ACM to investigate or relay upstream toward AS2/AS1/Uni.

- Retested the failed symptom while waiting:
  - Ran:
    - `ping -c 3 -I 198.82.0.1 128.173.0.1`
  - Result:
    - Still 100% packet loss.

- Reported final status after upstream diagnosis:
  - No route changes were made on Web.
  - No firewall or security policy changes were made.

2. Justification Behind Each Decision

- I first inspected local interfaces and routes because Knowledge Plane procedure requires local investigation before escalating. This confirmed Web’s stable loopback address and existing forwarding state.

- I advertised only the loopback `198.82.0.1/32` to ACM because the experiment instructions specified that loopback addresses are the stable node addresses to advertise network-wide. I did not advertise the point-to-point link address `10.0.4.2/30`, since that is only infrastructure addressing for the Web–ACM link.

- I sourced diagnostic traffic from `198.82.0.1` because remote nodes can route back to stable loopback addresses, while replies to point-to-point link addresses may fail misleadingly.

- I kept the existing default route via ACM because ACM is Web’s only neighbor and all non-local traffic should exit through ACM. The route was already correct:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- I tested ACM, AS2, AS1, and EveLink reachability to distinguish a general routing failure from a destination-specific problem. Since most upstream prefixes were reachable, the problem was narrowed to Uni-specific reachability.

- I ran `ip route get`, `ip route show`, `ip rule show`, and firewall checks before escalating because the KP role requires confirming that the failure is not local. The route lookup showed packets to Uni were being sent correctly to ACM, and local firewall policy did not block the traffic.

- I escalated to ACM only after local checks found no Web-side cause. This avoided pushing an unverified hypothesis upstream.

- I did not change any routes because the Web routing state was correct and ACM explicitly advised that no Web/ACM route change was indicated.

- I did not attempt to modify any access-control or firewall rules because the final fault was a Uni-local security policy. Security policy changes require administrator approval and cannot be performed autonomously.

3. Discoveries About the Network

- Web’s stable service address is:
  - `198.82.0.1/32`
  - This is the address bound to the ACM Digital Library HTTP service.

- Web has one physical neighbor:
  - ACM via `Web-eth0`
  - Web link IP: `10.0.4.2/30`
  - ACM link IP: `10.0.4.1/30`

- Web’s default route is:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- ACM’s stable loopback is:
  - `198.82.0.254/32`

- AS2’s stable loopback is:
  - `154.54.1.1/32`

- Additional upstream stable prefixes advertised by ACM/AS2:
  - `4.2.2.1/32` via AS2/AS1
  - `128.173.0.1/32` via AS2/AS1/Uni
  - `91.214.0.1/32` via AS2/AS1/EveLink

- Reachability results from Web sourced from `198.82.0.1`:
  - `10.0.4.1`: reachable
  - `198.82.0.254`: reachable
  - `154.54.1.1`: reachable
  - `4.2.2.1`: reachable
  - `91.214.0.1`: reachable
  - `128.173.0.1`: not reachable

- The failure to reach Uni was not caused by Web routing, Web firewall policy, ACM routing, AS2 transit, or AS1 transit.

- The final upstream finding was that Uni has explicit access-control rules dropping traffic involving ACM space:
  - Uni reported DROP rules affecting `198.82.0.0/24`
  - Supplemental detail indicated Uni iptables counters showed explicit `OUTPUT` and `FORWARD` DROP rules for destination `198.82.0.0/24`

- Therefore, the ACM/Web ↔ Uni/User failure is due to Uni-local security policy, not a routing failure.

4. Coordination With Other Agents

- Coordinated directly with ACM, Web’s only neighbor.

- Sent ACM Web’s service route advertisement:
  - Web stable loopback: `198.82.0.1/32`
  - Confirmed the Web–ACM link was up and the default route pointed to ACM.

- Received from ACM:
  - Confirmation that ACM advertised `198.82.0.1/32` upstream to AS2.
  - ACM stable loopback information: `198.82.0.254/32`.
  - AS2 and other upstream stable prefixes for testing:
    - `154.54.1.1/32`
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `91.214.0.1/32`

- Sent ACM a WHY request for the Uni reachability failure after local Web investigation showed no route or firewall issue.

- ACM reproduced the failure from its own loopback and escalated upstream.

- ACM reported the upstream investigation results:
  - AS2 and AS1 found expected routing and forwarding.
  - AS2 could reach Uni prefixes from AS2 space.
  - Traffic sourced from ACM space was blocked downstream.
  - Uni confirmed access-control rules dropping `198.82.0.0/24`.

- Final coordinated conclusion:
  - No Web or ACM route change is required.
  - The remaining connectivity failure requires Uni administrator review and approval to remove or narrow the relevant DROP rules if ACM/Web access is intended.