**Observed**: Loopback address 4.2.2.1/32 identified via `ip addr show lo`; route advertisements acknowledged by Uni, EveLink, and AS2; ACM reachable via AS2’s interface with successful ping and DNS resolution via `dig`.  

**Decided**: Advertise loopback address to neighbors, validate routes via `ip route show`, test ACM connectivity and DNS, then report task completion.  

**Why**: Ensure stable end-to-end communication, confirm route propagation, verify service functionality (DNS/ping), and signal task completion once objectives were met.
### Experiment Report: AS1 Agent Actions and Findings

---

#### **1. Actions Taken**
1. **Identified Stable Loopback Address**  
   - Ran `ip addr show lo` to discover the loopback address `4.2.2.1/32`, critical for end-to-end routing.
   - Justification: This address is the only globally routable identifier for AS1, ensuring remote nodes can route back to it.

2. **Advertised Loopback Address to Neighbors**  
   - Sent messages to **Uni**, **EveLink**, and **AS2**, instructing them to route `4.2.2.1/32` via their respective link IPs (e.g., `10.0.1.2` for Uni).  
   - Justification: Manual route sharing ensures customers/peers can reach AS1’s DNS resolver and services, fulfilling transit obligations.

3. **Configured Routing for ACM Web Server**  
   - Verified `198.82.0.0/24` (ACM) was reachable via AS2’s link (`10.0.2.2`), confirmed via `ip route show`.  
   - Justification: ACM’s connectivity via peer AS2 aligns with revenue goals and validates AS2’s role as a transit path.

4. **Validated Network Functionality**  
   - Ran `ping -c 3 -I 4.2.2.1 198.82.0.1` to confirm ACM reachability.  
   - Tested DNS resolution with `dig +short @4.2.2.1 example.com`, ensuring the resolver functioned on the loopback.  
   - Justification: Direct testing avoids false positives from relayed diagnostics and confirms end-to-end service reliability.

5. **Reported Completion**  
   - Called `report_done` after confirming all routes, DNS, and ACM connectivity were operational.  
   - Justification: Signaled network readiness and success to the testbed.

6. **Monitored Stability**  
   - Remained idle after stabilization, responding to periodic updates (e.g., AS2’s route acknowledgment).  
   - Justification: Avoided unnecessary configuration changes while maintaining awareness of network state.

---

#### **2. Justifications for Decisions**
- **Loopback Address Prioritization**: Sourcing traffic from `4.2.2.1` ensures replies can route back through the correct path, avoiding pitfalls of link-local addresses.  
- **Route Advertisement to Peers/Clients**: Essential for fulfilling transit obligations and enabling end-to-end reachability for customers like Uni/EveLink.  
- **ACM via AS2**: AS2 is a peer, so using its link avoids violating payment terms (no transit fees) while providing ACM access.  
- **DNS Validation**: AS1’s role as a recursive resolver requires confirming resolution works from its loopback, ensuring clients can use it reliably.  
- **Idle Monitoring**: Post-configuration stability checks avoid introducing errors while respecting the principle of minimal intervention for operational networks.

---

#### **3. Network Discoveries**
- **Topology Structure**:  
  - AS1 is connected to Uni/EveLink (customers) and AS2 (peer).  
  - ACM is reachable via AS2, confirming AS2’s upstream connectivity.  
- **Route Propagation**:  
  - Neighbors (Uni, EveLink, AS2) reliably installed advertised routes (e.g., `4.2.2.1/32`).  
- **DNS Functionality**:  
  - The resolver operates on `4.2.2.1`, accessible to clients.  
- **Path Stability**:  
  - ACM’s ICMP connectivity (0% loss) and DNS resolution validate end-to-end paths.  

---

#### **4. Agent Coordination**
- **With Uni/EveLink**:  
  - Directed them to install routes for `4.2.2.1/32` via their link IPs.  
  - Received acknowledgments confirming route installation and connectivity.  
- **With AS2**:  
  - Advertised `4.2.2.1/32` over the peering link (`10.0.2.1`).  
  - AS2 confirmed the route was active and valid, ensuring bidirectional transit.  
- **Cross-Agent Consistency**:  
  - All neighbors independently validated routes, reducing dependency on centralized coordination.  

---

### **Conclusion**  
The experiment achieved stable transit service for customers, ACM reachability via AS2, and functional DNS resolution. Collaboration with neighbors ensured consistent route propagation, while direct testing validated operational correctness. No anomalies were detected post-configuration, confirming the network’s readiness for production use.