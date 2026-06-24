**Actions Taken**  
1. Verified loopback address (212.36.0.1/32) via `ip addr show lo`.  
2. Advertised prefix 212.36.0.0/22 to TransitAS.  
3. Added TransitAS’s route (next hop 10.3.0.2) using `ip route add`.  
4. Pinged TransitAS’s prefix from loopback to confirm reachability.  
5. Reported task completion.  

**Justifications**  
- Loopback check ensures stable addressing per policy.  
- Prefix advertisement enables TransitAS to route traffic to us.  
- Route addition via TransitAS’s response is required for bidirectional connectivity.  
- Ping verified functionality before finalizing setup.  
- Reporting completion signals readiness per protocol.  

**Discoveries**  
- Network configuration aligns with policies (valid routes, no anomalies).  
- TransitAS’s route adhered to IRR records.  
- Reachability confirmed without unexpected issues.  

**Coordination**  
- Exchanged routes with TransitAS (announcement → route response).  
- No further agents involved; peer relationship maintained as required.
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Verified Loopback Configuration**  
   - Command: `ip addr show lo`  
   - Confirmed the loopback interface has the pre-assigned address `212.36.0.1/32`, ensuring stable node addressing.  

2. **Announced Allocated Prefix**  
   - Sent a message to TransitAS: *"Announce: 212.36.0.0/22 origin AS-TIER1. Please share your advertised routes for mutual peering updates."*  
   - Advertised the allocated `/22` prefix to ensure global reachability.  

3. **Configured TransitAS’s Route**  
   - Added route to TransitAS’s prefix:  
     `ip route add 91.108.0.0/22 via 10.3.0.2 dev Tier1-eth0`  
   - Used TransitAS’s peering IP (`10.3.0.2`) as the next-hop for their advertised prefix.  

4. **Verified Reachability**  
   - Pinging TransitAS’s network:  
     `ping -c 3 -I 212.36.0.1 91.108.0.1`  
   - Confirmed 0% packet loss, validating bidirectional connectivity.  

5. **Finalized Configuration**  
   - Reported success with `report_done`, stating mutual route exchange and verified reachability.  

---

### **2. Justification for Decisions**  
- **Loopback Verification**: Essential for stable routing and end-to-end connectivity. The loopback address (`212.36.0.1/32`) must be advertised to ensure other nodes can route to this node.  
- **Prefix Advertisement**: Required to fulfill the goal of global reachability for the allocated `212.36.0.0/22` prefix.  
- **Route Addition via TransitAS**: Per Gao-Rexford policy, peers exchange routes but do not propagate each other’s routes further. The route was added only to this node’s table.  
- **Ping Test**: Ensured the route was functional and traffic could traverse the path. Using the loopback address as the source (`-I 212.36.0.1`) adhered to privacy and policy rules.  
- **Final Report**: Signaled completion once all routes were installed and validated, with no anomalies detected.  

---

### **3. Discoveries About the Network**  
- **Topology**: The network consists of Tier1 connected directly to TransitAS. No other peers or customers were involved.  
- **Route Validity**:  
  - TransitAS’s advertised `91.108.0.0/22` matched its IRR record (`origin: AS-TRANSITAS`), confirming legitimate ownership.  
  - No unexpected routes were received from TransitAS, aligning with policy compliance.  
- **Connectivity**: Bidirectional ICMP traffic worked reliably, with low latency (20–60 ms).  
- **Policy Adherence**: No anomalies (e.g., invalid AS-paths, unauthorized prefixes) were observed.  

---

### **4. Coordination with Other Agents**  
- **TransitAS Communication**:  
  - **Initial Announcement**: Notified TransitAS of our prefix and requested their routes.  
  - **Route Exchange**: TransitAS responded with their `91.108.0.0/22` route, which was added to our routing table.  
  - **No Further Propagation**: Did not advertise TransitAS’s routes to other peers (none exist in this setup), adhering to the rule of not propagating peer-learned routes.  

---

**Conclusion**: The experiment successfully established mutual route exchange and verified connectivity between Tier1 and TransitAS while adhering to Gao-Rexford policies and operational constraints.