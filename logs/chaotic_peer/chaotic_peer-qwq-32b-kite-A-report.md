**Observed**: Failed route additions (RTNETLINK errors), 100% packet loss to E's interface, E rejecting route ads due to peer policy, and accidental advertisement of E's loopback.  
**Decided**: Block B via iptables, retry routes with explicit interfaces, remove misadvertisements, and coordinate with E/S on policy compliance.  
**Why**: To isolate B, fix connectivity, comply with network policies, and correct configuration errors causing route conflicts.
### Experiment Report  

---

#### **1. Actions Taken**  
**Blocking Malicious Node B:**  
- **Commands:**  
  ```  
  iptables -A INPUT -s 10.0.12.2 -j DROP  
  iptables -A FORWARD -s 10.0.12.2 -j DROP  
  ip route del default via 10.0.12.2  
  ```  
  Attempted to reroute via E:  
  ```  
  ip route add default via 10.0.14.2 dev A-eth1  
  ```  
- **Issue:** Route addition failed (`RTNETLINK answers: No such process`) due to E’s unresponsive interface.  

**Route Validation and Policy Compliance:**  
- Removed accidental advertisement of E’s loopback (10.255.2.1/32):  
  ```  
  ip route del 10.255.2.1/32  
  ```  
- Verified firewall rules:  
  ```  
  iptables -L FORWARD -v -n  
  ```  

**Connectivity Checks:**  
- Diagnosed E’s interface (`A-eth1`):  
  ```  
  ip link show A-eth1  
  ping -c 3 -I 10.0.14.1 10.0.14.2  
  ```  
- Tested reachability to S’s loopback (10.255.5.1/32) and external routes (8.8.8.8).  

---

#### **2. Justifications**  
- **Blocking B:** Immediate action to isolate malicious behavior (per E’s report) and prevent route poisoning.  
- **Route via E:** After B’s blockage, E became the only viable path. The `dev` parameter was added to specify the interface after initial syntax errors.  
- **Removing E’s Loopback Route:** Compliance with policy: peers’ loopbacks must not be advertised unless revenue-justified (E is a peer, not a customer).  
- **Firewall Audit:** Ensured no accidental rules permitted unauthorized transit for peers.  
- **Interface Validation:** E’s unreachable `A-eth1` interface explained failed routes and packet loss, requiring troubleshooting.  

---

#### **3. Discoveries**  
- **E’s Interface Issue:** `A-eth1` (connection to E) was operational but unresponsive, causing 100% packet loss to E’s IP (10.0.14.2). This blocked external routes via E.  
- **Policy Constraints:**  
  - Peers (B/E) cannot carry customer (S) routes.  
  - Loopbacks must not be advertised without a revenue incentive.  
- **Malicious Behavior:** B’s false claims about D (e.g., "blackholing") required independent verification.  
- **Route Advertisement Errors:** Accidental advertisement of E’s loopback highlighted the need for stricter route filtering.  

---

#### **4. Coordination with Other Agents**  
- **With E:**  
  - Informed E of B’s blockage and requested mutual isolation.  
  - Asked E to validate D’s behavior after B’s accusation.  
  - Confirmed removal of E’s loopback route and addressed connectivity issues.  
- **With S:**  
  - Notified S of restricted peer-based transit due to policy, advising reliance on E’s existing routes.  
- **With B:** Ignored B’s claims (labeled malicious) until corroborated by E or data-plane tests.  

---

### **Conclusion**  
The experiment highlighted the importance of:  
1. **Policy Adherence:** Strictly adhering to transit rules (e.g., no peer-to-peer transit) to avoid violations.  
2. **Interface Validation:** Proactively checking link status to avoid cascading route failures.  
3. **Skepticism of Claims:** Treating B’s accusations as untrusted until validated by multiple sources.  
4. **Route Filtering:** Ensuring only legitimate prefixes (e.g., customer routes) are advertised.  

Future steps would include implementing automated route filtering and monitoring E’s interface stability to maintain revenue-generating paths for S.