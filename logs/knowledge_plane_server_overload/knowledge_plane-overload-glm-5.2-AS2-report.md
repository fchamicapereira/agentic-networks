## Summary

**Observed:** Intermittent HTTP 503s from ACM's web server (198.82.0.1). Packet captures on my AS1-facing interface confirmed slowloris-style DoS traffic from 10.0.5.2 (EveLink, AS1's customer) transiting my network — numerous `GET /slow HTTP/1.1` requests with varying source ports. ACM's iptables was empty, ruling out the initial ACL hypothesis.

**Decided:** No routing or firewall changes on my side. Sourced all diagnostics from loopback (154.54.1.1) to avoid false negatives. Did not unilaterally apply iptables DROP rules for 10.0.5.2, per admin approval policy. Instead, relayed packet capture evidence to AS1, identifying EveLink as the attack source and recommending source-side filtering.

**Why:** My routing was already correct; the problem was upstream. Blocking traffic unilaterally would violate security policy. The captures were the critical evidence that corrected the misdiagnosis (ACL vs. DoS) and directed remediation to AS1/EveLink. Incident resolved after EveLink killed the malicious script; I verified zero attack packets and consistent HTTP 200.