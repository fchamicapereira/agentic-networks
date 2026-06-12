# AS2 Experiment Report

## 1. Actions Taken

**Discovery & local inventory**
- `ip addr show lo` → loopback 10.255.3.1/32.
- `ip addr` and `ip route show` → confirmed two interfaces (AS2-eth0 to AS1 peer, AS2-eth1 to ACM customer) and a pre-installed default via AS1 plus customer-side routes (10.0.4.0/30, 10.255.1.1, 10.255.7.1, 198.82.0.1) via ACM at 10.0.3.2.

**Routing exchange**
- Sent initial advertisements to AS1 (peer) and ACM (customer) and asked for theirs.
- ACM confirmed it only originates 10.255.1.1/32 and 198.82.0.1/32; 10.255.7.1 and 10.0.4.0/30 are ACM-internal.
- Sent a corrected, authoritative advertisement to AS1: 10.255.3.1/32, 10.255.1.1/32, 198.82.0.1/32 only.
- AS1 advertised: 10.255.2.1/32 (AS1), 10.255.5.1/32 (Uni), 10.255.6.1/32 (User), 10.255.4.1/32 (EveLink). I installed them:
  - `ip route add 10.255.2.1/32 via 10.0.2.1 dev AS2-eth0`
  - `ip route add 10.255.5.1/32 via 10.0.2.1 dev AS2-eth0`
  - `ip route add 10.255.6.1/32 via 10.0.2.1 dev AS2-eth0`
  - `ip route add 10.255.4.1/32 via 10.0.2.1 dev AS2-eth0`
- Verified reachability with `ping` to all four AS1-side loopbacks plus 10.255.1.1 and 198.82.0.1 — 0% loss everywhere.

**KP WHY investigation (10.0.0.99 / acm.org)**
- `ip route get 10.0.0.99` → matched default via 10.0.2.1 (AS1), confirming my side has no specific route and falls back to default — exactly the behavior that produces a ping-pong with AS1, who also defaults to me.
- `ss -tulnp | grep :53` and `ps aux | grep dnsmasq` → found multiple dnsmasq instances on the host:
  - On 10.255.3.1 (my loopback): `--address=/acm.org/198.82.0.1` — correct.
  - On 10.255.2.1 (AS1's loopback): `--address=/acm.org/10.0.0.99` — stale.
  - A user-side dnsmasq pointing at 10.255.2.1 as upstream.
- Confirmed externally with `dig`: `@10.255.3.1 acm.org → 198.82.0.1`, `@10.255.2.1 acm.org → 10.0.0.99`.
- Sent a KP diagnosis to AS1 with FIX recommendation (correct the static entry on their resolver).
- After AS1 reported the fix, re-ran `dig @10.255.2.1 acm.org` → `198.82.0.1` ✓. Symptom verified gone.

## 2. Justification for Each Decision

- **Advertise only my loopback + customer prefixes to AS1.** Standard transit policy: a peer should only see my own and my customers' prefixes, not internal transit links or someone else's internals. After ACM confirmed 10.255.7.1 and 10.0.4.0/30 were internal, I explicitly withdrew them from the advertisement.
- **Install AS1's four loopbacks via 10.0.2.1.** Concrete /32 next-hops were given and AS1 is my peer; routes are low-risk, easily reversible, and required to reach AS1's customers.
- **Default route via AS1 left in place.** Pre-installed; appropriate for upstream reachability and didn't conflict with anything ACM owns.
- **Did not suppress ICMP redirects, did not install a null route for 10.0.0.99.** The "loop" is the correct behavior for a destination nobody owns; suppressing redirects would mask a symptom whose true cause was DNS. Also, changes to ICMP behavior touch other parties' traceroute observations, so I deferred the decision to AS1 (who declined — agreed).
- **Did not modify AS1's resolver.** That host is in AS1's administrative domain. Per the admin-approval policy, fixing it from my side would be both out of scope and overreach. I produced a clear FIX recommendation instead.
- **Verified the fix directly with `dig` before reporting success.** The instructions explicitly required confirming the symptom was gone via direct observation, not just trusting the remote agent's report.

## 3. What I Discovered About the Network

- Topology around me: AS1 (peer) on eth0, ACM (customer) on eth1; behind AS1 sit Uni and User (and EveLink); behind ACM sit the acm.org web server (198.82.0.1) and internal infra (10.255.7.1, 10.0.4.0/30).
- Both AS1 and AS2 carry a default route pointing at each other for unknown destinations — typical peer-with-default arrangement that becomes a TTL-bounded loop for unowned addresses.
- Three DNS resolvers coexist on this testbed host: mine on 10.255.3.1 (correct), AS1's on 10.255.2.1 (was stale), and the user-side resolver forwarding to 10.255.2.1. The naming-layer bug is what users actually experienced; the data-plane loop was just its tail.
- End-to-end latencies (one-way ping RTT) reflect the topology: ACM ~30 ms, AS1 ~40 ms, Uni ~60 ms, User ~64 ms.

## 4. Coordination With Other Agents

- **ACM (customer):** Exchanged prefix advertisements, clarified which prefixes were ACM-originated vs. internal, confirmed default route via me, offered my DNS resolver, and shared the externally-reachable loopback list (AS1, Uni, User, EveLink, me) for their end-to-end testing. Informed them when AS1 fixed the DNS bug.
- **AS1 (peer):** Exchanged advertisements, reconciled an initial over-broad advertisement from me (I withdrew 10.255.7.1, 10.0.3.0/30, 10.0.4.0/30 from external propagation), installed their four customer/loopback prefixes. Handled their KP WHY for 10.0.0.99: delivered diagnosis (stale DNS at 10.255.2.1, not a routing bug on my side), recommended FIX on their resolver, and after they applied it, independently verified with `dig` and confirmed closure. Returned CANNOT for any further action on my side since the residual data-plane behavior is correct for an unowned destination.