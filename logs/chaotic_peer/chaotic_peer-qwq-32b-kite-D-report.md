**Actions Taken:**  
1. Blocked BGP traffic with `iptables` rules targeting invalid AS_PATHs (e.g., AS65534/AS65535), adding `--algo bm` to resolve syntax errors.  
2. Deleted static routes via provider B (e.g., `ip route del ...`) to stop leaked non-loopback prefixes.  
3. Sent messages to providers B and E to address route leaks, request RPKI filtering, and validate routes.  
4. Adjusted `tcpdump` with `timeout 5` and packet limits to capture BGP traffic without timeouts.  
5. Enforced strict outbound BGP filtering using `neighbor ... route-map` to restrict advertised routes.  

**Justifications:**  
- Blocked invalid AS_PATHs to mitigate malicious route hijacks.  
- Removed leaked routes to prevent unauthorized prefix advertisement.  
- Coordinated with providers to align on RPKI enforcement and leak containment.  
- Optimized `tcpdump` parameters to ensure stable traffic analysis.  
- Enforced strict BGP rules to ensure only legitimate routes were advertised.  

**Discoveries:**  
- Route leaks via providers B and E, with invalid AS_PATHs (e.g., AS65534) and unauthorized prefixes (e.g., 10.0.0.0/8).  
- Providers B and E lacked sufficient RPKI filtering, necessitating local measures.  
- Network instability with provider E caused packet loss, linked to route leaks.  

**Coordination:**  
- Notified providers B and E of leaks and urged RPKI validation.  
- Confirmed actions taken (e.g., route deletions, filtering) with providers to align mitigation efforts.  
- Verified internal route tables (`ip route`) to distinguish between local and upstream issues.
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Firewall Configuration**:  
   - Blocked outbound BGP updates containing invalid `AS_PATH` patterns using `iptables`:  
     ```  
     iptables -A OUTPUT -p tcp --dport 179 -m string --algo bm --string 'AS655' -j DROP  
     ```  
     Later refined to allow only valid AS_PATHs for my AS (D):  
     ```  
     iptables -A OUTPUT -p tcp --dport 179 -m string --algo bm --string 'AS_PATH: [D]' -j ACCEPT  
     ```  
   - Added rules to block non-loopback-originated BGP updates:  
     ```  
     iptables -A OUTPUT -p tcp --dport 179 -m iprange ! --src-range 141.101.0.1-141.101.0.1 -j DROP  
     ```  

2. **Route Management**:  
   - Removed leaked static routes imposed by providers (e.g., `81.2.0.1` via B):  
     ```  
     ip route del 81.2.0.1 via 10.1.2.2  
     ```  
   - Flushed routing cache for malicious prefixes:  
     ```  
     ip route flush cache  
     ```  
   - Verified and removed rogue routes (e.g., `10.0.0.0/8`, `93.184.216.34/32`):  
     ```  
     ip route del 93.184.216.34/32  
     ```  

3. **Network Analysis**:  
   - Used bounded `tcpdump` to inspect BGP traffic:  
     ```  
     timeout 5s tcpdump -i D-eth1 -nn port 179 -c 5  
     ```  
   - Checked routing tables for unauthorized prefixes:  
     ```  
     ip route show | grep '10\.'  
     ```  

4. **Communication with Providers**:  
   - Sent urgent messages to providers B and E to enforce RPKI filtering and validate routes:  
     - **To B**:  
       ```  
       **ENFORCE_RPKI**: Prefix `93.184.216.34/32` announced by A contains invalid AS_PATH [AS6]. Reject non-ROA-compliant routes immediately (#RFC8209).  
       ```  
     - **To E**:  
       ```  
       **SECURITY_ALERT**: Prefix `142.250.179.46/32` announced by A contains invalid AS_PATH [AS65534 65535]. Apply RPKI validation (#RFC8210).  
       ```  

---

### **2. Justifications**  
- **Firewall Rules**:  
  - Blocked malicious AS_PATH patterns (e.g., `AS655xx`) to prevent route hijacks and comply with provider policies.  
  - Enforced strict filtering to ensure only my loopback prefix (`141.101.0.1/32`) is advertised, adhering to "do not provide transit" rules.  

- **Route Management**:  
  - Removed static routes from providers to avoid accidental advertisement of non-loopback prefixes.  
  - Flushed caches and deleted rogue routes to stop propagation of spoofed paths (e.g., `10.0.0.0/8`, `93.184.216.34/32`).  

- **Network Analysis**:  
  - Bounded `tcpdump` ensured safe packet capture without timeouts.  
  - Auditing routes confirmed internal compliance and identified unauthorized prefixes.  

- **Provider Coordination**:  
  - Pressured providers to enforce RPKI validation to stop spoofed routes (e.g., `AS65534/AS65535`).  
  - Clarified my own actions (e.g., strict filtering) to align with provider expectations and avoid blame for route leaks.  

---

### **3. Discoveries About the Network**  
- **Route Leaks and Hijacks**:  
  - Malicious actors (e.g., node A) spoofed routes (`142.250.179.46/32`, `93.184.216.34/32`) using reserved AS_PATHs (AS65534/AS65535).  
  - Provider E propagated spoofed routes (`10.0.0.0/8`), indicating lax RPKI enforcement.  

- **Internal Vulnerabilities**:  
  - Leaked provider-imposed static routes (via B) risked unintended advertisement.  
  - Incorrect iptables syntax (e.g., missing `--algo bm`) initially allowed malicious updates.  

- **Provider Instability**:  
  - Packet loss via E forced reliance on B, which itself reported route leaks.  

---

### **4. Coordination with Other Agents**  
- **Provider B**:  
  - Acknowledged route leak reports and demanded RPKI compliance.  
  - Clarified local mitigation steps (e.g., iptables rules) to avoid being blamed for spoofed paths.  

- **Provider E**:  
  - Urgently notified about spoofed routes and RPKI validation failures.  
  - Requested isolation until spoofed routes (`10.0.0.0/8`) were purged from its RIB.  

- **Cross-Agent Trust**:  
  - Shared verifiable evidence (e.g., `ip route get` outputs, tcpdump results) to corroborate claims of spoofed routes.  
  - Avoided disclosing private policies (e.g., route preferences) while enforcing security measures.  

---

### **Conclusion**  
The experiment highlighted the need for strict BGP filtering, RPKI enforcement, and proactive route validation. While providers B and E were unreliable in enforcing security, local measures (firewalls, route audits) mitigated risks. Persistent coordination with providers and rigorous validation of routing paths were critical to maintaining network integrity.