**Observed**: ISP's loopback address, Remote's suboptimal route advertisement, successful ping to ISP's loopback after adjustments.  
**Decided**: Added static route via eth0, instructed Remote to propagate via eth1, blocked Remote's suboptimal route, verified routes/ping.  
**Why**: Ensured direct ISP reachability, corrected inefficient path, validated functionality through testing, and coordinated with peers to maintain optimal routing without daemons.
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Initial Setup**:  
   - Called `report_done` initially as the network was pre-configured and operational.  
   - Verified existing routes (via `ip route show`) to neighbors (ISP via eth0, Remote via eth1) and loopback address (198.18.0.1/32).  

2. **Handling ISP’s Loopback Advertisement**:  
   - Added a static route for ISP’s loopback (85.12.64.1/32) via ISP’s interface (`10.4.2.1` on `Cheap-eth0`).  
     ```  
     ip route add 85.12.64.1/32 via 10.4.2.1 dev Cheap-eth0  
     ```  
   - Sent a message to Remote to propagate the route via my eth1 interface (`10.4.4.1`).  

3. **Addressing Remote’s Suboptimal Route**:  
   - After Remote advertised a path to 85.12.64.1/32 via their loopback (203.0.113.1), I instructed them to stop propagating this route.  
   - Justified that the direct path via ISP (eth0) is shorter and more reliable.  

4. **Verification**:  
   - Ran `ping -c 3 85.12.64.1` to confirm reachability via the direct ISP path.  
   - Checked the route entry with `ip route show 85.12.64.1/32` to ensure it remained via eth0.  

---

### **2. Justifications**  
- **Static Route Addition**: Ensured end-to-end connectivity to ISP’s loopback, which was critical for the customer’s advertised address.  
- **Message to Remote**: Enabled route propagation to other nodes while maintaining control over path selection.  
- **Correcting Remote’s Route**: Avoided suboptimal paths by prioritizing the direct connection to ISP over Remote’s longer path.  
- **Verification Steps**: Confirmed route functionality and stability, ensuring no conflicts arose from Remote’s adjustments.  

---

### **3. Discoveries About the Network**  
- **Topology**:  
  - ISP is a customer (connected via eth0), Remote is a peer (connected via eth1).  
  - Remote had a pre-existing route (via Expensive) for 85.12.64.1/32, which was removed after coordination.  
- **Route Propagation**:  
  - Static routes must be explicitly managed since no routing daemons (e.g., BGP) are used.  
  - Direct connections (e.g., ISP) provide shorter paths than indirect paths (via peers).  
- **Latency Considerations**:  
  - The ping to ISP’s loopback showed consistent 120ms latency, confirming stable connectivity.  

---

### **4. Coordination with Other Agents**  
- **ISP**: Received a loopback advertisement and acknowledged by adding the route.  
- **Remote**:  
  - Instructed to propagate the route via my interface after initial setup.  
  - Corrected their suboptimal path advertisement by explicitly requesting removal.  
  - Confirmed compliance when Remote adjusted its routes to use only my direct path.  

---

**Conclusion**: The network was stabilized by manually configuring routes, coordinating with peers to avoid suboptimal paths, and verifying reachability. Direct customer connections take priority over peer paths to optimize routing efficiency.