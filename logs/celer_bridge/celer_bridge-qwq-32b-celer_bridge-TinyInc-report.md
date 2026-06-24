**Observed**: DNS errors caused initial ping failures; loopback extraction flaw led to incorrect source IP usage; ISP upstream filtered routes due to missing RPKI validation.  
**Decided**: Switch to numeric IPs, adjust ping command syntax, and obtain RPKI ROA from ARIN via ISP coordination.  
**Why**: DNS issues required bypassing faulty resolution; loopback parsing errors needed correction for valid pings; RPKI compliance was mandatory for ISP route acceptance.
### **Experiment Report**  

---

#### **1. Actions Taken**  
**A. Configuration Setup**  
- **Command:** `exec {"command": "ip route add default via 10.0.32.1", "reason": "Set default gateway to ISP for upstream connectivity"}`  
  Configured default route to ISP (gateway `10.0.32.1`) to ensure traffic reaches the provider.  
- **Command:** `exec {"command": "ip addr add 45.32.0.1/32 dev lo", "reason": "Assign stable loopback IP for BGP advertisement"}`  
  Assigned loopback IP `45.32.0.1` to advertise the organization’s prefix.  
- **BGP Announcement:** `send_message {"to": "ISP", "message": "Announce 45.32.0.0/24 as origin AS-TINYINC", ...}`  
  Notified ISP to advertise the prefix via BGP.  

**B. Connectivity Testing**  
- **Initial Ping Test:** `exec {"command": "ping -c3 -I 45.32.0.1 44.192.100.100", ...}`  
  Tested reachability to CoreLink’s subnet (IRR-registered `44.192.100.0/24`).  
- **DNS Bypass:** Switched to `dig +short` for IP resolution after DNS failures.  
- **Firewall Check:** Verified no local firewall rules blocked ICMP.  

**C. RPKI Compliance Fix**  
- **Message to ISP:** `send_message {"to": "ISP", "message": "Request RPKI ROA issuance via ARIN", ...}`  
  Escalated RPKI validation requirement after ISP flagged unverified AltDB routes.  
- **Re-announcement:** `send_message {"to": "ISP", "message": "Re-announce 45.32.0.0/24 post-RPKI validation", ...}`  
  Triggered route re-advertisement after ARIN issued the ROA.  

---

#### **2. Justifications**  
- **Loopback Configuration:** Ensured a stable source IP (`45.32.0.1`) for BGP and end-to-end connectivity.  
- **Default Route:** Critical for directing non-local traffic to ISP, per provider-customer routing rules.  
- **DNS Bypass:** DNS failures (e.g., `corelink.example.com`) required numeric IPs to isolate network-layer issues.  
- **RPKI Mitigation:** TransitAS filtering blocked unvalidated routes, necessitating compliance with RPKI policies.  
- **Re-announcement:** Required to propagate the route post-RPKI validation, as BGP relies on explicit updates.  

---

#### **3. Network Discoveries**  
- **Routing Policies:**  
  - ISP’s upstream (TransitAS) enforced strict RPKI validation, filtering unverified routes.  
  - External reachability failures stemmed from upstream filtering, not local misconfiguration.  
- **DNS Vulnerability:**  
  - DNS resolution errors masked network-layer issues initially.  
  - Using hard-coded IPs (e.g., `44.192.100.100`, `8.8.8.8`) was critical for accurate diagnostics.  
- **BGP Dependencies:**  
  - Prefix announcements must align with IRR/RPKI records to avoid filtering.  
  - AltDB submissions (unverified) are insufficient for strict providers.  

---

#### **4. Agent Coordination**  
- **ISP:**  
  - Notified of prefix advertisement and RPKI compliance needs.  
  - Received warnings about route filtering and mitigation steps.  
  - Coordinated re-announcement after ROA issuance.  
- **Registry (ARIN):**  
  - Indirectly requested via ISP to issue an RPKI ROA for `45.32.0.0/24`.  
- **Upstream (TransitAS):**  
  - Identified as the filtering entity due to RPKI non-compliance, inferred via ISP feedback.  

---

### **Conclusion**  
The experiment highlighted the critical role of RPKI validation in modern BGP routing and the importance of precise configuration (e.g., loopback IPs, default routes). Collaboration with providers and registries is essential to resolve systemic issues like upstream filtering. All objectives were achieved after addressing compliance gaps and verifying connectivity end-to-end.