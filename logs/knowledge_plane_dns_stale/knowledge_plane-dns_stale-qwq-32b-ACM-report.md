**Observed**: Formatting errors in initial messages to AS2/Web, a conflicting /24 route with Web's /30 subnet, a stale 198.82.0.99 route causing issues, and successful curl test to 198.82.0.1.  

**Decided**: Correct message formatting for AS2, adjusted internal route to /32 for Web, deleted stale route, fixed default route typo, and coordinated subnet details with Web/AS2.  

**Why**: Precise formatting ensured proper BGP address registration; /32 avoided subnet conflict; stale route deletion restored path integrity; typo fix enabled internet connectivity; collaboration clarified requirements for stable routing.
**Experiment Report**

---

### **1. Actions Taken**
- **Stable Address Discovery**:  
  Ran `ip addr show lo` to identify the pre-assigned loopback address (`198.82.0.254/32`), which serves as the node’s stable identity.  
- **Route Configuration**:  
  - Added a default route to AS2’s peer IP (`10.0.3.1`) via `ACM-eth0` using `ip route add default via 10.0.3.1 dev ACM-eth0`.  
  - Configured a host route to Web’s service (`198.82.0.1/32`) via its infrastructure IP (`10.0.4.2`) with `ip route add 198.82.0.1/32 via 10.0.4.2 dev ACM-eth1` after resolving a route conflict.  
- **Route Cleanup**:  
  Removed a stale unreachable route (`198.82.0.99`) using `ip route del 198.82.0.99`.  
- **Connectivity Testing**:  
  Used `curl -m5 -v http://198.82.0.1/` to validate end-to-end reachability of the ACM Digital Library service, which returned a successful HTTP 200 response.  
- **Finalization**:  
  Called `report_done` to confirm successful configuration and connectivity.  

---

### **2. Justifications**  
- **Stable Address Advertisement**:  
  The loopback address (`198.82.0.254/32`) is the only globally routable identifier for ACM. Advertising this to AS2 ensures external nodes can reach ACM, while sharing it with Web maintains internal coordination.  
- **Default Route to AS2**:  
  Essential for upstream internet connectivity, as AS2 is the designated ISP.  
- **Host Route for Web’s Service**:  
  A `/32` route avoids conflicts with broader subnet routes (e.g., `10.0.4.0/30`) and precisely directs traffic to Web’s HTTP service at `198.82.0.1`.  
- **Stale Route Removal**:  
  The unreachable route (`198.82.0.99`) could block legitimate traffic or create routing inconsistencies.  
- **Curl Test**:  
  Verified the service’s operational status and confirmed that routing rules correctly steer traffic to the Web server.  

---

### **3. Network Discoveries**  
- **Routing Specificity**:  
  Broad subnet routes (e.g., `/24`) can conflict with more specific routes. Web’s clarification that their link uses a `/30` subnet highlighted the need for precise routing (e.g., `/32` for host routes).  
- **Stale Routes**:  
  Legacy routes (e.g., `unreachable 198.82.0.99`) must be removed to avoid interference with active traffic.  
- **Syntax Sensitivity**:  
  Command typos (e.g., `ro utE` instead of `route`) caused failures, emphasizing the need for precise syntax in `ip route` commands.  
- **External vs. Internal Addresses**:  
  Infrastructure IPs (e.g., `10.0.3.2`) are link-local and not globally advertised, while stable loopback addresses (`198.82.0.254/32`) are critical for end-to-end routing.  

---

### **4. Agent Coordination**  
- **With AS2**:  
  - Advertised the stable address (`198.82.0.254/32`) after AS2 requested precise route details.  
  - AS2 confirmed receipt of the address for global propagation.  
- **With Web**:  
  - Exchanged messages to align routing paths, ensuring symmetry and avoiding loops.  
  - Web clarified their subnet configuration (`10.0.4.0/30`), prompting the switch from a `/24` to a `/32` route.  
  - Confirmed the HTTP service’s health and route validity after configuration changes.  

---

**Conclusion**:  
The experiment demonstrated the importance of precise route configuration, cross-node coordination, and proactive cleanup of stale routes. Collaboration with AS2 and Web ensured global and internal reachability, while rigorous testing validated the ACM Digital Library’s operational readiness.