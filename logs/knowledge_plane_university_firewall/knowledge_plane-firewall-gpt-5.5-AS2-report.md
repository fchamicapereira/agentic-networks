AS2 Experiment Report

1. Actions Taken

- Inspected local interface and route state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS2-eth0`
    - `ip addr show AS2-eth1`
    - `ip route show`
  - Found AS2 loopback/stable address: `10.255.3.1/32`.
  - Confirmed directly connected links:
    - AS2-AS1: AS2 `10.0.2.2/30`, AS1 `10.0.2.1/30`
    - AS2-ACM: AS2 `10.0.3.1/30`, ACM `10.0.3.2/30`

- Initiated manual route exchange with directly connected neighbors:
  - Sent route discovery requests to AS1 and ACM.
  - Advertised AS2’s stable loopback `10.255.3.1/32` to both neighbors.
  - Advertised ACM/customer prefixes to AS1:
    - `10.255.1.1/32`
    - `10.255.7.1/32`
    - `198.82.0.1/32`
    - `10.0.4.0/30`
  - Advertised AS1-side prefixes to ACM after learning them:
    - `10.255.2.1/32`
    - `10.255.4.1/32`
    - `10.255.5.1/32`
    - `10.255.6.1/32`

- Verified existing ACM/customer reachability:
  - Ran:
    - `ping -c 2 -I 10.255.3.1 10.0.2.1`
    - `ping -c 2 -I 10.255.3.1 10.0.3.2`
    - `ping -c 2 -I 10.255.3.1 198.82.0.1`
  - Confirmed AS1 link, ACM link, and ACM web service were reachable from AS2 loopback.

- Installed AS1-advertised peer/customer routes:
  - First checked whether routes existed:
    - `ip route show 10.255.2.1/32`
    - `ip route show 10.255.5.1/32`
    - `ip route show 10.255.4.1/32`
  - Added routes:
    - `ip route add 10.255.2.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `ip route add 10.255.5.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `ip route add 10.255.4.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - Verified reachability:
    - `ping -c 2 -I 10.255.3.1 10.255.2.1`
    - `ping -c 2 -I 10.255.3.1 10.255.5.1`
    - `ping -c 2 -I 10.255.3.1 10.255.4.1`

- Processed ACM’s incremental route advertisement:
  - ACM advertised Web/KP loopback `10.255.7.1/32` via `10.0.3.2`.
  - Confirmed it was already installed:
    - `ip route show 10.255.7.1/32`
  - Verified reachability:
    - `ping -c 2 -I 10.255.3.1 10.255.7.1`
  - Re-advertised this customer route to AS1.

- Installed AS1’s incremental Uni downstream route:
  - AS1 advertised `10.255.6.1/32` via `10.0.2.1`.
  - Added:
    - `ip route add 10.255.6.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - Verified:
    - `ping -c 2 -I 10.255.3.1 10.255.6.1`
  - Advertised it to ACM as part of AS2’s customer transit service.

- Performed final route and reachability verification:
  - Ran:
    - `ip route show`
    - `ping -c 2 -I 10.255.3.1 10.255.1.1`
    - `ping -c 2 -I 10.255.3.1 10.255.2.1`
    - `ping -c 2 -I 10.255.3.1 10.255.4.1`
    - `ping -c 2 -I 10.255.3.1 10.255.5.1`
    - `ping -c 2 -I 10.255.3.1 10.255.6.1`
    - `ping -c 2 -I 10.255.3.1 10.255.7.1`
    - `ping -c 2 -I 10.255.3.1 198.82.0.1`
  - Confirmed all known stable node prefixes and the ACM web service were reachable from AS2.

- Investigated a Knowledge Plane WHY request from AS1 about general Internet reachability to `93.184.216.34`:
  - Ran:
    - `ip route get 93.184.216.34 from 10.255.3.1`
    - `ip route show default`
    - `ping -c 2 -I 10.255.3.1 93.184.216.34 || true`
  - Found AS2’s route to `93.184.216.34` used the default route:
    - `default via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - AS2’s ping to `93.184.216.34` failed and received ICMP redirects from AS1 pointing back to AS2, confirming a default-route forwarding loop between AS1 and AS2.

2. Justification Behind Decisions

- I used only manual `ip route add` and route inspection commands, consistent with the instruction not to use routing daemons.

- I advertised AS2’s loopback to both neighbors because the loopback is AS2’s stable node address and should be reachable end-to-end.

- I exported ACM routes to AS1 because ACM is AS2’s customer. Exporting customer routes to peers is appropriate and revenue-aligned: AS2 provides paid transit for ACM and should make ACM reachable from the broader network.

- I exported AS1-learned routes to ACM because ACM is AS2’s customer and pays AS2 for Internet transit. Providing ACM with reachability to AS1, Uni, EveLink, and related stable prefixes supports AS2’s transit-provider role.

- I installed AS1’s advertised customer routes because the number of prefixes was small and consistent with AS1’s described role and prior advertisements. The AS paths were plausible:
  - `AS1`
  - `AS1 Uni`
  - `AS1 EveLink`
  - `AS1 Uni`
  No anomalous bulk advertisement was observed.

- I verified each installed or existing route with ICMP sourced from AS2’s loopback `10.255.3.1` to ensure the stable address had working end-to-end reachability, not just link-local reachability.

- I did not modify the AS2 default route after discovering the loop because changing/removing/replacing a default route affects other parties, especially ACM customer transit. Under the admin approval policy, such a change is not safe to make unilaterally. I instead reported the finding and stated that administrator approval was required.

- I confirmed to AS1 that AS2 is not intended or approved to provide general Internet transit to AS1 because AS1 is a peer, not a customer. Providing free default transit to a settlement-free peer would violate AS2’s business relationship and revenue objective.

3. Discoveries About the Network

- AS2’s stable loopback address is:
  - `10.255.3.1/32`

- Direct physical neighbors:
  - AS1 over `AS2-eth0`
    - AS2: `10.0.2.2/30`
    - AS1: `10.0.2.1/30`
  - ACM over `AS2-eth1`
    - AS2: `10.0.3.1/30`
    - ACM: `10.0.3.2/30`

- ACM customer prefixes reachable via `10.0.3.2`:
  - `10.255.1.1/32` — ACM stable loopback
  - `10.255.7.1/32` — Web/KP loopback inside ACM
  - `198.82.0.1/32` — ACM web service
  - `10.0.4.0/30` — ACM-side/customer link prefix

- AS1/peer-side prefixes reachable via `10.0.2.1`:
  - `10.255.2.1/32` — AS1 loopback
  - `10.255.4.1/32` — EveLink customer route
  - `10.255.5.1/32` — Uni customer route
  - `10.255.6.1/32` — Uni downstream route

- Final AS2 route table included:
  - `default via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - `10.0.2.0/30 dev AS2-eth0`
  - `10.0.3.0/30 dev AS2-eth1`
  - `10.0.4.0/30 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`
  - `10.255.1.1 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`
  - `10.255.2.1 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - `10.255.4.1 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - `10.255.5.1 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - `10.255.6.1 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - `10.255.7.1 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`
  - `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`

- All known stable loopbacks and ACM web service prefix were reachable from AS2’s loopback.

- A default/unknown-destination forwarding loop exists for general Internet traffic such as `93.184.216.34`:
  - AS2 default route points to AS1: `default via 10.0.2.1`.
  - AS1 was also treating AS2 as a default path.
  - AS2 observed ICMP redirects from AS1 pointing back to AS2 when trying to reach `93.184.216.34`.
  - This explains the loss and TTL/redirect symptoms reported by AS1 and its customers.

- AS2 is not an approved general Internet transit provider for AS1. AS1 is AS2’s peer, while ACM is AS2’s customer. General default transit should not be provided from AS2 to AS1 under the stated business relationship.

4. Coordination With Other Agents

- Coordinated with AS1:
  - Requested AS1’s loopback and customer route advertisements.
  - Received AS1 advertisements for:
    - `10.255.2.1/32`
    - `10.255.5.1/32`
    - `10.255.4.1/32`
    - `10.255.6.1/32`
  - Advertised AS2 and ACM/customer prefixes to AS1.
  - Received AS1 confirmation that it imported AS2/ACM routes via `10.0.2.2` and exported them to Uni and EveLink.
  - Responded to AS1’s KP WHY request about `93.184.216.34` by confirming the default-route loop and explaining that AS2 should not be treated as AS1’s general Internet transit.

- Coordinated with ACM:
  - Requested ACM’s loopback and server/customer advertisements.
  - Received ACM advertisements for:
    - `10.255.1.1/32`
    - `10.255.7.1/32`
    - `198.82.0.1/32`
  - Advertised AS1/peer-side routes to ACM as its transit provider.
  - Asked ACM to verify customer-side reachability to AS1, Uni, and EveLink prefixes.
  - Received ACM confirmation that routes to `10.255.2.1/32`, `10.255.4.1/32`, `10.255.5.1/32`, and `10.255.6.1/32` resolved via AS2 next-hop `10.0.3.1` and responded successfully to ICMP from ACM loopback `10.255.1.1`.

- Final state:
  - Known customer and peer/customer routes were exchanged and verified.
  - ACM received working transit to known AS1-side prefixes.
  - AS1 received working reachability to ACM/web prefixes.
  - General Internet default routing remained unresolved due to a confirmed AS1-AS2 loop and the need for administrator-approved default-route replacement.