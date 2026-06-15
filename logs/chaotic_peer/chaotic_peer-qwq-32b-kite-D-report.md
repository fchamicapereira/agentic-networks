**Observed:** MAC address for E was unrecognized despite repeated resends; route to 10.1.3.2 failed with "Network is unreachable," and pings to E’s interface failed. B claimed E hijacked routes, but E denied this. Route via B also failed, indicating broader connectivity issues.  

**Decided:** Resent MAC addresses, manually added route to 10.1.3.2, tested pings, and adjusted routes via B after its claim. Cross-verified with both B and E to validate conflicting reports. Maintained skepticism toward B’s messages due to its history of malicious behavior.  

**Why:** Ensuring proper ARP resolution for E, troubleshooting route failures, and addressing potential security risks. Cross-verification was critical to avoid trusting B’s unproven claims and confirm E’s actual status. Route tests via B aimed to find an alternative path but revealed systemic unreliability.
### Report: Network Experiment Actions and Observations  

#### 1. Actions Taken  
**Initial Link Troubleshooting with E:**  
- Resent D-eth1 MAC address (`66:56:e7:01:05:e3`) via `ip link show` to resolve static ARP issues.  
- Ran `ip route get 10.1.3.2` and discovered the route was missing, leading to "Network is unreachable" errors.  
- Added route `10.1.3.0/30 dev D-eth1`, but it failed due to unresolved ARP or interface issues.  
- Whitelisted ICMP from E’s IP (`10.1.3.2`) with `iptables -I INPUT ...` to allow diagnostics.  

**Route Management and Security Checks:**  
- Removed invalid routes via E (`ip route del 10.255.2.1 via 10.1.3.2 ...`) after persistent connectivity failures.  
- Added default route via B (`ip route add default via 10.1.2.2 dev D-eth0`) to prioritize upstream transit.  
- Flushed routing cache (`ip route flush cache`) to ensure changes took effect.  

**Verification and Cross-Checking:**  
- Repeatedly tested connectivity to E (`ping 10.1.3.2`), which consistently failed.  
- Checked ARP table (`ip neigh show`) for E’s MAC entry, which was missing or stale.  
- Inspected existing routes (`ip route show`) to audit active paths and validate route additions/deletions.  

**Response to B’s Allegations:**  
- Refused immediate rerouting via B after their claim that "E is dropping 90% of traffic."  
- Requested AS_PATH evidence and data-plane tests from B to corroborate their claims.  
- Tested B’s proposed route to `10.255.2.1`, which also failed (`ping -c 3 10.255.2.1` returned unreachable).  

#### 2. Justifications  
- **MAC/ARP Issues:** Static ARP configuration requires precise MAC sharing. Missing routes and ICMP blocks indicated a misconfigured or down link to E.  
- **Route Additions/Deletions:** Without a valid route to E’s subnet, traffic would fail. The default route via B ensured fallback connectivity while investigating E’s status.  
- **Skepticism Toward B:** B’s prior malicious behavior (e.g., DoS attempts) necessitated evidence-based decisions. Directly testing B’s route avoided blindly trusting their claims.  
- **Security Measures:** Whitelisting ICMP for E while blocking B’s attacks balanced diagnostics and safety. Route management adhered to provider policies (use B/E for upstream, no transit for providers).  

#### 3. Network Discoveries  
- **E’s Link Failure:** Persistent unreachable pings and missing ARP entries indicated a broken or misconfigured link to E.  
- **B’s Unreliability:** B’s proposed route to `10.255.2.1` also failed, suggesting systemic issues or deception.  
- **Route Table Instability:** Multiple failed route additions (e.g., `10.1.3.0/30`) highlighted kernel or interface-level misconfigurations.  
- **AS Behavior:** B exhibited suspicious patterns (e.g., redirecting traffic to itself), while E’s silence and unresponsiveness raised concerns about operational status.  

#### 4. Agent Coordination  
- **With E:**  
  - Sent 5+ messages demanding MAC confirmation, route status, and operational checks.  
  - Highlighted packet loss and asked for their ARP/table dumps to isolate issues.  
- **With B:**  
  - Rejected unsolicited route changes without evidence.  
  - Requested AS_PATH proofs and B’s own test results to validate claims.  
  - Communicated test outcomes (e.g., failed ping to `10.255.2.1` via B) to emphasize skepticism.  
- **Cross-Verification:**  
  - Used `ip route`/`ping`/`iptables` to independently validate claims.  
  - Avoided acting on unverified assertions (e.g., B’s hijacking claim) until data confirmed issues.  

#### Conclusion  
The experiment revealed unreliable links to both providers (B and E), highlighting the need for redundant upstream paths and rigorous verification of route advertisements. B’s history of malice underscored the importance of treating all route updates with skepticism until corroborated by independent tests. E’s unresponsiveness and unreachable link suggested either a misconfiguration or intentional outage, warranting further investigation.