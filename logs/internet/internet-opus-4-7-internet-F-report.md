# Experiment Report: AS F (Stub AS)

## 1. Actions Taken

**Initial reconnaissance:**
- Ran `ip addr show` and `ip route show` to inventory my interfaces and routing state.
- Discovered loopback 10.255.6.1/32, one physical interface F-eth0 with 10.1.1.1/30 toward A (peer .2), and an empty routing table.

**Routing configuration:**
- Attempted `ip route add default via 10.1.1.2` — failed ("invalid gateway") because 10.1.1.2 was not yet a known on-link host (the /30 mask on the interface was apparently not creating a usable connected route in this environment).
- Fixed by adding an explicit on-link entry first: `ip route add 10.1.1.2/32 dev F-eth0`.
- Then installed `ip route add default via 10.1.1.2` successfully.
- Final routing table:
  - `default via 10.1.1.2 dev F-eth0`
  - `10.1.1.2 dev F-eth0 scope link`

**Coordination:**
- Sent A a message announcing my loopback 10.255.6.1/32 for global advertisement, noting I have no customer prefixes.
- Did NOT share the link subnet 10.1.1.0/30 for advertisement (private infrastructure per policy).

**Verification:**
- Sourced pings from my loopback: `ping -I 10.255.6.1 -c 3 10.255.1.1`.
- First attempts failed (A had not yet installed its return route).
- After A confirmed, pings succeeded with 0% loss (~20 ms RTT).

## 2. Justification of Decisions

- **Default route via A only:** As a stub AS with a single provider, A is by policy my sole gateway to the rest of the internet. No alternative paths exist, so a static default is sufficient and simple.
- **Advertise only my loopback:** I have no customers and no peers. The only prefix I have a revenue incentive to expose is my own loopback (so others can reach me via A, whom I pay for transit). The /30 point-to-point link is private infrastructure and must not be leaked.
- **No transit offered:** As a stub with no customers, I never accept or forward traffic between other ASes. This is structural — I only have one neighbor — but also enforced by not advertising anything other than my own loopback.
- **Sourcing pings from loopback:** Link interface addresses are not globally advertised; replies could be dropped or returned via unexpected paths. Loopback is the stable, advertised identity.
- **Patience on initial ping failure:** Per policy, transient unreachability on the preferred (and only) path does not justify abandoning it. I retried and confirmed reachability once A's side converged.

## 3. Network Discoveries

- I am a leaf node: a single physical link to A, and A is my upstream transit provider.
- A's loopback is 10.255.1.1/32, reachable via the default route.
- Link subnet to A is 10.1.1.0/30. RTT to A's loopback is ~20 ms.
- I have no visibility into the wider topology beyond A; any global reachability is delegated to A's advertisements on my behalf.
- The environment required an explicit on-link host route for the gateway before a default could be installed — a quirk worth noting for future configurations.

## 4. Coordination With Other Agents

Only one peer, A (my provider):
- A initiated by introducing itself (10.255.1.1) and requesting my loopback plus any customer prefixes.
- I replied with my loopback 10.255.6.1/32 and stated I have no customers.
- A confirmed it would advertise 10.255.6.1/32 globally and offered itself as my default.
- I did not disclose policies, preferences, or contract details beyond what was operationally necessary (loopback prefix) — consistent with the privacy norm.
- Reachability to A's loopback was verified end-to-end after A installed its return route.

Final state: stub AS F is fully configured with a default route to provider A, loopback announced through A, and verified reachability to A.