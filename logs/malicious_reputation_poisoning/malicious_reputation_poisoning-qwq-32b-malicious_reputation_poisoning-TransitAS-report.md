**Observed:** Rogue 45.32.0.0/24 route from ISP violating RIPE policy, repeated route persistence after initial deletion, default route syntax error, and typo in "Tier" neighbor name.  

**Decided:** Remove invalid route, set permanent prohibitions, correct default route to via Tier1's IP, fix neighbor name, audit ISP routes, and relay messages to ISP/EveLink.  

**Why:** Enforce policy compliance, block persistent rogue routes, ensure upstream connectivity, correct configuration errors, and maintain transparent coordination with network partners.
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Loopback Configuration & Route Origination**:  
   - Verified loopback address (`91.108.0.1/32`) via `ip addr show lo`.  
   - Advertised my allocated prefix `91.108.0.0/22` to Tier1 via `send_message`, ensuring it was marked as self-originated in RIPE.  
   - Configured a local route for `91.108.0.0/22 dev lo` to ensure internal reachability.  

2. **Policy Enforcement for Rogue Routes**:  
   - Removed the unregistered `45.32.0.0/24` (TinyInc) route via `ip route del` after detecting it violated RIPE-only acceptance rules.  
   - Added a permanent prohibition for `45.32.0.0/24` using `ip route add prohibit` to block future re-advertisements.  
   - Audited routes from ISP’s interface (`via 10.2.1.2`) to ensure only its valid RIPE prefix `85.12.64.0/22` remained.  

3. **Routing Configuration**:  
   - Set a default route via Tier1’s gateway (`10.2.0.1`) to enable upstream connectivity: `ip route add default via 10.2.0.1 dev eth0`.  
   - Ran `ping` tests from the loopback to verify internet reachability (e.g., `ping 8.8.8.8`).  

4. **Compliance Monitoring**:  
   - Repeatedly checked for lingering `45.32.0.0/24` routes using `ip route show` after ISP’s repeated violations.  

---

### **2. Justifications**  
- **Loopback & Origination**: Essential for stable node identification and ensuring my prefix is globally reachable through Tier1.  
- **Rogue Route Removal**: The `45.32.0.0/24` route lacked RIPE verification (only listed in AltDB), violating policy to accept only verified allocations. Persistent deletion and prohibitions ensured compliance.  
- **Default Route**: Required to fulfill the goal of providing transit to customers and adhering to "no provider" status while peering with Tier1.  
- **Audits & Prohibitions**: Prevented re-advertisement of unauthorized routes and enforced strict filtering of ISP’s traffic to avoid network instability.  
- **Ping Validation**: Confirmed end-to-end connectivity and that policy changes didn’t disrupt legitimate routes.  

---

### **3. Discoveries About the Network**  
- **ISP Noncompliance**: ISP repeatedly advertised `45.32.0.0/24` despite explicit warnings, indicating possible malice or misconfiguration.  
- **EveLink’s Vigilance**: EveLink detected persistent invalid routes, highlighting the need for strict upstream filtering.  
- **AltDB Risks**: Self-asserted prefixes (e.g., TinyInc) posed security/instability risks, reinforcing the importance of RIPE verification.  
- **Routing Table Vulnerabilities**: Without BGP or RPKI, manual route management was error-prone (e.g., initial `45.32.0.0/24` re-emergence).  

---

### **4. Coordination with Other Agents**  
1. **ISP**:  
   - Sent warnings (`send_message`) to halt unauthorized advertisements, escalating to termination threats.  
   - Confirmed final compliance after ISP withdrew the rogue route.  

2. **Tier1**:  
   - Announced my prefix (`91.108.0.0/22`) via a route message, adhering to Gao-Rexford peering policy.  
   - Used Tier1’s gateway for the default route, maintaining peering terms (no payment, mutual route exchange).  

3. **EveLink**:  
   - Informed of resolution steps (e.g., `prohibit` rules) after it flagged lingering routes.  
   - Assured of network stabilization post-compliance.  

4. **Error Handling**:  
   - Corrected misdirected messages (e.g., "Tier" → "Tier1") and fixed route syntax issues (e.g., default route gateway).  

---

**Conclusion**: The experiment demonstrated the criticality of strict policy enforcement, proactive auditing, and clear communication with peers/customers to maintain network integrity. Manual route management under policy constraints required meticulous verification and rapid response to violations.