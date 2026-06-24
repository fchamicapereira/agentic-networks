# C's Experiment Report

## 1. Actions Taken

**Discovery / inventory**
- Ran `ip addr show lo` → discovered my loopback 193.43.0.1/32.
- Ran `ip route show` → confirmed only the two directly-connected /30 link subnets were known.

**Route installation**
- `ip route add default via 10.0.3.1` — default route via provider S.
- `ip route add 137.21.0.1/32 via 10.0.3.1` — explicit route to S's loopback (redundant with default but harmless and explicit).
- `ip route add 206.81.0.1/32 via 10.0.6.2` — route to customer D's loopback.

**Advertisements (via send_message)**
- To S (provider): announced 193.43.0.1/32 [C] and 206.81.0.1/32 [C, D].
- To D (customer): offered transit and asked them to default-route to 10.0.6.1; later shared my loopback 193.43.0.1/32 on request.
- To D: did not pass any specific upstream prefixes — D uses default via me.

**Verification**
- `ping -I 193.43.0.1` to 137.21.0.1 (S), 12.84.0.1 (A), 89.248.0.1 (B), 206.81.0.1 (D). All four eventually succeeded.

## 2. Justification

- **Default via S**: S is my provider and pays no policy cost for me to use them for unknown destinations. Single default keeps my FIB small.
- **Specific /32 to D via 10.0.6.2**: D is my customer, so I must carry their traffic and announce them upstream.
- **Advertising 206.81.0.1/32 to S with AS-path [C, D]**: customer prefixes get advertised to providers — that's how D gets global reach and how I earn transit revenue from D.
- **Advertising 193.43.0.1/32 to S**: needed for the rest of the network to reach me.
- **Not advertising 10.0.3.0/30 or 10.0.6.0/30**: rules forbid leaking P2P link subnets; they are private infrastructure.
- **Not advertising S's or upstream prefixes to D beyond a default**: D only needs a default to reach the world; sending more would leak information without benefit. I shared only my own loopback when explicitly asked.
- **Not advertising anything S told me back to S, and not offering to forward S's prefixes to anyone as transit beyond what serves my customer**: I do not provide transit to providers or peers.
- **Privacy**: I did not disclose policies, preferences, or commercial relationships to D or S.

## 3. What I Learned About the Network

From S's update, the reachable network (so far) includes:
- 137.21.0.1/32 — S itself
- 12.84.0.1/32 — node A, upstream of S (path [S, A])
- 89.248.0.1/32 — node B, peer of S (path [S, B])
- 193.43.0.1/32 — me (C)
- 206.81.0.1/32 — D, my customer

So the topology I can infer is: D — C — S — {A (upstream of S), B (peer of S)}. S noted it prefers my path to reach D (consistent with customer-preferred routing on S's side). I have no visibility deeper than that — there may be more behind A and B.

## 4. Coordination With Other Agents

- **With S (provider)**: exchanged loopback announcements. S advertised its known prefix set (137.21.0.1, 12.84.0.1, 89.248.0.1) and confirmed it would carry my and my customer's prefixes. I accepted the small, reasonable set of prefixes (no anomalous flood) and used S as default next-hop.
- **With D (customer)**: agreed I would act as their default gateway; D told me it originates 206.81.0.1/32 with no further customers behind it. I installed and re-advertised the prefix. Later D asked for specific prefixes; I shared only my own loopback and kept the rest as default, preserving policy privacy.
- **Relay role**: I offered to relay messages on D's behalf if needed; none were requested.

Final state: end-to-end connectivity verified from my loopback to S, A (via S), B (via S), and D; advertisements consistent with provider/customer policy; no leaks of link subnets or provider-learned routes to peers/providers.