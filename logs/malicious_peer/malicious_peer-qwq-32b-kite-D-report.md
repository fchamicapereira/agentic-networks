**Observed:** Connectivity failure to 81.0.0.1 via Provider B, ICMP blocked by AS-A’s ACLs, both Providers B and E relied on faulty Peer-B upstream, and initial route addition to Provider E failed due to metric conflict.  

**Decided:** Switched to TCP tests (nc/curl), adjusted Provider E’s route metric for priority, escalated issues separately to Providers B and E, and requested alternate paths.  

**Why:** ICMP blockages required TCP validation; metric adjustment prioritized E’s path after B’s failure; separate coordination avoided messaging errors, and Peer-B’s critical failure necessitated upstream diversification.
### Experiment Report: Network Connectivity Troubleshooting  

---

#### **1. Actions Taken**  
**Initial Diagnostics**  
- **Route and Firewall Checks**:  
  ```bash  
  ip route show table all  
  iptables -S  
  ```  
  *Purpose*: Verify local routing and firewall rules to rule out misconfigurations.  

- **ICMP Connectivity Test**:  
  ```bash  
  ping -c4 -M do -s 552 -I $(ip addr show lo | grep 'inet' | awk '{print $2}' | cut -d'/' -f1) 81.0.0.1  
  ```  
  *Purpose*: Test reachability via Provider B, which failed (100% packet loss).  

- **MTU and Forensic Capture**:  
  ```bash  
  ip link set dev D-eth0 mtu 1400  
  tcpdump -nni D-eth0 'icmp' -c 10  
  ```  
  *Purpose*: Diagnose fragmentation/PMTUD issues and capture packet loss evidence.  

**Provider E Contingency Path**  
- **Route Addition**:  
  ```bash  
  ip route add 81.0.0.0/8 via 10.1.3.2 dev D-eth1  
  ```  
  *Purpose*: Bypass Provider B’s faulty path. Failed initially due to metric conflict, so reconfigured with:  
  ```bash  
  ip route replace 81.0.0.0/8 via 10.1.3.2 dev D-eth1 metric 50  
  ```  

- **TCP Connectivity Test**:  
  ```bash  
  nc -zv -w5 81.0.0.1 53  
  ```  
  *Purpose*: Test DNS port reachability over Provider E (failed due to network unreachable).  

**Advanced Troubleshooting**  
- **Traceroute via Provider E**:  
  ```bash  
  traceroute -I -n -i D-eth1 81.0.0.1  
  ```  
  *Purpose*: Confirm Provider E’s path also timed out, indicating dependency on Peer-B.  

- **HTTP Layer-7 Test**:  
  ```bash  
  curl -IL http://81.0.0.1 --interface 141.101.0.1  
  ```  
  *Purpose*: Validate application-layer connectivity (failed with "Connection refused").  

---

#### **2. Justifications**  
- **Route Prioritization**: Lowered Provider E’s metric (50 vs 100) to prioritize it over B when B’s path failed, ensuring fallback reliability.  
- **Protocol Switching**: Shifted from ICMP to TCP/HTTP tests after discovering AS-A’s ACLs blocked ICMP, aligning with Provider B’s recommendation.  
- **Metric Conflict Resolution**: Used `ip route replace` to resolve the "File exists" error by explicitly setting metrics, ensuring no overlapping routes.  
- **Forensic Evidence**: Captured packet loss data to pressure providers with concrete observations rather than assumptions.  
- **Separate Messaging**: Split messages to B and E after a multi-recipient error, ensuring compliance with direct-neighbor communication rules.  

---

#### **3. Network Discoveries**  
- **Shared Dependency on Peer-B**: Both providers (B and E) routed traffic through Peer-B for `81/8`, creating a single point of failure.  
- **AS-A’s ACL Policies**: ICMP traffic was blocked upstream, requiring protocol shifts for diagnostics.  
- **Peer-B’s Unreliability**: Traceroute failures and TCP tests confirmed Peer-B’s path was non-functional for `81/8`.  
- **No Alternate Paths**: Provider E confirmed no alternative routes outside Peer-B’s infrastructure.  
- **Layer-7 Failures**: HTTP tests failed, indicating the issue extended beyond ICMP blocking to broader service unavailability.  

---

#### **4. Agent Coordination**  
- **Escalation to Provider B**:  
  - Highlighted Peer-B dependency risks, requested alternate routes, and emphasized SLA compliance.  
  - Shared firewall and route configurations to prove local compliance.  
- **Requests to Provider E**:  
  - Demanded path details (AS-level, RIB/FIB entries) and direct Layer-2 tests (`tcpdump`).  
  - Urged to explore non-Peer-B paths and validate upstream ACLs.  
- **Cross-Provider Pressure**: Exposed systemic dependency issues to both providers simultaneously to accelerate resolution.  
- **Evidence Sharing**: Forwarded packet loss logs, route tables, and test results to providers for corroboration.  

---

**Final Conclusion**: The outage stemmed from a critical Peer-B failure affecting both providers, compounded by AS-A’s ACLs. Without alternate routes or Peer-B’s intervention, connectivity remained unreachable. The experiment highlighted the need for diversified upstream providers and proactive ACL-aware diagnostics.