**Observed**:  
- Failed ping to 8.8.8.8 ("Destination Net Unreachable"), existing default route to 10.3.4.1.  
- `birdc` command unavailable (blocked by rules).  
- Incorrect loopback extraction (`$NF` vs `$4`), missing local route for 45.32.0.0/24.  
- ISP initially didn’t propagate TinyInc’s prefix; IPv6 test irrelevant to IPv4 issue.  

**Decided**:  
- Avoid re-adding default route; use `send_message` to notify ISP.  
- Fix loopback capture with `$4`, add `ip route local` for prefix ownership.  
- Retry pings with corrected variables; ensure `report_done` is standalone.  

**Why**:  
- Prevent route duplication errors; comply with no-daemon rules.  
- Accurate loopback ensures stable pings; local route avoids routing blackholes.  
- ISP coordination required for prefix advertisement; isolate final report call to avoid conflicts.
**Report: TinyInc Network Configuration and Connectivity Experiment**  

---

### 1. Actions Taken  
- **Loopback Configuration**:  
  - Verified loopback address using `ip addr show lo`, confirming `45.32.0.1/32` was assigned.  
  - Added a local route for the allocated prefix: `ip route add local 45.32.0.0/24 dev lo` to ensure ownership.  

- **Default Route Configuration**:  
  - Confirmed default route via ISP gateway (`10.3.4.1`) with `ip route show`.  
  - Avoided re-adding the route after detecting it already existed to prevent errors.  

- **ISP Coordination**:  
  - Sent manual advertisements via `send_message` to ISP:  
    ```  
    "Please advertise my allocated prefix 45.32.0.0/24 originated from AS-TINYINC (loopback: 45.32.0.1)"  
    ```  
  - Followed up with reminders to ensure the ISP propagated the route.  

- **Connectivity Testing**:  
  - Used corrected loopback capture syntax (`$4` in `awk` instead of `$NF`) to avoid errors:  
    ```  
    LOOP=$(ip -o -4 addr show dev lo scope global | awk '{print $4}' | cut -d/ -f1)  
    ```  
  - Tested reachability to ISP gateway (`10.3.4.1`) and external DNS (`8.8.8.8`) using:  
    ```  
    ping -c3 -I$LOOP 10.3.4.1 && ping -c3 -I$LOOP 8.8.8.8  
    ```  

- **Policy Compliance**:  
  - Avoided BGP daemons (e.g., `birdc`), adhering to the rule to manage routes manually.  
  - Ensured no private link subnets (e.g., `10.3.4.0/30`) were advertised externally.  

---

### 2. Justifications  
- **Loopback Configuration**:  
  - A stable loopback address (`45.32.0.1`) is critical for end-to-end connectivity and routing consistency.  
  - The local route (`45.32.0.0/24 dev lo`) ensures traffic destined to TinyInc’s prefix is correctly handled locally.  

- **Default Route**:  
  - The route via `10.3.4.1` is TinyInc’s only provider, ensuring all external traffic flows through the ISP. Re-attempting its addition caused errors, so we validated it first.  

- **Manual ISP Coordination**:  
  - BGP daemons were prohibited, so explicit messaging was the only way to advertise the prefix. The ISP’s role as a transit provider necessitated their cooperation to propagate routes globally.  

- **Loopback Capture Fix**:  
  - Using `$NF` incorrectly captured the interface name (`lo`), causing `ping` failures. Switching to `$4` retrieved the correct IP (`45.32.0.1`).  

- **IPv4 Focus**:  
  - The problem was IPv4-specific (prefix `45.32.0.0/24`), so IPv6 tests were abandoned after a hostname resolution error.  

---

### 3. Network Discoveries  
- **ISP Dependency**: External reachability entirely relies on the ISP’s route advertisement. Without their cooperation, the prefix remains unreachable.  
- **Routing Rules**:  
  - The ISP’s default route (`10.3.4.1`) must exist for any external traffic.  
  - `ping` failures (e.g., `Destination Net Unreachable`) indicated the ISP had not yet propagated TinyInc’s prefix.  
- **Tool Limitations**:  
  - `birdc` (BGP tool) was unavailable, necessitating manual route management.  
  - Shell syntax errors (e.g., incorrect `awk` fields) caused critical command failures.  

---

### 4. Agent Coordination  
- **Messages to ISP**:  
  - Sent two reminders to ensure the ISP advertised `45.32.0.0/24`. The first message was a request, the second a reminder referencing IRR records (`AS-TINYINC`).  
- **No Other Peers**:  
  - TinyInc has no customers or peers, so coordination was limited to the ISP.  
- **Assumptions**:  
  - Trusted the ISP to honor TinyInc’s prefix advertisement request, as per the provider-customer relationship.  

---

### Final State  
- **Success**:  
  - The ISP eventually propagated the prefix, enabling successful pings to `8.8.8.8` via the loopback source.  
  - All routing rules (customer preference, no private advertisement) were followed.  
- **Completion**:  
  - `report_done` was called alone after verifying internal and external connectivity, fulfilling the experiment’s goals.