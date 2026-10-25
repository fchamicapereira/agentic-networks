Experiment Report — ACM KP Agent

1. Actions taken

- Performed a local audit after receiving AS2’s KP WHY/FIX request for acm.org / 198.82.0.1.
- Ran:
  - `ip addr show lo`
  - `ip addr show`
  - `ip route show`
  - `ping -c 3 -I <ACM-loopback> 198.82.0.1`
  - `curl -k -sS -o /tmp/acm_curl_body -D /tmp/acm_curl_headers --resolve acm.org:443:198.82.0.1 https://acm.org/ || true`
- Confirmed ACM’s stable loopback address was `198.82.0.254/32`.
- Confirmed interfaces were up:
  - `ACM-eth0` toward AS2: `10.0.3.2/30`
  - `ACM-eth1` toward Web: `10.0.4.1/30`
  - `lan0`: `198.82.0.254/24`
- Confirmed routing table included:
  - Default route via AS2: `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - Route to Web service: `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`
- Verified ICMP reachability from ACM to `198.82.0.1` using ACM’s loopback source. Ping succeeded with 0% loss.
- Verified the reported HTTPS symptom locally. HTTPS to `https://acm.org/` resolved to `198.82.0.1` completed but returned:
  - `HTTP/1.1 503 Service Unavailable`
  - `Server: acm-dl/2.3`
  - Body: `503 Service Unavailable`

- Sent an internal KP WHY/FIX request to the directly connected Web agent, describing the observed service-layer failure and asking it to audit the host/application.

- Received Web’s diagnosis and fix report.
  - Web found routing and listeners healthy.
  - Web reproduced the 503 locally.
  - Web diagnosed application-level worker starvation.
  - Web applied a local, low-risk, reversible application change and restarted the service.
  - Web verified local HTTPS and HTTP returned 200 OK.

- Re-tested from ACM after Web’s fix with:
  - `curl -k -sS -o /tmp/acm_verify_body -D /tmp/acm_verify_headers --resolve acm.org:443:198.82.0.1 https://acm.org/`
- Confirmed the original symptom was resolved:
  - HTTPS returned `HTTP/1.1 200 OK`
  - Server remained `acm-dl/2.3`
  - Response body contained the ACM Digital Library HTML page.

- Sent a KP FIX result back to AS2, asking AS2 to relay the result to AS1/Uni.
- Reported externally only the public service status and that ACM had applied a local application-service fix. I did not disclose internal application implementation details to AS2.

- No routing rules were added or deleted during this experiment.

2. Justification behind each decision

- I audited ACM locally before escalating because the KP role requires local investigation first. AS2 had already shown network reachability and TLS completion, but I needed to confirm whether the failure was observable from ACM’s own vantage point.

- I used ACM’s loopback address as the source for diagnostic traffic because the instructions specified that loopback is the stable routable address and link addresses are only point-to-point infrastructure addresses. This avoided misleading results caused by replies to non-routable link-source addresses.

- I checked interface and routing state to distinguish between network-layer failure, local forwarding failure, and service/application failure.

- I used `curl --resolve acm.org:443:198.82.0.1` so that the test used the intended service IP while preserving the correct HTTPS Host/SNI name, `acm.org`.

- I did not make any routing changes because routing was already converged and correct:
  - ACM could reach Web.
  - AS2 could reach ACM’s service prefix.
  - Ping and TLS both worked.
  - The failure was HTTP 503, indicating an application/service issue rather than a routing failure.

- I escalated to Web because Web is the host within ACM’s organization running the service at `198.82.0.1`, and ACM is allowed to share internal information with Web.

- I waited for Web’s response rather than attempting unauthorized service changes from ACM, because the service process lived on Web.

- After Web reported a fix, I independently verified from ACM before reporting success. This followed the requirement to confirm that the original symptom was gone before declaring the problem fixed.

- In the external report to AS2, I avoided leaking ACM-internal root-cause details. The service status and high-level fact that an ACM local application-service fix was applied were appropriate to disclose publicly, but the detailed implementation cause was internal to ACM.

3. What I discovered about the network

- ACM’s stable loopback address is `198.82.0.254/32`.

- ACM has these relevant connected interfaces:
  - `ACM-eth0` to AS2 with ACM IP `10.0.3.2/30`, peer `10.0.3.1/30`.
  - `ACM-eth1` to Web with ACM IP `10.0.4.1/30`, peer `10.0.4.2/30`.
  - `lan0` on `198.82.0.254/24`.

- ACM’s routing was healthy:
  - Default traffic exits via AS2.
  - Traffic to the web service IP `198.82.0.1` is routed via Web peer `10.0.4.2` on `ACM-eth1`.
  - The route to `198.82.0.0/24` exists on `lan0`.

- Network reachability to `198.82.0.1` was working:
  - ICMP from ACM to Web succeeded with 0% loss.
  - AS2 also reported successful ping from its loopback to `198.82.0.1`.
  - TLS sessions to `198.82.0.1` completed.

- The observed outage was not caused by AS1, AS2, ACM routing, or basic reachability. It was a service-layer failure: HTTPS returned `503 Service Unavailable`.

- After Web’s local fix, the ACM Digital Library service at `198.82.0.1` returned `HTTP/1.1 200 OK` for `https://acm.org/`.

4. Coordination with other agents

- AS2 contacted ACM with a relayed KP WHY/FIX request on behalf of AS1/Uni. AS2 provided its local audit results showing:
  - AS2 interfaces were up.
  - AS2 had a route to `198.82.0.0/24` via ACM.
  - Ping to `198.82.0.1` succeeded.
  - HTTPS completed TLS but returned 503.
  - AS1 and Uni observed the same symptom.

- I coordinated internally with Web by sending a KP WHY/FIX request. I included:
  - ACM’s routing and reachability observations.
  - The confirmed HTTPS 503 response.
  - A request for Web to audit the host/application and apply a local low-risk fix if authorized.

- Web replied with:
  - Confirmation that the web host routing and listeners were healthy.
  - Local reproduction of the HTTPS 503.
  - Diagnosis of application-level worker starvation.
  - Confirmation that it applied a local reversible application fix and restarted the service.
  - Verification that HTTPS and HTTP returned 200 locally.

- I then verified the fix independently from ACM and reported the service restoration to AS2. I asked AS2 to relay the result to AS1/Uni and re-test from their vantage points.