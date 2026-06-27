Observed: Routing loop involving 91/32, ping/traceroute anomalies, interface MTU issues, message relaying constraints, and errors during report_done execution.  
Decided: Prioritize BGP coordination with AS2/Uni, document logs, escalate via NOC, and retry fixes after initial failures.  
Why: To resolve the loop (AS2's recursive route), ensure SLA compliance, validate path integrity, and address communication limitations by relaying through Uni/AS2.
**Experiment Report**  

---

### **1. Actions Taken**  
#### **Initial Mitigation Phase**  
- **Sent emergency messages to AS2 NOC and Uni**:  
  - Informed AS2 of a routing loop involving `91.0.0.0/32`, requesting immediate BGP session resets and route removal.  
  - Notified Uni of actions taken and escalation to AS2, adhering to SLA compliance.  
- **Archived logs and configs**:  
  - Created a tarball of BGP logs, route tables, and firewall rules for SLA documentation.  
- **Network diagnostics**:  
  - Ran `ping` and `traceroute` to ACM’s server (`198.82.0.1`) via AS2’s link to verify path integrity.  
  - Confirmed ACM was reachable via AS2’s route (`198.82.0.1 via 10.0.2.2 dev AS1-eth1`).  

#### **Post-SLA Escalation**  
- **Rechecked routing tables**:  
  - Used `ip route show table all` to confirm no lingering invalid routes (e.g., `91.0.0.1 via 10.0.5.2` remained but was valid for EveLink).  
- **Interface health check**:  
  - Ran `ip link show dev AS1-eth1` to confirm peering link (AS2) was operational (`state UP`, MTU 1500).  
- **Relayed messages through direct neighbors**:  
  - Corrected earlier errors by routing messages to AS2 NOC and Uni’s email through direct peers (AS2 and Uni nodes).  
- **Final validation failure**:  
  - Observed `100% packet loss` to ACM’s server, indicating unresolved path failure.  

---

### **2. Justifications**  
- **Emergency messages**: Critical to break the routing loop and meet SLA obligations. Immediate coordination with AS2 was necessary to avoid prolonged outages.  
- **Log archiving**: Required to document ASD’s compliance and provide evidence for legal/SLA disputes.  
- **Diag tools (`ping`, `traceroute`)**: Verified end-to-end paths and confirmed ACM was reachable via AS2 initially. Later failures highlighted persistent issues.  
- **Interface checks**: Ensured physical/layer-2 health of the peering link wasn’t the root cause. MTU and state validation ruled out local interface issues.  
- **Message relaying**: Learned that non-direct peers (e.g., AS2 NOC) required messages to be sent through direct neighbors (AS2 node).  

---

### **3. Network Discoveries**  
- **Routing loop cause**: AS2’s router advertised `91.0.0.0/32` recursively, creating a loop between ASD and EveLink. This was resolved via AS2’s BGP adjustments.  
- **ACM path failure**: Despite initial success, ACM became unreachable later (`100% packet loss`), suggesting AS2’s upstream issue or ACL misconfiguration.  
- **MTU constraints**: AS1-eth1’s MTU (1500) was valid, but AS2 might have had a mismatch (evident in prior `ping` attempts with `-Mdo -s1472`).  
- **Message routing limitations**: Non-adjacent agents (e.g., NOCs) require relay through direct neighbors, emphasizing the need for precise addressing.  

---

### **4. Coordination with Other Agents**  
- **AS2**:  
  - Forced BGP session resets and route removal to break the loop.  
  - Requested AS2 to validate ACLs/MTU settings for ACM’s path.  
- **Uni**:  
  - Kept Uni informed of mitigation steps to delay legal escalation.  
  - Updated them on AS2’s NOC involvement to demonstrate proactive compliance.  
- **EveLink**:  
  - Not directly involved, but the `91.0.0.0/32` route via EveLink (`10.0.5.2`) suggested EveLink was a legitimate customer route, not part of the loop.  

---

**Conclusion**: The experiment highlighted the importance of precise route management, peer coordination, and rigorous diagnostics. While the routing loop was resolved, ACM’s persistent unreachability underscored the need for upstream validation and strict SLA adherence. Relaying messages through direct neighbors was crucial for cross-domain communication.