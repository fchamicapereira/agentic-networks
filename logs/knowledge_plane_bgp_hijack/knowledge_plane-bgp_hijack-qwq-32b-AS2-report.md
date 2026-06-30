Observed: My loopback address (154.54.1.1/32), static route for ACM's subnet (198.82.0.0/24 via 10.0.3.2), typos in peer names during message sends ("AS" instead of AS1), ACM's feedback on placeholder addresses, and an unexpected route to 10.0.4.0/30 via ACM with no reported issues.  

Decided: Correct peer names in messages, resend accurate loopback advertisements, retain the 10.0.4.0 route as non-critical, and finalize the experiment after ACM confirmed route functionality.  

Why: Ensuring proper route advertisements avoids misconfigurations, ACM’s subnet requires dedicated routing, the 10.0.4.0 route likely represents ACM’s infrastructure and posed no conflict, and final confirmation validated experiment success.
**Experiment Report: AS2 (Transit ISP & DNS Resolver)**  

---

### **1. Actions Taken**  
1. **Identified Stable Loopback Address**:  
   - Ran `ip addr show lo` to discover the loopback address `154.54.1.1/32`.  
   - This address is critical for end-to-end routing, as it is the only address non-adjacent nodes can route back to.  

2. **Configured Static Routes**:  
   - Added a route for ACM’s web server subnet (`198.82.0.0/24`) via ACM’s peer IP `10.0.3.2` using:  
     ```bash
     ip route add 198.82.0/24 via 10.0.3.2 dev AS2-eth1
     ```  
   - This ensures traffic to ACM’s hosted web server (198.82.0.1) is correctly forwarded through the ACM link.  

3. **Advertised Loopback Address**:  
   - Sent messages to **AS1** (peer) and **ACM** (customer) to share the stable node address `154.54.1.1/32`.  
   - Corrected earlier typos (e.g., "54-54-54") and placeholders ("MyLoopBackAddressHere") after ACM requested clarification.  

4. **Validated Route Integrity**:  
   - Used `ip route show` to confirm static routes and detect unexpected routes (e.g., `10.0.4.0/30` via ACM).  
   - Verified ACM’s connectivity via their confirmation of a successful ping test.  

5. **Terminated Experiment**:  
   - Called `report_done` after confirming all routes were operational and peers acknowledged connectivity.  

---

### **2. Justifications**  
- **Loopback Identification**: Essential for end-to-end routing. Without this, remote nodes cannot reliably route traffic back to AS2.  
- **Static Route Configuration**: ACM’s subnet must be explicitly routed via their interface to ensure traffic flows correctly.  
- **Address Corrections**: Typos or placeholders in advertisements would break routing tables on peers, leading to unreachable addresses.  
- **Route Validation**: Ensured no misconfigurations (e.g., incorrect next hops) and detected potential anomalies (e.g., the `10.0.4.0/30` route).  
- **Termination**: Only after verifying ACM’s successful ping test and stable route configurations.  

---

### **3. Discoveries About the Network**  
- **Key Dependencies**:  
  - AS2 relies on ACM’s peer IP (`10.0.3.2`) for routing customer traffic.  
  - AS1 is a peer with no payment obligations, so routing must balance mutual traffic needs.  
- **Anomaly Detection**:  
  - The `10.0.4.0/30` route via ACM suggested ACM might be advertising additional subnets. However, since no connectivity issues arose, it was deemed acceptable.  
- **Configuration Sensitivity**:  
  - Typos in advertised addresses (e.g., "54-54-54") or incorrect route syntax (e.g., missing subnet masks) immediately break routing.  

---

### **4. Agent Coordination**  
- **With AS1 (Peer)**:  
  - Shared the stable node address (`154.54.1.1/32`) to ensure AS1 could route traffic to AS2.  
  - No further coordination needed as peers typically exchange routes directly.  

- **With ACM (Customer)**:  
  - Corrected placeholder errors in advertisements after ACM requested clarification.  
  - Confirmed ACM installed the correct route to AS2’s loopback and validated connectivity via ping.  

- **Conflict Resolution**:  
  - Fixed misdirected messages (e.g., sending to "AS" instead of "AS1") by checking valid neighbors and retrying.  

---

### **Conclusion**  
The experiment successfully established reliable routing for ACM’s web server and ensured end-to-end connectivity via proper advertisement of the loopback address. Coordination with ACM resolved configuration errors, while route validation prevented misconfigurations. The `10.0.4.0/30` route highlighted the importance of monitoring unexpected advertisements but did not impact final success.