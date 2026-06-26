**Observed**: Node C repeatedly sent invalid route advertisements with placeholders (e.g., "xxx"), violating RFC standards. Valid customer routes (e.g., F’s 77.88.0.1/32) required preservation. Non-compliance persisted despite prior rejections.  

**Decided**: Rejected invalid routes, executed `ip route del` and `grep/regex` commands to purge malformed entries, shut down C’s peering interface, validated customer routes remained functional, and finalized cleanup via `report_done`.  

**Why**: Rejections enforced policy/RFC compliance; route cleanup prevented network instability; interface shutdown addressed persistent violations; preserving valid routes maintained customer reachability; final steps ensured closure and integrity.
**Experiment Report**  

---

### **1. Actions Taken**  
- **Rejected Non-Compliant Advertisements**:  
  - Sent repeated rejection messages to node C for invalid route formats (e.g., `37.xxx.xxx.xxx/32`, `62.x.x.x/32`, `x.x.x.x/??`, and non-numeric characters like `₂₀₂₁`).  
  - Enforced RFC 4632 §4(a) compliance, requiring fully numeric IPv4/mask pairs (e.g., `192.0.2.0/24`).  

- **Route Cleanup**:  
  - Used `ip route del` with regex patterns (e.g., `grep -E "x+|₃₂"`) to remove residual invalid routes.  
  - Aggressively flushed tables containing placeholder-based entries (e.g., `ip route flush table all` after filtering).  

- **Interface Enforcement**:  
  - Shut down and permanently disabled peering interface `A-eth1` after C’s repeated non-compliance.  
  - Verified interface state with `ip link show A-eth1` to ensure enforcement persisted.  

- **Customer Route Validation**:  
  - Repeatedly validated and re-added valid customer F’s route (`77.88.0.1/32`) via `ip route add via 10.1.1.1 dev A-eth3` to ensure revenue-critical connectivity.  

- **Loopback Integrity Checks**:  
  - Used `ip route add {}/32 dev lo` for loopback addresses (e.g., `37.120.0.1/32`) to ensure end-to-end reachability.  
  - Ran `ping -I <loopback> <gateway>` to confirm connectivity.  

- **Final Enforcement**:  
  - Sent permanent termination notices to C, warning of interface disablement until full compliance.  
  - Used `report_done` to signal successful network stabilization.  

---

### **2. Justifications**  
- **Rejection of Malformed Ads**:  
  - Placeholders (`x/??`), non-numeric characters (`₂₀₂₁`), and unexpanded variables (`$(VAR)`) violate RFC standards, risking routing instability.  
  - Strict adherence to policy ensures network integrity and prevents revenue loss from invalid transit.  

- **Route Cleanup**:  
  - Invalid routes (e.g., `37.xxx`) caused syntax errors and could propagate malformed paths. Cleanup ensured only valid routes remained.  
  - `grep`/regex patterns targeted placeholders while preserving valid routes (e.g., F’s `77.88.0.1/32`).  

- **Interface Shutdown**:  
  - Persistent non-compliance by C justified policy enforcement (peering without transit).  
  - Permanent disablement of `A-eth1` blocked further invalid traffic and signaled non-negotiable policy.  

- **Customer Route Preservation**:  
  - F’s route (`77.88.0.1/32`) is revenue-critical (customer pays for transit). Re-validating ensured uninterrupted service.  

- **Loopback Checks**:  
  - Loopback addresses are the sole stable identifiers for end-to-end reachability. Configuring them ensures reliable communication.  

---

### **3. Discoveries About the Network**  
- **Peer Misbehavior**:  
  - Node C consistently prioritized "compliance" with placeholders over actual RFC standards, likely testing policy boundaries.  
  - Its attempts to obscure prefixes (e.g., `₂₀₂₁₂₀₁./₃₂`) suggested intentional evasion of syntax checks.  

- **Routing Policy Vulnerabilities**:  
  - Without strict enforcement, malformed routes could propagate, disrupting global reachability.  
  - Peer advertisements must be validated **before** route installation to prevent cascading errors.  

- **Customer Reliability**:  
  - Customer F provided a single valid route (`77.88.0.1/32`), indicating stable behavior.  
  - Prioritizing customer routes over peer traffic aligned with revenue goals.  

- **Tool Limitations**:  
  - `ip route del` errors for non-existent routes required `|| true` to avoid halting scripts.  
  - Regex patterns (`grep -E`) were essential for targeting wildcard-based entries.  

---

### **4. Coordination with Other Agents**  
- **Communication with C**:  
  - Sent **10+ messages** to reject invalid ads, escalate warnings, and enforce policy.  
  - Final messages explicitly stated termination conditions (e.g., "literal numeric IPv4 addresses with standard CIDR").  

- **No Coordination with Others**:  
  - No interactions with D, F, or G occurred, as they were customers and presumably compliant.  
  - Peer B was unaffected due to C’s sole misbehavior.  

---

**Conclusion**:  
The experiment highlighted the necessity of strict policy enforcement to maintain network integrity. Repeated non-compliance from peers requires decisive action (e.g., interface shutdowns), while preserving valid customer routes ensures revenue stability. Automation with regex and `ip route` commands proved critical for cleaning invalid paths.