**Observed:**  
- Successfully advertised loopback address, configured routes to ACM (/22) and AS1 (/24), and confirmed ping connectivity.  
- AS1 queried about missing /24 subnet; discovered ACM only advertised partial /24, leaving gaps.  

**Decided:**  
- Inform AS1 of existing routes and ACM’s partial /24 advertisement.  
- Request ACM to advertise full /24 subnet for complete reachability.  
- Maintain policy-compliant configurations and security settings.  

**Why:**  
- Advertisements ensured routability; ping verified functionality.  
- AS1’s query required route validation and ACM’s partial ad must be addressed for full connectivity.  
- Policy adherence prevents misconfigurations and ensures network integrity.
### Experiment Report  

---

#### **1. Actions Taken**  
1. **Advertised Stable Loopback Address**:  
   - Ran `ip addr show lo` to identify my stable node address (`154.54.1.1/32`).  
   - Sent messages to **AS1** (peer) and **ACM** (customer) advertising this address to ensure end-to-end reachability.  

2. **Configured Routing Tables**:  
   - Added a specific route for AS1’s loopback (`4.2.2.1/32`) via `10.0.2.1` after AS1 advertised it.  
   - Verified existing routes to ACM’s web server (`198.82.0.1/32`) via `AS2-eth1` (link to ACM).  

3. **Tested Connectivity**:  
   - Used `ping -c 3 -I 154.54.1.1 198.82.0.1` to confirm reachability to ACM’s web server from my loopback address.  

4. **Addressed AS1’s Query About 198.82.0/24**:  
   - Ran `ip route show 198.82.0/24` to check for the missing subnet.  
   - Confirmed only `198.82.0.1/32` was advertised by ACM.  
   - Informed AS1 that only the `/32` route exists and prompted ACM to advertise the full `/24` subnet.  

---

#### **2. Justifications**  
- **Stable Address Advertisement**:  
  - Required for end-to-end routing. Without this, other nodes cannot route traffic back to AS2’s loopback.  
- **AS1’s Loopback Route**:  
  - Added to enable direct communication with AS1’s infrastructure, improving specificity over the default route.  
- **ACM’s Web Server Route**:  
  - ACM is a customer, so routes to their hosted services (`198.82.0.1`) must be configured to fulfill transit obligations.  
- **Connectivity Test**:  
  - Verified that traffic sourced from the loopback (the stable address) reaches ACM’s server, ensuring correct routing and avoiding link-local address issues.  
- **Handling AS1’s Query**:  
  - ACM, as the subnet owner, must advertise the `/24` route. I cannot originate routes for ACM’s network without their advertisement, adhering to routing policy and security practices.  

---

#### **3. Discoveries**  
- **Successful Routes**:  
  - ACM’s web server (`198.82.0.1/32`) is reachable via `AS2-eth1` (ACM’s link).  
  - AS1’s loopback (`4.2.2.1/32`) is correctly routed via the peer link (`AS2-eth0`).  
- **Missing Subnet Route**:  
  - ACM only advertised `198.82.0.1/32`, not the full `/24` subnet. This explains AS1’s packet failures beyond their link.  
- **Policy Compliance**:  
  - No misconfigured routes or security issues detected. All actions followed transit ISP best practices (e.g., not propagating unadvertised prefixes).  

---

#### **4. Coordination with Other Agents**  
- **AS1**:  
  - Acknowledged their route advertisement (`4.2.2.1/32`) and confirmed its implementation.  
  - Informed them that the `198.82.0/24` subnet is not advertised by ACM, requiring ACM’s action.  
- **ACM**:  
  - Notified via message to advertise the full `/24` subnet for broader reachability.  
- **Knowledge Plane Interaction**:  
  - Followed protocols by auditing local routes before escalating issues (e.g., verifying `ip route` before replying to AS1).  

--- 

### **Conclusion**  
The network is stable for ACM’s hosted services and peer communication. ACM must advertise the full `/24` subnet to resolve AS1’s packet issues. All actions prioritized revenue (via reliable transit) and security (adhering to routing policies).