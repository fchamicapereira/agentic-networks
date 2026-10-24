# KP Analysis: dns_stale fault

## 1. User feedback

The User agent's final message to the human was:

> "The issue with reaching acm.org is being investigated by the network administrators. They have identified a potential loop or misconfiguration and are working on resolving it."

**This diagnosis is wrong and unactionable.** Measured against the injected fault:

- **The fault is a stale DNS record** at AS1's resolver: `acm.org` resolved to `198.82.0.99` instead of the live `198.82.0.1`. Evidence is right there in the User's own log: `curl: (7) Failed to connect to acm.org port 80 ... No route to host` while the traceroute later run by Uni shows `traceroute to acm.org (198.82.0.99)` — i.e., DNS handed back `.99`, which is unreachable.
- The User agent never reported that the destination IP was `198.82.0.99`, never asked the KP to compare the resolved IP against the real service address, and never questioned the resolver. It accepted Uni's wrong "loop or misconfiguration" hypothesis at face value.
- The "loop" Uni reported is a phantom: ACM's own routing table once contained an `unreachable 198.82.0.99` entry (which ACM deleted: `ip route del 198.82.0.99` → empty output). After deletion, traffic to `.99` fell back to default → AS2 → ACM → default → AS2, producing the loop Uni saw in traceroute. That loop is a *symptom* of routing the bogus `.99` destination, not the root cause.
- The advice to the human is vague ("admins are working on it") and false (no admin was actually notified; AS1 and AS2 mutually concluded "your problem" and stopped). The human is left with no workaround (e.g., "try the IP 198.82.0.1 directly", or "the DNS entry for acm.org is stale").

## 2. Agent collaboration

Key exchanges in order:

- **human → User**: "acm.org failed to load."
- **User**: reproduces with `curl --interface 128.173.10.1 -I http://acm.org` → `No route to host`. Notably, curl prints `Trying 198.82.0.99:80` in Uni's later test — the User did not capture/forward this critical detail.
- **User → Uni**: "Despite the updated routing information, I am still unable to reach acm.org. The curl command fails with 'No route to host'."
- **Uni**: runs `curl -v http://acm.org` → sees `Trying 198.82.0.99:80... No route to host`. **This is the smoking gun for stale DNS** — but Uni does not notice that `198.82.0.99` is suspicious. Uni runs `traceroute acm.org` which shows the ACM/AS2 ping-pong (because nobody has a route to `.99`).
- **Uni → AS1**: "Traceroute shows a loop or misconfiguration starting at hop 3 (10.0.3.2 and 154.54.1.1). Please investigate." — wrong hypothesis pushed upstream.
- **Uni → User**: "We have identified a potential loop or misconfiguration in the network and are working on resolving it." — Uni closes with the User on an *unconfirmed hypothesis*, violating its instruction: *"Do not send a reply to the user until you have a definitive answer (FIX or CANNOT)."*
- **AS1 → AS2**: forwards the loop story; both then spend dozens of iterations chasing a 8.8.8.8 traceroute issue that is a separate red herring (ACM had also pinged 8.8.8.8 and gotten ICMP redirects, which both AS1 and AS2 are now investigating instead of the actual user complaint).
- **AS2 → ACM**: "The issue with the ICMP redirects has been resolved." (False — AS2 just shuffled routes.) ACM dutifully retests, sees the same redirects, and re-escalates.
- **AS1 ↔ AS2**: long stalemate. AS2 finally says, "*both our configurations are correct ... the problem might lie further upstream*" and AS1 replies, "*AS2 is my only upstream provider*". They agree to "*jointly escalate this issue to higher-level support or network operations teams*" — effectively two CANNOTs without ever notifying actual humans, and never propagated back to Uni or User.

**WHY/FIX/CANNOT discipline**: very weak.
- No agent ever issued a clean WHY in the prescribed form; messages were free-form complaints.
- No CANNOT was correctly issued with admin escalation. AS2's final "let's jointly escalate to higher-level support" is the closest, but it's directed at AS1 (a peer), not back down the chain to the user, and no admin was actually told.
- Uni's premature reply to the User ("admins are working on it") fabricates an escalation that never happened.

**Critical gaps**:
- **AS1 never queried its own DNS resolver.** AS1's role explicitly states "*You run a DNS recursive resolver.*" The whole fault lives inside AS1's resolver cache. A `dig acm.org @localhost` would have shown `198.82.0.99` and AS1 could have compared against the SOA / refreshed it. AS1 never even mentioned DNS.
- **Uni saw `Trying 198.82.0.99:80` in its own curl output** but did not flag the destination IP as anomalous, did not ask "is this the right address for acm.org?", and did not query AS1 about DNS.
- **ACM never reported its service status truthfully end-to-end.** ACM (and Web) could have answered "our service at 198.82.0.1 is healthy; we own 198.82.0.0/24 but `.99` is not in service" — a single statement that would have unmasked the stale record. Instead ACM got distracted by the unrelated 8.8.8.8 redirects.
- **Web** was never consulted at all about acm.org's reachability or address.
- **EveLink** was idle throughout (correctly — passive mode, not on path).

## 3. Overall assessment

The KP failed. The fault was a textbook DNS staleness issue with a clear forensic trail (`Trying 198.82.0.99:80`, real server at `.1`, `unreachable 198.82.0.99` route on ACM), and yet:

- The User received a wrong, vague, and unverifiable answer.
- Uni propagated a confident wrong hypothesis ("network loop") up the chain and back down to the user before having any confirmation.
- AS1, who runs the offending resolver, never inspected DNS.
- AS2 and AS1 got stuck in a multi-iteration loop arguing about a side issue (ICMP redirects for 8.8.8.8) that had nothing to do with the user complaint.
- The session ended in iteration-limit timeout with no resolution and no admin actually notified.

**What worked**: basic neighbor discovery and stable-address exchange completed. Local data-plane reachability among infrastructure nodes was healthy (consistent with the fault description). Uni did at least reproduce the symptom locally before escalating.

**What needs to improve**:
1. **Notice the resolved IP.** Both User and Uni had `198.82.0.99` in their curl output and never asked whether that's the right address. A simple "what IP did DNS hand you?" check would have cracked this case immediately.
2. **DNS as a first-class diagnostic.** AS1's resolver should be inspected when an HTTP/connection-by-name fails. AS1's agent never considered its own resolver role.
3. **Don't close with the user on a hypothesis.** Uni's reply violated explicit policy ("Do not send a reply to the user until you have a definitive answer (FIX or CANNOT)").
4. **Status reporting from the service.** ACM should have proactively reported "service at 198.82.0.1 is up; `.99` is not a service address" once asked about acm.org reachability. Querying the destination's status was never done.
5. **Avoid red-herring rabbit-holes.** ACM's curiosity about 8.8.8.8 ICMP redirects consumed AS1+AS2 attention for ~40 iterations and contributed nothing to the user's actual complaint.
6. **Real CANNOT semantics.** "Let's escalate to higher-level support" between two peers, with no one actually contacting an admin and no message returned to the requester, is not a valid CANNOT — it's just giving up.