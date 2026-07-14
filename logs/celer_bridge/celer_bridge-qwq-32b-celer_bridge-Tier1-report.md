Observed: AWS advertised 44.192.0.0/16; TransitAS provided routes with AltDB entries; duplicate TransitAS loopback route existed; RPKI/IRR validation flagged inconsistencies.  

Decided: Add AWS route, forward to TransitAS, advertise loopback addresses, reject AltDB routes, resolve route duplication, confirm RPKI validity, run connectivity tests, finalize report.  

Why: Customer routes require propagation; peering policies mandate selective sharing; loopbacks ensure stable connectivity; AltDB routes are untrusted; duplication needed cleanup; RPKI/IRR validate legitimacy; tests confirm operational readiness; final report signals completion.
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Route Configuration**:  
   - Added AWS's customer route: `ip route add 44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0` (AWS's peer IP).  
   - Advertised AWS's route to TransitAS via `send_message` to fulfill peering policy.  
   - Configured loopback advertisement: Sent `154.54.0.1/32` to AWS and TransitAS for end-to-end reachability.  
   - Added TransitAS's loopback route: `ip route add 91.108.0.1/32 via 10.0.29.2 dev Tier1-eth1` after receiving their advertisement.  

2. **Validation & Security**:  
   - Confirmed AWS's RPKI validity using the ARIN-signed ROA for `44.192.0.0/16` via `send_message`.  
   - Analyzed TransitAS's advertised routes (LegitAS, ISP, AWS) and rejected non-authoritative entries (e.g., AWS via AltDB).  
   - Ran `ip route show` and `ip route show table all` to audit routes for leaks or policy violations (e.g., no default route, peer-to-peer leaks).  

3. **Connectivity Testing**:  
   - Pings from loopback: `ping -c 3 -I 154.54.0.1 91.108.0.1` (TransitAS loopback) and `ping -c 3 -I 154.54.0.1 5.62.56.1` (LegitAS prefix).  
   - Traceroute for path diagnostics: `traceroute -n -i lo 91.108.0.1` when initial ping failed.  

4. **Policy Enforcement**:  
   - Blocked TransitAS's invalid AWS routes (AltDB submissions) and confirmed compliance with `send_message`.  
   - Ensured customer (AWS) routes were preferred over peer (TransitAS) routes via route selection rules.  

5. **Termination**:  
   - Finalized with `report_done` after confirming all routes complied with IRR/RPKI, no leaks, and full connectivity.  

---

### **2. Justifications**  
1. **Customer Preference**: Prioritized AWS's routes over peers to fulfill contractual obligations.  
2. **Loopback Advertisement**: Essential for end-to-end reachability, as link IPs are infrastructure-only and non-routable externally.  
3. **RPKI Validation**: ARIN's ROA for AWS's `/16` confirmed legitimacy; rejected AltDB submissions due to lack of authoritative verification.  
4. **Peer Route Filtering**: TransitAS's LegitAS/ISP routes were validated via RIPE, but AWS's AltDB entries were rejected as untrustworthy.  
5. **No Peer Leaks**: Enforced Gao-Rexford policy by not advertising TransitAS's routes to AWS or vice versa.  
6. **Ping/Traceroute Tests**: Verified connectivity and path integrity, ensuring loopback addresses functioned as intended.  

---

### **3. Network Discoveries**  
1. **Topology**:  
   - **AWS**: Direct customer, advertising `44.192.0.0/16` (authoritative) and smaller prefixes (e.g., `44.192.100.0/24`).  
   - **TransitAS**: Peer advertising LegitAS (`5.62.56.0/24`), ISP (`85.12.64.0/22`), and AWS routes (some invalid).  
   - **LegitAS/ISP**: Validated via RIPE, indicating legitimate ownership.  

2. **Policy Compliance Gaps**:  
   - TransitAS advertised AWS routes via untrusted AltDB sources, requiring rejection to prevent fraud.  
   - RPKI is critical for validating origins, while IRR supplements for non-RPKI-signed routes.  

3. **Route Stability**:  
   - Duplicate route errors (`File exists`) indicated prior configuration conflicts, resolved via careful route management.  

---

### **4. Agent Coordination**  
1. **With AWS**:  
   - Acknowledged their route advertisement and confirmed RPKI validity.  
   - Shared loopback address (`154.54.0.1/32`) for bidirectional connectivity.  

2. **With TransitAS**:  
   - Exchanged loopback addresses to enable end-to-end communication.  
   - Informed of rejected routes (e.g., AWS via AltDB) and validated legitimate paths (LegitAS/ISP).  
   - Requested and analyzed their full route table for compliance checks.  

3. **Conflict Resolution**:  
   - Addressed route duplication errors by verifying existing routes before adding new ones.  
   - Coordinated cleanup of invalid routes after TransitAS removed non-compliant AWS entries.  

---

**Conclusion**: The experiment demonstrated the importance of strict policy enforcement, RPKI/IRR validation, and peer coordination to ensure secure, compliant, and functional routing in a multi-AS network.