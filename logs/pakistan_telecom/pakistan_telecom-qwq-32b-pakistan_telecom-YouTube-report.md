**Observed**: Loopback interface configured with 208.65.153.1/32; default route via Tier1’s 10.0.20.2 established. Ping tests to Tier1’s link IP succeeded. Tier1 confirmed route propagation after follow-up. Network relies on manual messaging for route advertisement instead of BGP/OSPF.  

**Decided**: Assign loopback address, set default route, send prefix advertisement, perform connectivity tests, and await Tier1’s confirmation before declaring success.  

**Why**: Loopback ensures stable end-to-end communication; default route directs upstream traffic. Manual advertisement bypasses missing routing daemons. Ping tests validate local connectivity, while Tier1’s confirmation guarantees global reachability adherence to routing rules (customer > peer > provider).
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Loopback Configuration**:  
   - Ran `ip addr add 208.65.153.1/32 dev lo` to assign the assigned prefix’s first address to the loopback interface.  
   - Verified with `ip addr show lo` to ensure the address was configured.  

2. **Default Route Setup**:  
   - Added a default route via Tier1’s link-local IP (`10.0.20.2`) using `ip route add default via 10.0.20.2`. This ensures all non-local traffic uses Tier1 as the upstream provider.  

3. **Prefix Advertisement**:  
   - Sent a message to Tier1 (`send_message`) to advertise `208.65.153.0/24`, instructing them to propagate it into their routing domain.  

4. **Connectivity Testing**:  
   - Tested reachability to Tier1 using `ping -c 3 -I 208.65.153.1 10.0.20.2`, sourced from the loopback to validate basic connectivity.  

5. **Route Validation**:  
   - Ran `ip route show` to confirm the default route and absence of unexpected routes. Observed Tier1-advertised routes (e.g., `63.218.0.1 via 10.0.20.2`).  

6. **Final Verification**:  
   - Requested Tier1 to confirm propagation of the prefix and perform a reciprocal ping test.  
   - After Tier1 confirmed bidirectional reachability, called `report_done` to signal completion.  

---

### **2. Justifications**  
- **Loopback Configuration**:  
  - The loopback address (`208.65.153.1/32`) is the stable identifier for YouTube, ensuring end-to-end reachability. Link-local addresses (e.g., `10.0.20.1`) are infrastructure-only and not advertised.  

- **Default Route**:  
  - As a customer of Tier1, the default route via Tier1 ensures all traffic exits through the provider, aligning with the "provider last" route preference rule.  

- **Prefix Advertisement**:  
  - Without dynamic routing protocols (BGP/OSPF), direct messaging to Tier1 was the only way to propagate the assigned prefix into the wider network.  

- **Loopback-Sourced Pings**:  
  - Link-local addresses lack global routing, so tests must originate from the loopback to ensure replies can return via the correct path.  

- **Route Validation**:  
  - Verified no rogue routes were installed and confirmed Tier1’s routes were learned correctly, ensuring proper upstream connectivity.  

- **Tier1 Coordination**:  
  - Explicit confirmation of route propagation and bidirectional reachability was critical to validate global accessibility of the prefix.  

---

### **3. Discoveries About the Network**  
- **Static Route Dependency**: The network relies on manual route advertisement (via messages) rather than dynamic protocols, requiring explicit coordination with providers.  
- **Provider’s Role**: Tier1 acts as the sole upstream path, and its routing decisions directly control the global reachability of YouTube’s prefix.  
- **Address Scope**: Link-local addresses (`10.0.20.0/30`) are confined to the physical link and cannot be used for end-to-end communication.  
- **Route Preference**: The absence of customers or peers means YouTube’s routing table prioritizes Tier1 as the default exit point.  

---

### **4. Coordination with Other Agents**  
- **Tier1 Communication**:  
  - Sent two messages:  
    1. Initial advertisement of `208.65.153.0/24` to ensure Tier1 propagated the prefix.  
    2. A follow-up request to verify bidirectional reachability and route propagation.  
  - Relied on Tier1’s confirmation of successful ping tests to validate end-to-end connectivity.  
- **No Interaction with Non-Neighbors**:  
  - Could not directly coordinate with non-adjacent nodes (e.g., h2). All communication funneled through Tier1, which acts as the upstream transit provider.  

---

**Conclusion**: The experiment confirmed that YouTube’s prefix is globally reachable via Tier1 after proper configuration and provider coordination. All goals were met through careful route management, loopback address usage, and explicit messaging with the provider.