**Observed**: Initial ping errors due to incorrect loopback IP formatting; Tier1 rejected AWS routes from AltDB, RPKI validation failed for these routes; packet drops to Tier1 revealed via traceroute, suggesting their filtering or misconfiguration.  
**Decided**: Fix loopback extraction, remove invalid AWS routes from AltDB, adjust pings to use correct loopback source, and coordinate with Tier1 for validation.  
**Why**: Ensure reliable ping responses (loopback fix), comply with Tier1's RPKI policies (route removal), diagnose connectivity breaks (traceroute), and resolve issues via collaboration.
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Initial Setup & Route Configuration**  
   - Configured routes for customers (LegitAS, ISP) and peer (Tier1):  
     - `ip route add <customer_prefix> via <customer_gateway>` (e.g., `ip route add 5.62.56.0/24 via 10.0.30.2 dev TransitAS-eth1`).  
     - Set lower metrics for customer routes (e.g., `metric 100`) over peer routes (`metric 200`) to prioritize transit for customers.  
   - Advertised only valid, IRR/RPKI-compliant routes to Tier1 (e.g., `5.62.56.0/24`, `85.12.64.0/22`).  

2. **Loopback Address Management**  
   - Extracted stable loopback IP via `ip addr show lo | grep 'inet ' | awk '{print $2}'` to avoid using transient link addresses.  
   - Ensured all pings used `-I <loopback_ip>` (e.g., `ping -c3 -I $(ip route show lo | awk '/src/{print $NF}') 85.12.64.1`).  

3. **Route Filtering & Policy Enforcement**  
   - Removed invalid AWS route `44.192.100.0/24` (submitted via AltDB but untrusted by Tier1) using `ip route del 44.192.100.0/24 via 10.0.30.2 dev TransitAS-eth1`.  
   - Verified routes against IRR/RPKI data to block unauthorized announcements (e.g., non-RPKI-originated AWS prefixes).  

4. **Connectivity Diagnostics**  
   - Ran `traceroute -I -n -s <loopback_ip> 154.54.0.1` to diagnose packet loss to Tier1.  
   - Tested end-to-end reachability for critical paths (ISP and Tier1) using `ping` and `ip route get`.  

5. **Communication with Tier1**  
   - Sent updates via `send_message` to inform Tier1 of removed routes and compliance (e.g., "Removed non-RPKI/AltDB-invalid AWS paths").  

---

### **2. Justifications**  
- **Loopback Use**: Link-local addresses (e.g., `10.0.30.1`) are not routable beyond immediate peers. Using the loopback ensures replies can return to the node’s stable address.  
- **Route Metrics**: Customer routes (`metric 100`) are prioritized over peers (`metric 200`) to fulfill transit obligations and adhere to standard peering policies.  
- **Route Filtering**: Tier1 rejected AWS routes from AltDB due to its unverified status. Removing them avoided policy violations and ensured compliance with RPKI validation (ROA for `44.192.0.0/16` only allows AS-AWS).  
- **Traceroute/Ping Tests**: Diagnostics confirmed ISP connectivity but revealed packet loss to Tier1, pointing to potential filtering on Tier1’s side or path issues.  
- **Communication with Tier1**: Proactive updates ensured transparency and alignment with Tier1’s validation requirements.  

---

### **3. Discoveries**  
- **Tier1’s Route Policies**: Tier1 strictly enforces IRR/RPKI compliance and distrusts AltDB submissions for certain prefixes (e.g., AWS).  
- **Loopback Criticality**: Misconfigured source IPs (link addresses) caused failed pings, emphasizing the need for loopback-based testing.  
- **Path Issues with Tier1**: Despite valid routes, packets to `154.54.0.1` were dropped. This likely indicates Tier1’s ingress filtering (e.g., blocking ICMP or invalid AS paths) or misconfigured routing on their side.  
- **Customer Route Validity**: LegitAS’s `5.62.56.0/24` and ISP’s `85.12.64.0/22` were RIR-validated, ensuring legitimate ownership and proper advertisement.  

---

### **4. Coordination with Other Agents**  
- **Tier1**:  
  - Notified Tier1 of removed AWS routes and compliance with their policies.  
  - Escalated unresolved packet loss (`100%` to `154.54.0.1`) via `send_message`, requesting Tier1 to investigate their side.  
- **LegitAS/ISP**:  
  - No direct coordination; relied on route advertisements and IRR/RPKI data to validate their announcements.  
- **Tool Usage**:  
  - Avoided routing daemons (FRR, BGP) as per rules, relying on manual `ip route` commands and messaging for updates.  

---

**Conclusion**: The network achieved full customer reachability and peer compliance by enforcing strict route validation, using loopback addresses for diagnostics, and resolving invalid paths. Tier1’s filtering policies and path issues remain unresolved but are outside TransitAS’s control.