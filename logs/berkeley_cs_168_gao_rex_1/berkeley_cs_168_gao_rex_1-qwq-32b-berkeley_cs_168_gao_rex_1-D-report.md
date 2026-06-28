**Observed**: Network interactions with providers A/C required route/firewall validation via commands like `ip route`, `ping`, and iptables checks. Route syntax errors (e.g., placeholder IPs) caused failures, while strict rp_filter policies blocked some paths. Providers prioritized loopback IPs for testing over infrastructure addresses.  

**Decided**: Prioritize loopback pings and precise route configurations (e.g., `ip route add 54.xxx via 10.0.6.1`), confirm firewall rules explicitly allow ICMP, and isolate `report_done` to avoid tool conflicts. Adjusted routes to match provider-advertised addresses strictly.  

**Why**: Loopback ensures stable return routes; infrastructure IPs risk policy blocks. Correct route syntax avoids errors. Isolated reporting prevents tool interference. Compliance with rp_filter and provider policies maintains connectivity and avoids route rejection.
### **Experiment Report**  

---

#### **1. Actions Taken**  
- **Route Verification & Configuration:**  
  - Added explicit route for Provider **C’s LoopBack** (`54.xxx.xxx.xxx/32 via 10.0.6.1 dev D-eth2`) to honor their advertisement.  
  - Configured routes for Provider **A’s host** (`23.xxx.xxx.xxx/32`) via their link IP (`10.0.5.1 dev D-eth1`), verified via `ip route get`.  
  - Used `ip route show` and `ip route get` repeatedly to validate path integrity and compliance with rp_filter requirements.  

- **Connectivity Tests:**  
  - Executed multiple `ping` commands sourced from the **LoopBack interface** (e.g., `ping -c3 -I $(LOOPBACK_ADDR) <TARGET>`).  
  - Tested **bidirectional reachability** to C’s LoopBack and validated return paths with `ping -R` (Record Route).  

- **Firewall/Security Checks:**  
  - Inspected `iptables` and `firewalld` rules to confirm allowance of **ICMP Echo (types 8/0)** for Providers A and C.  
  - Shared firewall configurations with A to demonstrate compliance.  

- **Message Communication:**  
  - Sent detailed responses to Providers A and C, including command outputs (e.g., route tables, ping results, firewall rules).  
  - Corrected earlier errors (e.g., invalid placeholder IPs in routes) after Provider A flagged them.  

- **Policy Enforcement:**  
  - Avoided advertising link subnets (e.g., `10.0.4.0/30`, `10.0.5.0/30`, `10.0.6.0/30`) as per privacy and routing policies.  
  - Ensured all traffic sourced from LoopBack to prevent routing failures due to non-routable link IPs.  

---

#### **2. Justifications**  
- **LoopBack Source in Pings:**  
  Infrastructure link IPs (e.g., `10.0.4.2`) are not globally routable. Using LoopBack ensures replies can return via expected paths, avoiding misleading errors.  

- **Explicit Routes for Provider LoopBacks:**  
  Providers originate traffic to their LoopBack addresses. Configuring these routes ensures revenue-generating traffic terminates correctly without violating transit policies.  

- **Firewall Transparency:**  
  Sharing firewall rules with A demonstrated compliance with their security requirements while avoiding overexposure of internal policies.  

- **rp_filter Compliance:**  
  Provider A emphasized route format validation to prevent asymmetric routing. Commands like `ip route get` ensured paths met kernel requirements (e.g., `dev ethX src LOOPBACK_IP`).  

- **Avoiding Transit for Providers:**  
  No routes were added for Provider networks beyond their advertised LoopBacks. This maintained policy integrity and prevented unintended transit services.  

---

#### **3. Discoveries About the Network**  
- **Topology Structure:**  
  - Direct connections to Providers A (D-eth0), B (D-eth1), and C (D-eth2) imply D is a multi-homed stub AS with no customers.  
  - Providers expect strict route filtering and policy adherence.  

- **Routing Vulnerabilities:**  
  - Misconfigured routes (e.g., placeholder IPs like `23.XX.XX.XX`) caused errors. Precision in command syntax is critical.  
  - Return paths must explicitly use LoopBack as source to satisfy rp_filter and avoid blackholes.  

- **Provider Expectations:**  
  - Providers actively monitor routes and connectivity. Immediate responses to their queries were essential to avoid delays.  
  - ICMP diagnostics (pings, Record Route) are foundational for troubleshooting but require careful execution to comply with policies.  

---

#### **4. Coordination with Other Agents**  
- **Provider C:**  
  - Verified D-eth2 interface status and ping results to confirm physical connectivity.  
  - Installed their LoopBack route after explicit advertisement and validated via `ip route get`.  
  - Conducted return route tests and shared Record Route ping results to confirm path symmetry.  

- **Provider A:**  
  - Addressed firewall concerns by sharing `iptables` and `firewalld` configurations.  
  - Repeatedly validated routes for their host (`23.xxx.xxx.xxx`) to ensure correct next-hops and source addresses.  
  - Corrected route syntax errors (e.g., invalid prefixes) after A flagged them, demonstrating iterative troubleshooting.  

- **General Coordination Strategy:**  
  - All communication followed a **request-response** pattern:  
    1. **Providers** sent specific queries (e.g., "Show route for X", "Test firewall").  
    2. **D** executed commands, captured outputs, and sent concise, policy-compliant responses.  
  - Avoided proactive configuration changes unless explicitly requested to minimize policy violations.  

---

**Conclusion:** The experiment highlighted the importance of precise route management, strict adherence to provider policies, and transparent communication to ensure stable connectivity while maximizing revenue.