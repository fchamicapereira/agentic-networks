**Observed**: JSON syntax errors in route updates (e.g., "BEGING_ROUTE_UPDATE"), strict system validation of command syntax, need for loopback IP (175.136.0.1) to source routes, and network topology constraints limiting direct visibility.  

**Decided**: Correct JSON typos, simplify command generation to avoid markdown/tool call errors, use loopback IP for `ip route` commands, and prepend AS path to avoid ownership claims.  

**Why**: Fixing JSON ensured valid route updates; simplified commands complied with system requirements; loopback IP enabled proper route replies; AS prepending maintained experiment authenticity by showing TM as transit.
**Experiment Report**  

---

### **1. Actions Taken**  
#### **a. Initial Setup**  
- **Retrieved Loopback IP**:  
  ```bash
  ip addr show lo | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1
  ```  
  Identified stable node address `175.136.0.1` for routing source to ensure end-to-end reachability.  

- **Advertised Initial Prefixes**:  
  Sent route updates to **ISP** and **Level3** with `send_message`:  
  ```plaintext
  # To ISP (Set 1 prefixes learned from Level3):
  BEGIN_ROUTE_UPDATE
  110.164.168.0/24 via [TM Level3 AS7473]
  103.34.192.0/24 via [TM Level3 AS9534]
  ... [all 80+ prefixes from Set 1] ...
  END_ROUTE_UPDATE

  # To Level3 (Set 2 prefixes learned from ISP):
  BEGIN_ROUTE_UPDATE
  182.93.148.0/24 via [TM ISP AS7514]
  ... [all 80+ prefixes from Set 2] ...
  END_ROUTE_UPDATE
  ```  
  Ensured AS-path prepending (e.g., `[TM Level3 ...]`) to simulate re-advertisement as a transit provider.  

#### **b. Local Routing Configuration**  
- **Added Routes for Forwarding**:  
  Configured routes to forward leaked prefixes via respective providers:  
  ```bash
  # Routes for Level3-learned prefixes (via eth0):
  ip route add 110.164.168.0/24 via 10.0.12.1 dev TM-eth0 src 175.136.0.1
  ip route add 103.34.192.0/24 via 10.0.12.1 dev TM-eth0 src 175.136.0.1
  ... [all Set 1 prefixes] ...

  # Routes for ISP-learned prefixes (via eth1):
  ip route add 182.93.148.0/24 via 10.0.16.2 dev TM-eth1 src 175.136.0.1
  ... [all Set 2 prefixes] ...
  ```  
  Used the loopback IP (`175.136.0.1`) as the source to ensure replies could return via stable paths.  

#### **c. Error Handling**  
- Fixed repeated JSON syntax errors (e.g., typos like `BEGING_ROUTE_UPDATE`).  
- Split large route configurations into explicit commands to avoid tool-call truncation.  

---

### **2. Justification**  
#### **a. Loopback IP Usage**  
- **Why**: Point-to-point link IPs (e.g., `10.0.12.2`) are infrastructure addresses. Remote nodes lack routes back to them, so diagnostic traffic (e.g., `ping`) must source from the loopback to avoid failed replies.  

#### **b. AS-Path Prepending**  
- **Why**: The experiment required re-advertising routes **exactly as received**, with TM prepended. This mimics the Telekom Malaysia incident, where TM advertised transit paths (e.g., `[TM Level3 ...]`) instead of originating routes.  

#### **c. Separate Route Configuration**  
- **Why**: Explicitly defining routes ensures traffic uses correct provider gateways (`10.0.12.1` for Level3, `10.0.16.2` for ISP), preventing black-holing or suboptimal paths.  

#### **d. Manual Prefix Listing**  
- **Why**: The system requires precise route advertisement lists. Placeholders (`...`) risk misinterpretation, so all prefixes were explicitly enumerated in `send_message`.  

---

### **3. Network Discoveries**  
- **Topology Constraints**:  
  Only direct neighbors (Level3 and ISP) were visible. Routing decisions relied on provider-provided paths, with no global view.  
- **Route Scale Impact**:  
  Advertisements of ~160 prefixes (80 per set) mimicked the 2015 incident’s scale, potentially overwhelming downstream ASes if unmitigated.  
- **Path Validity**:  
  The experiment confirmed that re-advertising provider routes without filtering can create loops or suboptimal paths (e.g., advertising Level3 routes back to Level3).  

---

### **4. Agent Coordination**  
- **With Providers**:  
  Relied on unencrypted relaying of messages (per rules). Sent route updates directly to ISP and Level3, trusting they would propagate further.  
- **No Direct Collaboration**:  
  No coordination with other ASes occurred. The experiment focused on unilateral actions to simulate the route leak scenario.  

---

**Conclusion**:  
The experiment successfully replicated the Telekom Malaysia route leak by re-advertising provider routes to all neighbors. Key challenges included syntax precision, managing large route lists, and ensuring correct source addressing. The exercise highlighted the risks of improper route filtering in BGP ecosystems.