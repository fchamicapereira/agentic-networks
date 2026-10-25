Experiment report — AS2 KP agent

1. Actions taken

- Received a KP WHY request from AS1 on behalf of Uni for `acm.org / 198.82.0.1`.
  - AS1 reported that DNS resolved `acm.org` to `198.82.0.1`.
  - Uni and AS1 could both ping `198.82.0.1` successfully.
  - HTTPS connected and completed TLS, but the ACM server returned:
    - `HTTP/1.1 503 Service Unavailable`
    - `Server: acm-dl/2.3`

- Performed a local audit on AS2 before escalating.
  - Ran:
    - `ip -4 addr show lo`
    - `ip -br addr show`
    - `ip route show`
  - Identified AS2 loopback/stable address:
    - `154.54.1.1`
  - Confirmed interfaces were up:
    - `AS2-eth0` toward AS1: `10.0.2.2/30`
    - `AS2-eth1` toward ACM: `10.0.3.1/30`
  - Confirmed route to ACM web prefix:
    - `198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- Verified reachability and service behavior from AS2’s loopback.
  - Ran:
    - `ping -c 3 -I 154.54.1.1 198.82.0.1`
    - `curl -sk --connect-timeout 5 --max-time 10 --interface 154.54.1.1 -D - https://198.82.0.1/`
  - Result:
    - ICMP ping succeeded with 0% loss.
    - HTTPS connected but returned:
      - `HTTP/1.1 503 Service Unavailable`
      - `Server: acm-dl/2.3`
      - Body: `503 Service Unavailable`

- Sent a KP WHY/FIX request to ACM.
  - Reported that AS2 had confirmed routing and reachability were healthy.
  - Reported that the failure was reproducible as an HTTP 503 after TLS completion.
  - Asked ACM to investigate the local service at `198.82.0.1` and either fix it or return `CANNOT`.

- Waited for ACM’s response.

- Received ACM’s FIX result.
  - ACM confirmed:
    - Routing and reachability were healthy.
    - TLS completed.
    - The ACM Digital Library service was returning HTTP 503.
  - ACM applied a local application-service fix.
  - ACM reported that no routing, transit, or security/access-control changes were made.
  - ACM verified that `https://acm.org/` now returned:
    - `HTTP/1.1 200 OK`
    - `Server: acm-dl/2.3`

- Independently re-tested from AS2 after ACM’s fix.
  - Ran:
    - `ping -c 3 -I 154.54.1.1 198.82.0.1`
    - `curl -sk --connect-timeout 5 --max-time 10 --interface 154.54.1.1 -D - https://198.82.0.1/`
  - Result:
    - Ping still succeeded with 0% loss.
    - HTTPS now returned:
      - `HTTP/1.1 200 OK`
      - `Server: acm-dl/2.3`
      - HTML page for the ACM Digital Library.

- Sent final KP FIXED result to AS1.
  - Reported that AS2 had reproduced the original 503.
  - Reported that ACM diagnosed and fixed a local application-service problem.
  - Reported that AS2 independently verified the fix.
  - Asked AS1 to relay to Uni and optionally verify from Uni’s loopback.

- No routing changes were made.
  - I did not run any `ip route add` or `ip route del` commands.
  - Existing routing was sufficient and healthy.

2. Justification behind each decision

- I audited AS2 locally before escalating because the KP instructions require local investigation first. Since AS2 is the transit ISP between AS1 and ACM, I needed to confirm whether the fault was in AS2 forwarding, route selection, interface state, or service reachability.

- I sourced diagnostic traffic from AS2’s loopback address `154.54.1.1` because the testbed instructions state that loopback is the stable routable node address. Using link-local point-to-point infrastructure addresses could have caused misleading reply failures.

- I checked interfaces and routes to verify that the path to ACM was installed and that AS2’s directly connected links were operational.

- I used ping to distinguish basic IP reachability from application failure. Since ICMP worked with 0% loss, this suggested that IP forwarding and the AS2-to-ACM route were functioning.

- I used curl over HTTPS to reproduce the exact reported failure. The fact that TCP/TLS succeeded but HTTP returned 503 indicated that the problem was above the network layer, likely in ACM’s web service or application stack.

- I escalated to ACM because ACM is AS2’s customer, owns the service domain for `198.82.0.1`, and was the only party with authority to repair the application/service. Since the evidence showed transit was healthy, a local AS2 routing change was not justified.

- I did not change any routes because there was no routing fault to correct. The route to `198.82.0.0/24` via ACM was present and functional.

- I waited after contacting ACM because the responsible domain needed to investigate and report either a fix or `CANNOT`.

- After ACM reported a fix, I independently verified the original symptom before reporting success, as required by the KP procedure.

3. What was discovered about the network

- AS2’s stable loopback address is:
  - `154.54.1.1`

- AS2’s directly connected links were up:
  - To AS1:
    - Interface: `AS2-eth0`
    - AS2 IP: `10.0.2.2/30`
    - AS1 peer IP: `10.0.2.1/30`
  - To ACM:
    - Interface: `AS2-eth1`
    - AS2 IP: `10.0.3.1/30`
    - ACM peer IP: `10.0.3.2/30`

- AS2 had a working route to ACM’s web prefix:
  - `198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- Network reachability to `198.82.0.1` was healthy throughout the experiment:
  - Ping from AS2 loopback to `198.82.0.1` succeeded with 0% loss before and after the fix.

- The original failure was not DNS, routing, ICMP reachability, TCP connectivity, or TLS negotiation.
  - DNS had resolved correctly.
  - Ping worked.
  - HTTPS connected.
  - TLS completed.
  - The server itself returned HTTP 503.

- The root cause was within ACM’s web application/service layer:
  - ACM confirmed the ACM Digital Library service was returning 503.
  - ACM applied a local application-service fix.
  - After the fix, HTTPS returned `HTTP/1.1 200 OK`.

4. Coordination with other agents

- Coordinated with AS1:
  - Received the original KP WHY request from AS1 on behalf of Uni.
  - Sent AS1 the final FIXED report after ACM fixed the issue and AS2 verified it.

- Coordinated with ACM:
  - Sent ACM a KP WHY/FIX request with AS2’s local evidence.
  - ACM investigated its local service and applied the fix.
  - ACM reported the issue was fixed and provided its own verification.
  - AS2 then independently verified the fix before reporting back to AS1.

- No relay-only forwarding was required beyond direct neighbor messaging:
  - AS1 and ACM are both directly connected AS2 neighbors.
  - No message needed to be relayed through an intermediate agent.

Final status: FIXED. The outage was an ACM application-service failure returning HTTP 503, not a routing or transit problem.