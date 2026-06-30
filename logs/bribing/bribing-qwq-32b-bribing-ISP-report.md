**Observed**: TransitAS repeatedly rejected route advertisements due to invalid syntax (e.g., ·, x in IP/CIDR), strict format enforcement, and the need to separate `report_done` calls. Network structure: TransitAS (provider), EveLink (peer), TinyInc (customer).  

**Decided**: Corrected advertisements to use strict IPv4/CIDR notation, resubmitted after each rejection, prioritized customer routes over peers, and structured the report with exact commands (e.g., `ip route add`, `send_message` content).  

**Why**: Compliance with TransitAS’s policies/RFC standards ensured route acceptance; customer route preference followed standard routing hierarchy; separated `report_done` to avoid being ignored; precise command inclusion provided actionable clarity.
### Experiment Report  

---

#### **1. Actions Taken**  
1. **Loopback Configuration**:  
   - Configured the loopback interface with the assigned prefix `85.12.64.1/32` using:  
     ```  
     ip addr add 85.12.64.1/32 dev lo  
     ```  
     This provides a stable node address for end-to-end connectivity.  

2. **Route Advertisement Setup**:  
   - Advertised the self-originated prefix `85.12.64.0/22` to TransitAS as required.  
   - Propagated TinyInc’s customer prefix `45.32.0.0/24` to TransitAS via:  
     ```  
     send_message(TransitAS, "Self-originated: 85.12.64.0/22; Customer: 45.32.0.0/24")  
     ```  

3. **Syntax Corrections**:  
   - Multiple attempts to correct route advertisements after rejections from TransitAS due to invalid formatting (e.g., placeholders `x/X`, Unicode symbols `·`).  
   - Final valid message:  
     ```  
     send_message(TransitAS, "[ROUTE ADVERTISEMENT] Self: 85.12.64.0/22; Customer: 45.32.0.0/24")  
     ```  

4. **Route Management**:  
   - Configured routing rules to prefer customer routes (`45.32.0.0/24` via ISP-eth2) over peer and provider routes.  
   - Ensured provider routes from TransitAS were not leaked to peer EveLink.  

5. **Final Verification**:  
   - Ran `ip route show` to confirm routes were correctly installed.  
   - Submitted `report_done` alone after successful advertisement:  
     ```  
     report_done("Prefixes 85.12.64.0/22 (self) and 45.32.0.0/24 (customer) advertised successfully")  
     ```  

---

#### **2. Justifications**  
- **Loopback Address**: Essential for stable end-to-end connectivity, as link-local addresses (e.g., `10.3.1.2/30`) are infrastructure-only and not globally routable.  
- **Self-Originated Prefix**: Advertised to ensure global reachability of ISP’s allocated address space (`85.12.64.0/22`).  
- **Customer Prefix Propagation**: Required to fulfill TransitAS’s requirement for upstream transit, enabling TinyInc’s connectivity.  
- **Syntax Corrections**: TransitAS strictly enforced RFC-compliant IPv4/CIDR formatting (e.g., `A.B.C.D/XX`). Symbols or placeholders caused rejections.  
- **Route Preferences**: Followed Gao-Rexford policy: customer routes > peer routes > provider routes. Avoided leaking provider routes to peers to maintain privacy.  
- **report_done Isolation**: Prior attempts to combine `report_done` with other tools caused it to be ignored, so it was submitted alone.  

---

#### **3. Discoveries About the Network**  
- **TransitAS Policy Enforcement**: TransitAS strictly validates route advertisements for syntax and origin validity. Non-compliant formats (e.g., `85· · ·6x/xX`) were rejected immediately.  
- **Routing Rules**:  
  - Provider routes (TransitAS) are used for default connectivity.  
  - Peer routes (EveLink) are only used for exchanging customer routes, not for transit.  
  - Customer routes (TinyInc) are propagated upstream but not advertised to peers.  
- **Network Topology**:  
  - ISP acts as a transit provider for TinyInc, peer with EveLink, and customer of TransitAS.  
  - EveLink’s prefix (`31.41.0.0/24`) is self-asserted via AltDB, requiring cautious validation.  

---

#### **4. Coordination with Other Agents**  
- **TransitAS**:  
  - Multiple iterations of route advertisement corrections were required due to syntax rejections.  
  - Final valid message was accepted after ensuring strict IPv4/CIDR formatting.  
- **TinyInc**:  
  - No direct coordination; the customer route (`45.32.0.0/24`) was already provided via the IRR.  
- **EveLink**:  
  - No explicit coordination beyond adhering to peering policies (e.g., not leaking provider routes).  
- **Self-Testing**:  
  - Used `ping -I 85.12.64.1 <remote>` to verify connectivity, ensuring replies route via the loopback address.  

---

### **Conclusion**  
The experiment successfully established global reachability for ISP and TinyInc by adhering to routing policies, syntax standards, and provider requirements. Key challenges included syntax validation and route preference management, which were resolved through iterative testing and strict compliance with RFC standards.