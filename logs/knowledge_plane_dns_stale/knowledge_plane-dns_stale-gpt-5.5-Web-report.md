Experiment report — Web node

1. Actions taken

- Inspected Web’s loopback addresses:
  - Command: `ip addr show lo`
  - Result: Web has `198.82.0.1/32` configured on loopback, in addition to `127.0.0.1/8`.

- Inspected Web’s routing table:
  - Command: `ip route show`
  - Result:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - `10.0.4.0/30 dev Web-eth0 proto kernel scope link src 10.0.4.2`

- Checked listening TCP services:
  - Command: `ss -ltnp`
  - Result:
    - HTTP service listening on `198.82.0.1:80`
    - HTTPS service listening on `198.82.0.1:443`
    - DNS service also listening on `198.82.0.1:53` and `127.0.0.1:53`

- Verified local HTTP health for the ACM Digital Library service address:
  - Command: `curl -sS -o /tmp/acm_http.out -w 'HTTP %{http_code} from %{local_ip} to %{remote_ip}\n' --interface 198.82.0.1 http://198.82.0.1/ && head -c 200 /tmp/acm_http.out`
  - Result: `HTTP 200 from 198.82.0.1 to 198.82.0.1`
  - The returned page content was the ACM Digital Library HTML.

- Verified local HTTPS health for the ACM Digital Library service address:
  - Command: `curl -k -sS -o /tmp/acm_https.out -w 'HTTPS %{http_code} from %{local_ip} to %{remote_ip}\n' --interface 198.82.0.1 https://198.82.0.1/ && head -c 200 /tmp/acm_https.out`
  - Result: `HTTPS 200 from 198.82.0.1 to 198.82.0.1`
  - The returned page content was the ACM Digital Library HTML.

- Checked whether `198.82.0.99` was configured locally:
  - Command: `ip -o addr show | grep -w '198\.82\.0\.99' || true`
  - Result: no output; `198.82.0.99` is not configured on Web.

- Sent a Knowledge Plane response to ACM summarizing the findings:
  - Reported that Web’s actual service address is `198.82.0.1/32`.
  - Reported that `198.82.0.99` is not configured on Web and is not an expected ACM Digital Library service address from this host.
  - Reported that HTTP and HTTPS on `198.82.0.1` are healthy.
  - Recommended ACM investigate DNS, external publication, or stale client configuration causing users to target `198.82.0.99`.

- No routing rules were added, deleted, or modified.

2. Justification behind each decision

- I first audited local state before escalating or drawing conclusions, following the Knowledge Plane requirement to investigate locally before attributing the issue to another domain.

- I checked `ip addr show lo` because the loopback address is the stable node/service address and the likely address used for ACM’s public service.

- I checked `ip route show` to confirm Web’s forwarding and source-address behavior, and to verify whether any route or host configuration existed for the reported problematic address.

- I checked `ss -ltnp` to confirm whether the HTTP/HTTPS service was actually listening, and on which IP addresses.

- I tested HTTP and HTTPS directly against `198.82.0.1`, explicitly using `--interface 198.82.0.1`, because diagnostics to non-adjacent or service addresses should be sourced from the stable loopback address. This verified the service from the Web host’s own vantage point.

- I checked for `198.82.0.99` on all interfaces because ACM specifically asked whether that address was configured or expected to serve `acm.org`.

- I did not configure any route changes because the local route table was consistent with the node’s role, the actual service was healthy, and the reported failure concerned an address not assigned to Web. There was no evidence of a local routing fault to fix.

- I sent the result to ACM because ACM was the requesting neighbor and organizational peer responsible for deciding the next external-facing diagnostic or remediation step.

3. What I discovered about the network

- Web’s stable loopback/service address is `198.82.0.1/32`.

- The ACM Digital Library HTTP server is bound to Web’s loopback address:
  - `198.82.0.1:80`
  - `198.82.0.1:443`

- The ACM Digital Library service is locally healthy:
  - HTTP returned `200`.
  - HTTPS returned `200`.
  - Both returned ACM Digital Library page content.

- `198.82.0.99` is not configured on Web and is not the expected service address for the ACM Digital Library from this host.

- Web’s only physical neighbor is ACM over `Web-eth0`:
  - Web IP: `10.0.4.2/30`
  - ACM peer IP: `10.0.4.1/30`

- Web’s routing table uses ACM as its default gateway:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- The symptom reported by ACM — traffic to `198.82.0.99` falling to a local `198.82.0.0/24` LAN and failing ARP — is consistent with users or some external system targeting the wrong/nonexistent service address, not with a failure of the Web host or its HTTP service.

4. Coordination with other agents

- I coordinated only with ACM, Web’s directly connected neighbor and organizational peer.

- ACM sent a KP internal WHY request asking whether `198.82.0.99` was configured or expected to serve `acm.org`, and asking for verification of the actual ACM service address health.

- After local investigation, I replied to ACM with a KP WHY response containing:
  - Web’s configured service address: `198.82.0.1/32`
  - Confirmation that `198.82.0.99` is not configured locally
  - Confirmation that HTTP and HTTPS on `198.82.0.1` returned status `200`
  - Diagnosis that Web is healthy and that the issue likely lies in DNS, external publication, or stale client configuration pointing users to `198.82.0.99`

- No relay requests were received or forwarded.

- No administrative changes were requested or applied.