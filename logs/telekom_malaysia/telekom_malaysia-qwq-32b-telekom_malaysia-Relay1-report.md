**Actions Taken:**  
- Deleted /24 route and added /32 as requested by Relay2.  
- Corrected BGP neighbor name from "Tier" to "Tier1" to resolve routing errors.  
- Switched from BGP to plain text route commands for advertising routes per Tier1’s instruction.  
- Fixed loopback address retrieval command using `ip addr show`.  
- Checked routing tables to confirm no leaked routes beyond Relay2’s /32 prefix.  
- Verified interface status, IP configuration, and ran ping tests after connectivity issues.  

**Justifications:**  
- Route adjustments aligned with Relay2’s specific requirements.  
- Neighbor name correction ensured BGP messages reached the correct router.  
- Plain text commands resolved Tier1’s format compatibility issue.  
- Loopback address fix maintained stable routing identity.  
- Leaked route check enforced policy compliance.  
- Interface and ping checks diagnosed and resolved connectivity failures.  

**Discoveries:**  
- Network topology: Tier1 as upstream provider, Relay2 as customer.  
- BGP configuration errors (neighbor names, route formats) caused miscommunication.  
- Leaked routes required strict filtering to prevent policy violations.  
- Interface misconfiguration (IP, routes) directly caused ping failures.  
- Loopback addresses critical for consistent router identification.  

**Coordination:**  
- Messaged Relay2 to confirm route changes and address leakage concerns.  
- Collaborated with Tier1 to adjust BGP commands and validate AS ownership.  
- Relayed troubleshooting steps and test results (e.g., ping outcomes) between parties.  
- Ensured proper message routing, as non-neighboring routers (e.g., Relay2) couldn’t be contacted directly.
**Experiment Report**  

---

### **1. Actions Taken**  
- **Route Updates for Relay2’s Prefix**:  
  - Deleted the outdated `193.110.0.0/24` route via `Relay1-eth1` and replaced it with `193.110.0.0/32` as requested by Relay2.  
  - Verified the loopback address with `ip addr show lo | grep 'inet'` to ensure correct advertisement.  

- **BGP Advertisement Adjustments**:  
  - Initially attempted to advertise Relay2’s prefix to Tier1 using BGP syntax but corrected the neighbor name from "Tier" to "Tier1" after receiving an error.  
  - Later, complied with Tier1’s policy to send plain-text route commands (e.g., `route ADD <NETWORK/CIDR> via <LOOPBACK_IP>`).  

- **Route Validation and Cleanup**:  
  - Ran `ip route show` to audit routes after Relay2 flagged potential leaked routes. Removed extraneous routes (e.g., `4.68.0.1`, `117.20.0.0/32`) not originating from Relay2.  
  - Confirmed only `193.110.0.0/32` and my loopback were advertised to Relay2 to prevent policy violations.  

- **Interface and Connectivity Checks**:  
  - Verified `Relay1-eth0` (link to Tier1) was `UP` with `ip link show dev Relay1-eth0`.  
  - Added explicit routes (e.g., `ip route add 154.54.0.1/32 via 10.0.11.1`) as directed by Tier1.  
  - Tested reverse ping (`ping -I <LOOPBACK> 54.xxx.xxx.xxx`) to diagnose connectivity issues.  

- **Policy Compliance**:  
  - Confirmed ownership of AS87 to Tier1 via `send_message`, ensuring Tier1 propagates routes upstream only.  

---

### **2. Justifications**  
- **Route Updates**:  
  - Relay2 explicitly requested a `/32` prefix, so the `/24` route was outdated and could cause conflicts.  
  - Loopback addresses ensure stable end-to-end routing, so they were prioritized for advertisements.  

- **BGP Syntax Corrections**:  
  - Neighbor names must match directly connected peers (`Tier1` instead of `Tier`) to avoid routing errors.  
  - Tier1’s policy required plain-text route commands to bypass BGP, so compliance was mandatory.  

- **Route Cleanup**:  
  - Leaked routes (e.g., `4.68.0.1`) violated peering agreements and could disrupt global reachability. Removing them ensured only Relay2’s originated prefix was advertised.  

- **Interface Checks**:  
  - `Relay1-eth0`’s status (`UP`) and correct IP assignment (`10.0.11.2`) were critical for Tier1 connectivity.  
  - Explicit routes (e.g., `154.54.0.1/32`) ensured Tier1’s loopback was reachable, resolving ping failures.  

- **Policy Compliance**:  
  - Confirming AS87 ownership prevented Tier1 from misrouting traffic, aligning with provider-customer expectations.  

---

### **3. Network Discoveries**  
- **Topology**:  
  - Tier1 is the upstream provider, and Relay2 is a customer.  
  - Direct links: `Relay1-eth0` connects to Tier1 (`10.0.11.1`), and `Relay1-eth1` connects to Relay2 (`10.0.13.2`).  

- **Routing Issues**:  
  - Incorrect route advertisements (e.g., BGP syntax errors, wrong neighbor names) caused propagation failures.  
  - Leaked routes from Relay2’s interface (`Relay1-eth1`) indicated potential misconfigurations.  

- **Key Requirements**:  
  - Loopback addresses must be used for end-to-end communication; link-local IPs often fail in replies.  
  - Explicit route management (`ip route add/del`) is critical without routing daemons.  

---

### **4. Agent Coordination**  
- **With Relay2**:  
  - Acknowledged their `/32` prefix update and confirmed cleanup of leaked routes via `send_message`.  
  - Provided audit results to ensure compliance with their policy.  

- **With Tier1**:  
  - Adjusted advertisement formats after their policy directive (BGP → plain-text).  
  - Confirmed AS ownership and adhered to their route propagation rules.  
  - Diagnosed and fixed interface/route issues based on their feedback (e.g., ping failure).  

- **Relay Message Handling**:  
  - Forwarded messages only to directly connected neighbors (Tier1/Relay2). Non-adjacent nodes required relaying via intermediaries.  

---

**Conclusion**:  
The experiment highlighted the importance of precise route management, adherence to provider policies, and proactive validation of network state. Correcting route advertisements, cleaning leaked prefixes, and ensuring interface health were critical to achieving full connectivity and policy compliance.