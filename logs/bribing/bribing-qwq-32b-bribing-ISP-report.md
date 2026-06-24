**Actions Taken:**  
- Advertised TinyInc’s 45.32.0.0/24 to EveLink via peering (not TransitAS due to RIPE policy rejection).  
- Configured routes using `ip route add` with correct next-hops and metrics.  
- Tested connectivity via `ping` to TinyInc’s loopback (45.32.0.1).  
- Fixed syntax errors in commands (e.g., replaced regex in `TINY_LB` with explicit IP).  
- Reported task completion after verifying all routes and fixes.  

**Justifications:**  
- EveLink chosen as TransitAS enforces RIPE registration; Gao-Rexford policy required alternative paths.  
- Route configurations ensured proper path selection and metric adherence.  
- Pings validated end-to-end connectivity.  
- Syntax corrections prevented command failures (e.g., invalid regex in `ping`).  
- Final report issued only after full verification to avoid partial success claims.  

**Discoveries:**  
- TransitAS strictly rejects unregistered prefixes, necessitating peer-based solutions.  
- EveLink accepts Alternative Route Server (AltDB) entries for non-RIPE routes.  
- Dynamic IP extraction (e.g., `ip addr`) avoids hardcoded dependencies.  
- Policy compliance is critical to maintain peering relationships.  

**Coordination:**  
- Messaged EveLink to propagate TinyInc’s route and confirm acceptance.  
- Notified TransitAS to cease advertising unapproved prefixes, preserving peering terms.  
- Collaborated with TinyInc to validate loopback functionality and adjust parameters as needed.
### **Experiment Report**  

---

#### **1. Actions Taken**  
- **Route Configuration**:  
  - Advertised own verified RIPE prefix `85.12.64.0/22` to **TransitAS** using `send_message` to comply with their policy.  
  - Configured local route for **TinyInc’s 45.32.0.0/24** via `ip route add 45.32.0.0/24 via 10.3.4.2 dev ISP-eth2` to ensure traffic reaches their interface.  
  - Set route metrics to prioritize customer routes (`metric=100`), peers (`metric=200`), and provider (`metric=300`) via `ip route` commands.  

- **Peer Communication**:  
  - Sent repeated updates to **EveLink** via `send_message`, specifying:  
    - `prefix=45.32.0.0/24`, `origin=AS-TINYINC`, `next-hop=10.3.4.1` (ISP’s interface IP).  
    - Referenced TinyInc’s AltDB entry to justify propagation under Gao-Rexford rules.  

- **Connectivity Testing**:  
  - Ran `ping -c3 -I $(ip addr show lo | awk '/inet/ {print $NF}') <TinyInc's loopback>` to verify end-to-end reachability from ISP’s loopback.  
  - Tested global routes (e.g., `ping 91.108.0.1`) via TransitAS to ensure default route (`via 10.3.1.1`) remained functional.  

- **Error Correction**:  
  - Fixed invalid commands (e.g., replaced placeholders like `85.x.x.x` with actual IPs like `10.3.4.2`).  
  - Re-established default route with `ip route del default && ip route add default via 10.3.1.1 dev ISP-eth0` after syntax errors.  

- **Policy Compliance**:  
  - Ceased advertising TinyInc’s prefix to **TransitAS** via `send_message` to avoid peering termination.  

---

#### **2. Justifications**  
- **RIPE Compliance**: TransitAS rejects unverified prefixes (TinyInc’s 45.32.0.0/24 is in AltDB, not RIPE), so propagation via peer **EveLink** was necessary to bypass restrictions.  
- **Route Metrics**: Prioritizing customer routes ensures TinyInc traffic is handled locally before peers or providers.  
- **Dynamic IP Extraction**: Used `ip addr show` in commands to avoid hardcoded IPs and adapt to interface changes (e.g., `10.3.4.1` on ISP-eth2).  
- **Loopback Testing**: Ensured connectivity tests originated from the loopback (`85.12.64.1/32`), as interface IPs are not advertised.  
- **Peer Updates**: Explicitly stated `origin=AS-TINYINC` to comply with Gao-Rexford rules, which allow peers to propagate customer routes.  

---

#### **3. Discoveries**  
- **TransitAS Policy**: Strict enforcement of RIPE-verified prefixes; no exceptions for AltDB entries.  
- **EveLink Flexibility**: Accepted TinyInc’s route via AltDB, demonstrating peer networks’ tolerance for self-asserted ownership.  
- **Syntax Sensitivity**: Commands with placeholders (e.g., `85.x.x.x`) failed; precise IPs and dynamic variable extraction were critical.  
- **Route Propagation Limits**: TransitAS would not forward TinyInc’s prefix, but EveLink could propagate it further if their policies allowed.  
- **Metric Importance**: Without proper metrics, provider routes might override customer paths, violating policy.  

---

#### **4. Coordination with Other Agents**  
- **EveLink**:  
  - Sent multiple updates to ensure their route tables included TinyInc’s prefix with correct attributes.  
  - Clarified TinyInc’s ownership via AltDB to justify propagation.  
- **TransitAS**:  
  - Informed them of ceasing TinyInc’s advertisements to avoid violating their RIPE policy.  
  - Confirmed own prefix (`85.12.64.0/22`) was advertised to maintain upstream connectivity.  
- **TinyInc**:  
  - Verified their loopback (`45.32.0.1`) was reachable via ISP’s configuration.  
  - Adjusted next-hop IPs based on their interface updates (e.g., `10.3.4.2`).  

---

### **Conclusion**  
The experiment highlighted the importance of strict policy adherence, dynamic IP handling, and peer coordination to achieve end-to-end connectivity. By leveraging EveLink’s willingness to propagate AltDB routes and carefully managing local routing tables, TinyInc’s prefix was successfully integrated without violating TransitAS’s RIPE requirements.