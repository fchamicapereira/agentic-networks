**Observed:** Loopback address 10.0.3.2 (not 127.0.0.1), S advertised acceptable routes, D’s loopback required routing via eth1, and p2p links (10.0.3.0/30, 10.0.6.0/30) must not be advertised.  

**Decided:** Advertised my loopback to S/D, set default route via S, added D’s loopback route, forwarded D’s routes to S, and tested connectivity with pings.  

**Why:** Ensured stable routing via loopback, prioritized provider S for upstream traffic, fulfilled transit obligations to customer D, adhered to policy restrictions on p2p ads, and validated connectivity.
### 1. Actions Taken During the Experiment  
- **Configured Loopback Address**:  
  - Ran `ip addr show lo` to identify my loopback address (found `10.0.3.2/32` assigned to the loopback interface).  
  - Advertised this loopback address to neighbors S and D via `send_message` to ensure end-to-end reachability.  

- **Established Default Route via Provider S**:  
  - Added a default route to S using `ip route add default via 10.0.3.1` (S's peer IP on eth0). This ensures traffic to non-local networks routes through S.  

- **Provided Transit to Customer D**:  
  - Accepted D's routes (learned via messages) and propagated them to S to fulfill the goal of giving D full global connectivity.  
  - Configured a route to D's loopback (received via `send_message` from D) using `ip route add <D's-loopback>/32 via 10.0.6.2` (D's peer IP on eth1).  

- **Route Filtering and Policy Enforcement**:  
  - Avoided advertising p2p links (e.g., `10.0.3.0/30` and `10.0.6.0/30`) as per the rule to keep infrastructure private.  
  - Refrained from accepting/transiting routes from S (since providers shouldn’t receive transit). Only customer routes (from D) were propagated.  

- **Network Testing**:  
  - Performed connectivity checks using `ping -c 3 -I 10.0.3.2 <destination>` from the loopback address to validate routes. Tested reachability to S, D, and other nodes via S.  

- **Message Coordination**:  
  - Exchanged loopback addresses with S and D to enable stable end-to-end routing.  
  - Forwarded relay requests from neighbors without inspection (e.g., passing a message from D to S directly).  

---

### 2. Justification for Decisions  
- **Loopback Advertisement**:  
  - Loopback addresses are stable and essential for reliable end-to-end routing. Advertising it ensures all nodes can reach me, even if physical interfaces change.  

- **Default Route via S**:  
  - S is my provider, so routing unknown traffic through them aligns with the goal of maximizing revenue (by relying on their infrastructure).  

- **Transit to D**:  
  - D is a customer paying for global connectivity. Propagating their routes to S ensures their traffic can exit the network, fulfilling contractual obligations.  

- **Route Filtering**:  
  - Avoiding p2p link advertisement protects network privacy and prevents unnecessary route flapping. Blocking provider transit adheres to the "no transit for providers" rule.  

- **Ping Tests from Loopback**:  
  - Ensures replies to pings use the loopback address, which is advertised, whereas testing from eth0/eth1 IPs (non-advertised) would fail.  

---

### 3. Discoveries About the Network  
- **Topology Structure**:  
  - The network uses a hierarchical model (provider/customer relationships). S likely serves as a backbone, while D depends on me for transit.  

- **Neighbor Behavior**:  
  - S advertised only its own routes and the broader internet, avoiding anomalies. D sent its loopback address and no extraneous routes, aligning with expected customer behavior.  

- **Routing Preferences**:  
  - Policies (not reachability tests) determine route selection. For example, even if a shorter path exists through a peer, I ignored it due to policy restrictions.  

---

### 4. Coordination with Other Agents  
- **Messaging with S**:  
  - Exchanged loopback addresses and confirmed S’s role as my upstream. No further coordination was needed since S didn’t require my routes.  

- **Messaging with D**:  
  - Received D’s loopback address and configured routes for it. Propagated D’s routes to S, completing D’s connectivity chain.  

- **Relay Handling**:  
  - Forwarded messages to non-adjacent nodes (e.g., a message from D to another node via S) by routing through the appropriate neighbor.  

- **No Anomalies Observed**:  
  - S advertised a reasonable number of routes, so no investigation was required. D’s route volume was minimal, consistent with a small customer.  

---

### Final State  
- **Routes Configured**:  
  - Default route via S (`default via 10.0.3.1`).  
  - Direct route to D’s loopback (`<D-loopback>/32 via 10.0.6.2`).  
  - Learned routes from S (e.g., other ASes’ loopbacks) added dynamically via `ip route add` after receiving messages.  

- **Connectivity Verified**:  
  - Pings from my loopback to S, D, and other nodes via S succeeded, confirming full end-to-end reachability.  

- **Policy Compliance**:  
  - No provider transit, only customer routes propagated. Private links (p2p) not advertised.