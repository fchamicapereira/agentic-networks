# H Stub AS — Experiment Report

## 1. Actions Taken

**Discovery**
- Ran `ip addr show` and `ip route show`. Found loopback 10.255.8.1/32 and eth0 link 10.1.3.1/30 to B (peer 10.1.3.2). No routes installed.

**Routing setup**
- Attempted `ip route add default via 10.1.3.2`, which failed because the gateway was not yet on-link (the /30 was treated correctly, but the kernel rejected the gateway resolution at that moment).
- Worked around it with:
  - `ip route add 10.1.3.2/32 dev H-eth0`
  - `ip route add default via 10.1.3.2`
- Final route table: default via 10.1.3.2 dev H-eth0; 10.1.3.2 dev H-eth0 scope link.

**Coordination with B**
- Sent B my loopback (10.255.8.1/32) and confirmed no downstream customers, asking it to advertise the loopback globally.
- B confirmed installation and global advertisement, and provided a list of 14 known global prefixes.

**Connectivity verification**
- Pinged each known global prefix sourced from my loopback: `ping -I 10.255.8.1 -c N <dst>`.
- Initial sweep: 11/14 reachable; 10.255.4.1, 10.255.12.1, 10.255.13.1 failed.
- Per policy, kept the (only and preferred) path via B installed and retried after waits. After convergence, all 14 prefixes were reachable.
- Reported results to B.

## 2. Justifications

- **Default route via B**: As a stub AS with B as sole provider, a single default route is the simplest and correct configuration. There is no other upstream and no customers, so no alternate paths or selective routes are needed.
- **Advertising only the loopback**: Rules forbid advertising point-to-point/infrastructure prefixes (the /30 link). The loopback is the only legitimate prefix I should originate. I have no customers, so no customer prefixes to re-advertise.
- **No transit provided**: H is a stub; I do not relay traffic between others. With only one neighbor and no customers, this is automatic.
- **Source pings from loopback**: Link IPs (10.1.3.0/30) are not advertised globally, so replies to them might not return. The loopback is the announced, routable address.
- **Held the preferred path through failures**: Rules require not abandoning a policy-preferred path on transient failures. With only one provider, switching wasn't an option anyway, but I still followed retry-then-decide discipline. Patience paid off — all destinations converged.
- **Did not disclose policy details to B**: Communication stayed factual (loopback, route status, ping results) without revealing preferences or contracts. B is my provider and only sees what it needs.

## 3. Network Discoveries

- I have exactly one neighbor: B (10.1.3.2), my provider, loopback 10.255.2.1/32.
- The global topology contains at least 14 advertised loopback prefixes in 10.255.0.0/16: A=10.255.1.1, B=10.255.2.1, C=10.255.3.1, D=10.255.4.1, plus 10.255.5.1 through 10.255.7.1, I=10.255.9.1, 10.255.10.1–10.255.15.1.
- B has visibility into A (peer), D (customer), I (customer), and learns more from its peers.
- Routing convergence was not instantaneous; some destinations took multiple tens of seconds to become reachable after initial advertisement, confirming that transient unreachability is expected during propagation and that the "don't abandon preferred path" rule has real operational value.

## 4. Coordination With Other Agents

Only B was contacted (my sole neighbor and provider):
1. B greeted me, offered global connectivity, and requested my loopback and any customer prefixes.
2. I replied with 10.255.8.1/32, declared no customers, and confirmed the default route via 10.1.3.2.
3. B confirmed my prefix was installed and globally advertised, verified reachability from its loopback, and shared the full list of 14 known prefixes.
4. After my connectivity sweep, I shared the reachable/unreachable list with B (informational; not as a request to change policy). All destinations subsequently converged.

No communication with any other AS was necessary or appropriate for a stub.