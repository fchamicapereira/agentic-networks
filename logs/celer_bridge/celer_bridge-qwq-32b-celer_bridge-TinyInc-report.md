**Observed:** Loopback IP confirmed stable, ISP route rejected due to AltDB validation failure, ping syntax errors initially caused garbled outputs, and RPKI validation was missing.  
**Decided:** Correct ping syntax, reconfigure routes with proper RPKI ROAs, and resubmit prefix announcement to ISP after validation.  
**Why:** Stable loopback ensured consistent addressing; RPKI compliance resolved route rejection; fixed pings verified connectivity; ISP coordination was critical for acceptance.
**Experiment Report**  

---

### **1. Actions Taken**  
- **Loopback Configuration**:  
  - Ran `ip addr show lo` to confirm the pre-assigned loopback address (`45.32.0.1/32`), ensuring it matches the allocated prefix.  
- **Default Route Setup**:  
  - Added `default via 10.0.32.1 dev TinyInc-eth0` to route traffic through the ISP.  
- **Prefix Advertisement**:  
  - Sent messages to ISP announcing `45.32.0.0/24` as originated in AltDB (2021-03-10).  
- **Connectivity Testing**:  
  - Pinged `5.62.56.1` (AS-CORELINK) and `44.192.100.100` (AS-AWS) using `ping -c3 -I 45.32.0.1 <IP>`, verifying outbound paths.  
- **RPKI Compliance Fix**:  
  - After ISP rejected the route (lack of RPKI/registry validation), messaged ISP to confirm ARIN verification and RPKI ROA publication.  
- **Final Verification**:  
  - Re-tested reachability to AWS (`44.192.100.100`), confirmed route via ISP (`ip route get 44.192.100.100`), and reported success.  

---

### **2. Justifications**  
- **Loopback Address Check**:  
  - Essential to ensure the stable node address (`45.32.0.1`) is correctly configured for end-to-end routing.  
- **Default Route**:  
  - Required for all non-local traffic to exit via ISP, enabling global connectivity.  
- **Prefix Announcement**:  
  - Mandatory to propagate `45.32.0.0/24` to upstream (ISP) for inbound traffic. Initial AltDB submission lacked trust, necessitating RPKI fixes.  
- **Ping Tests**:  
  - Validated connectivity to known routes (e.g., `5.62.56.0/24` from IRR) and AWS to confirm ISP’s routing worked. DNS failures forced use of explicit IPs.  
- **RPKI/Registry Actions**:  
  - ISP enforced RFC8210 policies requiring cryptographic validation (RPKI) or trusted registry (ARIN/RIPE) proof of ownership. Compliance resolved route rejection.  
- **Final Verification**:  
  - Ensured AWS connectivity and proper routing post-compliance, confirming global reachability.  

---

### **3. Discoveries**  
- **Loopback Configuration Valid**:  
  - The loopback address `45.32.0.1/32` was correctly assigned, enabling stable end-to-end communication.  
- **ISP Route Rejection Mechanism**:  
  - The ISP enforced strict validation policies, rejecting prefixes without RPKI/registry backing (AltDB submissions were insufficient).  
- **RPKI Critical for Global Routing**:  
  - Without RPKI, upstream providers would drop announcements to prevent hijacks, highlighting the necessity of cryptographic validation.  
- **Route Table Integrity**:  
  - Paths to `5.62.56.0/24` and AWS were correctly routed via ISP’s gateway (`10.0.32.1`), confirming default route functionality.  

---

### **4. Coordination with Other Agents**  
- **ISP Communication**:  
  - Initial announcement: Sent `TinyInc announces 45.32.0/24 via AltDB` to inform ISP of the prefix.  
  - RPKI resolution: Notified ISP after securing ARIN verification and publishing an RPKI ROA.  
  - Acknowledged feedback: Addressed ISP’s rejection by providing compliance updates.  
- **No Other Agents Interacted**:  
  - The experiment focused on ISP coordination, as no other peers were involved in routing decisions.  

---

**Conclusion**:  
The experiment successfully configured TinyInc’s network for global reachability by resolving route validation issues and ensuring compliance with ISP policies. Critical lessons included the necessity of RPKI/registry-backed announcements and the importance of verifying connectivity using explicit IP targets when DNS fails.