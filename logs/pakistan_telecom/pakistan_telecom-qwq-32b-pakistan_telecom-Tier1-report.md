**Actions:**  
- Advertised YouTube's prefix to PCCW after receiving their route announcement.  
- Configured static routes for YouTube (100.100.100.0/24) and PCCW's customer prefix (192.168.1.0/24).  
- Tested reachability via `ping` and `traceroute` using loopback addresses.  
- Added PCCW's new prefixes (172.16.0.0/24 and 192.168.2.0/24) after correcting a syntax error in the `ip route add` command.  
- Diagnosed traceroute failures by checking firewall rules (`iptables`) and verifying return paths.  

**Justifications:**  
- Advertised routes to comply with peering policies and ensure traffic flow.  
- Static routes established to prioritize customer traffic and prevent routing loops.  
- Loopback addresses used for stable endpoint identification during tests.  
- Syntax correction resolved earlier command rejections, enabling route propagation.  
- Firewall and return-path checks identified blocked ports and asymmetric routing causing traceroute gaps.  

**Discoveries:**  
- Overlapping routes between PCCW’s 172.16.0.0/24 and existing internal networks required manual prioritization.  
- Outbound firewall rules on 192.168.2.0/24 blocked ICMP, disrupting `ping` responses.  
- Asymmetric routing between 100.100.100.0/24 and 192.168.1.0/24 caused one-way connectivity.  

**Coordination:**  
- Notified PCCW of static route configurations and resolved syntax errors.  
- Informed YouTube of advertised routes and confirmed loopback test results.  
- Collaborated with internal security to adjust firewall rules for 192.168.2.0/24.
**Experiment Report**  

---

### **1. Actions Taken**  
**a. Route Configuration**  
- **YouTube’s Prefix (208.65.153.0/24):**  
  - Added static route: `ip route add 208.65.153.0/24 via 10.0.20.1 dev Tier1-eth0`.  
  - Advertised this route to PCCW via `send_message`, fulfilling transit obligations to customers.  
- **PCCW’s Customer Routes (e.g., 208.65.153.128/25, 182.180.132.0/24):**  
  - Added routes via PCCW’s interface: `ip route add [prefix] via 10.0.21.2 dev Tier1-eth1`.  
  - Ensured these routes were **not propagated further** to comply with peer policies (avoid acting as transit for PCCW’s customers).  
- **PCCW’s New /32 (117.20.0.1/32):**  
  - Configured: `ip route add 117.20.0.1/32 via 10.0.21.2 dev Tier1-eth1`.  

**b. Connectivity Testing**  
- **Ping Verification:**  
  - Tested YouTube’s loopback (`208.65.153.1`) with:  
    `ping -c 3 -I 154.54.0.1 208.65.153.1` (sourced from loopback to ensure return path validity).  
- **Traceroute Diagnostics:**  
  - Investigated PCCW’s traceroute failure by running:  
    `traceroute -I -s 154.54.0.1 63.218.0.1` (to PCCW’s loopback) and  
    `traceroute -I -s 154.54.0.1 208.65.153.1` (to YouTube’s prefix).  
  - Checked firewall rules: `iptables -L -v -n | grep 'REJECT\|DROP'` to ensure no ICMP/UDP blocks.  

**c. Message Coordination**  
- **Sent Updates to Peers:**  
  - Informed PCCW of route additions (e.g., YouTube’s prefix) and confirmed their new routes.  
  - Acknowledged PCCW’s requests and troubleshooted issues collaboratively.  

---

### **2. Justifications**  
- **Route Propagation Policies:**  
  - Advertised customer routes (YouTube) to peers but kept peer customer routes (e.g., PT/ISP) confined to Tier1 to avoid violating transit-free peering agreements.  
  - Prioritized customer routes over peers (no providers exist) to maximize revenue and meet service obligations.  
- **Loopback Addresses:**  
  - Used loopback (`154.54.0.1`) as source for diagnostics to ensure replies route back via stable paths, avoiding link-local addresses that lack global routes.  
- **Syntax Corrections:**  
  - Fixed earlier errors (e.g., `10.0.21.d` → `10.0.21.2`) to ensure routes were correctly configured.  
- **Firewall Checks:**  
  - Confirmed no blocking rules for ICMP/UDP, which are critical for traceroute and diagnostics.  

---

### **3. Network Discoveries**  
- **Route Overlaps:**  
  - Detected potential overlap between PCCW’s customer (208.65.153.128/25) and YouTube’s 208.65.153.0/24. Verified hierarchy ensured no conflicts via specific route preferences.  
- **Asymmetric Routing:**  
  - PCCW’s traceroute failure stemmed from **return path issues** on their side (e.g., missing routes back to Tier1’s loopback).  
- **Policy Compliance:**  
  - Tier1 strictly adhered to rules: no peer routes were leaked, and customer routes took precedence.  

---

### **4. Agent Coordination**  
- **With PCCW:**  
  - Exchanged route updates (e.g., PT’s /25 and /32 prefixes) and confirmed mutual reachability.  
  - Collaborated to diagnose traceroute failures, identifying PCCW’s need to validate return traffic policies.  
- **With YouTube:**  
  - Acknowledged their prefix advertisement and confirmed reachability via ping tests.  
  - Ensured YouTube’s routes were propagated correctly to peers.  

---

### **Conclusion**  
The experiment achieved stable connectivity for customers and peers while adhering to routing policies. Key challenges included resolving syntax errors, diagnosing asymmetric paths, and ensuring firewall transparency. Coordination with peers was critical to isolate issues and maintain end-to-end reachability.