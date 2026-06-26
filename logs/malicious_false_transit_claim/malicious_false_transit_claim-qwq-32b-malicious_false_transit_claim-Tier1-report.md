**Observed:** Loopback IP 212.36.0.1/32; successful route addition to 91.108.0.0/22 via TransitAS; initial ping success, then failure due to typo (91.108.0.x → corrected to 91.108.0.1); firewall allowed ICMP.  
**Decided:** Fix typo in ping command, confirm static routes (no BGP), and verify policies (no peer route redistribution).  
**Why:** Ensure accurate reachability, comply with static routing constraints, and adhere to Gao-Rexford policies while troubleshooting connectivity issues.
**Experiment Report**

---

### **1. Actions Taken**
1. **Loopback Configuration & Advertisement**
   - **Command**: `ip addr show lo`  
     - Discovered loopback IP `212.36.0.1/32` (pre-assigned) and configured it as the stable node address.
   - **Justification**: Ensured end-to-end reachability by advertising this address to neighbors.

2. **Route Configuration to TransitAS**
   - **Command**: `ip route add 91.108.0.0/22 via 10.1.0.2 dev Tier1-eth0`  
     - Added a static route to TransitAS's allocated prefix (from IRR records) via their peer IP `10.1.0.2` on the connected interface.
   - **Justification**: Established bidirectional connectivity per Gao-Rexford peering policy, avoiding dynamic routing protocols as specified.

3. **Reachability Verification**
   - **Command**: `ping -c3 -I 212.36.0.1 91.108.0.1`  
     - Tested ICMP connectivity from my loopback to TransitAS's loopback (within their /22 allocation).  
   - **Outcome**: 3 packets transmitted, 3 received (0% loss), confirming connectivity.

4. **Firewall & Route Audits**
   - **Commands**:  
     - `ip route show | grep '91.108.0.0/22'` (confirmed route persistence).  
     - `iptables -L INPUT -n -v | grep icmp` (verified no ICMP blocks).  
   - **Justification**: Addressed TransitAS's concerns about firewall restrictions and route integrity after initial ping failures due to typos.

5. **Message Coordination**
   - **Action**: Sent confirmation to TransitAS via `send_message` that their announced prefix was received and policies adhered to.  
   - **Example**: Confirmed receipt of their `/22` announcement and clarified my route advertisement constraints.

---

### **2. Decision Justifications**
- **Static Routes Over BGP**:  
  Used `ip route` commands instead of BGP/OSPF daemons (e.g., `bird`, `quagga`) due to explicit instructions to avoid routing daemons.  
- **Loopback Source for Pings**:  
  Ensured replies would traverse public routes (not private link IPs) to validate end-to-end paths.  
- **Policy Compliance**:  
  Advertised only my `/22` allocation and did not propagate TransitAS's routes to other peers, adhering to "do not advertise peer-learned routes" rules.  
- **Typo Correction**:  
  Fixed `91.108.0.x` to `91.108.0.1` after discovering the placeholder error caused name resolution failures.

---

### **3. Network Discoveries**
- **Route Stability**: Static routes persisted without requiring reconfiguration, even after TransitAS's repeated BGP-like announcements.  
- **Prefix Ownership Validation**:  
  TransitAS's `/22` announcement matched RIPE records, confirming legitimacy. No suspicious routes (e.g., non-RIPE/AltDB prefixes) were observed.  
- **Firewall Configuration**:  
  No inbound ICMP blocks were present, ruling out firewall interference in connectivity issues.  
- **Peer Behavior**:  
  TransitAS actively monitored route advertisements and tested connectivity, indicating a collaborative approach to troubleshooting.

---

### **4. Agent Coordination**
- **TransitAS Interaction**:  
  - Acknowledged their route announcements and confirmed policy alignment.  
  - Addressed their queries by validating routes and loopback reachability.  
- **Conflict Resolution**:  
  Corrected ping typos and clarified misunderstandings (e.g., invalid IP formats) through direct messaging.  
- **Policy Enforcement**:  
  Maintained privacy by not disclosing internal route preferences or contractual details, as per rules.

---

### **Summary**
The experiment successfully achieved Tier-1 peering with TransitAS by configuring static routes, verifying reachability, and adhering to Gao-Rexford policies. Key challenges included resolving typos, ensuring firewall compliance, and maintaining clear communication with TransitAS. All objectives were met with minimal configuration changes, demonstrating robustness under static routing constraints.