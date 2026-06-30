Observed: Routing loop on 128/8 resolved via static route and disabled redirects; ACM server (198.82.0.1) unreachable due to misconfigured routes (EveLink instead of AS2), command typos ("rote"), and incorrect subnet masks (/8 vs. /30). AS2 confirmed ACM's issue stemmed from their own configuration.  

Decided: Correct route to point to AS2, fix typo, adjust subnet to /30, update loopback script, and coordinate with Uni/AS2 to confirm changes.  

Why: Static route/redirection fix halted loops; precise AS2 route ensured proper path; subnet correction targeted ACM’s specific subnet; script fix avoided errors; coordination aligned configurations and informed stakeholders.
### **Experiment Report**  

---

#### **1. Actions Taken**  
- **Initial Loop Resolution**:  
  - Configured static route `128.0.0.0/8 via 10.0.1.1` (Uni) to break a routing loop.  
  - Disabled IP redirects (`sysctl net.ipv4.conf.all.send_redirects=0`) to prevent loop reoccurrence.  
  - Validated connectivity via `ping` and `traceroute` from loopback.  

- **ACM Connectivity Issues**:  
  - Added route `198.0.0.0/8 via 10.0.2.2` (AS2) but encountered packet loss.  
  - Diagnosed misconfigured route pointing to EveLink (`198.82.0.0/30 via AS1-eth2`) and deleted it.  
  - Corrected route to ACM’s specific subnet `198.82.0.0/30 via 10.0.2.2` (AS2).  
  - Fixed loopback address retrieval syntax in `ping`/`traceroute` commands (e.g., `$(ip addr show lo | grep -Po 'inet \K\d+\.\d+\.\d+\.\d+' | head -n1)`).  

- **Validation & Communication**:  
  - Ran `ip route show` to audit routing table for conflicts.  
  - Sent messages to AS2 to confirm route stability and inform of corrections.  
  - Notified Uni of loop resolution and ACM service updates.  

---

#### **2. Justifications**  
- **Static Route for 128/8**: The loop was caused by a recursive route pointing back to AS1. The static route forced traffic toward Uni, the correct upstream.  
- **Redirect Suppression**: Redirects could have caused asymmetric paths, exacerbating the loop. Disabling them ensured deterministic routing.  
- **Specific ACM Route**: The `/30` subnet for ACM (198.82.0.0/30) takes precedence over broader `/8` routes, avoiding misdirection to EveLink.  
- **Loopback Syntax Fixes**: Prior commands used `lo` directly, causing errors. Capturing the loopback IP dynamically ensured source addresses were valid for replies.  
- **Route Deletion (EveLink)**: The incorrect route via EveLink (a customer link) violated peering agreements and caused invalid paths. Removing it enforced policy compliance.  
- **Peer Coordination**: AS2 confirmed ACM’s subnet ownership, so further fixes required ACM’s intervention. AS1’s role was to ensure its own routing alignment.  

---

#### **3. Network Discoveries**  
- **Routing Conflicts**: Broad routes (e.g., `198.0.0.0/8`) can override specific paths if not properly managed. The ACM subnet required a `/30` route to avoid interference.  
- **Syntax Errors**: Typos (e.g., `rote` instead of `route`) and incorrect loopback references caused command failures. Rigorous validation of scripts was critical.  
- **Path Instability**: AS2 reported ACM’s subnet (198.82.0.0/30) as unstable, indicating the issue originated at ACM, not AS1’s configuration.  
- **Interface Misuse**: Routing ACM traffic via EveLink (AS1-eth2) violated peering policies, as EveLink is a customer, not a transit path for external routes.  

---

#### **4. Coordination with Other Agents**  
- **AS2**:  
  - Requested path confirmation and notified of route changes (e.g., ACM subnet correction).  
  - Received updates on ACM’s responsibility for instability, guiding AS1 to avoid unnecessary reconfiguration.  
- **Uni**:  
  - Informed of loop resolution and ACM service status to align expectations.  
- **EveLink**:  
  - No direct coordination, but misrouted ACM traffic via EveLink was corrected to prevent policy violations.  

---

**Conclusion**: The experiment highlighted the importance of precise route specificity, syntax accuracy, and peer coordination. While AS1 resolved its local misconfigurations, ACM’s subnet instability underscored the dependency on upstream providers and the need for clear fault isolation through the Knowledge Plane.