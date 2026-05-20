# G Agent Experiment Report

## 1. Actions Taken

### Discovery & link bring-up
- Ran `ip addr show` and `ip route show` to learn local state: loopback 10.255.6.1/32; G-eth0 to E (10.0.13.2/30); G-eth1 to H (10.0.14.1/30).
- Discovered that the kernel had no connected routes for the /30 link subnets in the main table, so my first attempt at `ip route add 10.255.7.1/32 via 10.0.14.2` failed with "Nexthop has invalid gateway". I added link-scope routes to make the next-hops reachable:
  - `ip route add 10.0.13.0/30 dev G-eth0`
  - `ip route add 10.0.14.0/30 dev G-eth1`

### Routes installed
- `ip route add 10.255.7.1/32 via 10.0.14.2` — customer H's loopback.
- `ip route add default via 10.0.13.1` — default route through provider E.
- `ip route add 10.255.5.1/32 via 10.0.14.2` — customer-of-customer F.
- `ip route add 10.255.3.1/32 via 10.0.14.2` — installed (D via F as customer), removed when E flagged it as a likely leak, then re-installed once multi-homing was verified.

### Advertisements (via send_message)
- **To E (provider)** — only customer-cone prefixes: 10.255.6.1/32 (self), 10.255.7.1/32 (H), 10.255.5.1/32 (F), and ultimately 10.255.3.1/32 (D via F).
- **To H (customer)** — provider/peer-learned prefixes: 10.255.4.1 (E), 10.255.2.1 (C), 10.255.1.1 (B), 10.255.3.1 (D, as a fallback provider-path).
- Never advertised the link /30s (10.0.13.0/30, 10.0.14.0/30) to either neighbor.

### Verification
- Pinged every learned loopback sourced from `-I 10.255.6.1`. Final result: 6/6 OK (10.255.1.1, 10.255.2.1, 10.255.3.1, 10.255.4.1, 10.255.5.1, 10.255.7.1).

## 2. Justification of Decisions

- **Link-scope routes for /30s**: required to make next-hops resolvable; not advertised anywhere per the rule against announcing point-to-point subnets.
- **Default via E**: E is my provider, so a single default route covers all non-customer destinations and minimizes state.
- **Specific /32 customer routes via H**: customer routes must be preferred over provider routes (Gao-Rexford), and a /32 longest-match beats the default.
- **Advertise customer prefixes to provider; advertise provider prefixes to customer**: classic transit policy — I get paid by H for transit, so I propagate H's cone upward and propagate the upstream global table downward.
- **Did not propagate provider/peer-learned routes to E**: that would be a route leak (paying my provider to carry someone else's transit traffic).
- **Sourced all ping tests from loopback 10.255.6.1**: link IPs are private and not advertised, so replies wouldn't return reliably.
- **Initial leak rollback of 10.255.3.1/32**: when E rejected the customer-path advertisement as a likely leak (D is also reachable via E→C→B→D), I immediately withdrew the customer route locally and from my upstream advertisement. The conservative behavior — trust the provider's view when leak suspected.
- **Re-installing 10.255.3.1/32 after multi-homing was verified**: F confirmed a direct P2P link to D with bidirectional forwarding, making D a legitimate multi-homed AS (customer of both B and F). Per Gao-Rexford "prefer customer", the customer path G→H→F→D should be preferred over the provider path E→C→B→D, and the prefix should also be re-announced to the provider. Latency confirmed the customer path was shorter (115 ms vs 140 ms).
- **`report_done` after stable idle cycles**: after several `wait` cycles with no events, polling indefinitely added no value, so I closed the session.

## 3. What I Discovered About the Network

Topology (inferred from messages):

```
            C (10.255.2.1)
           / \
          E   B (10.255.1.1)
         /|   |\
        G |   | D (10.255.3.1) ── F (10.255.5.1)
        |     |                    |
        H ────┘────────────────────┘
        (10.255.7.1)
```

- My provider chain upward: G → E → C, with C also having B as a customer, and B having D in its cone.
- My customer chain downward: G → H → F → D (D multi-homed via direct P2P link to F).
- AS D is **multi-homed**: it appears in B's customer cone AND in F's customer cone simultaneously. This is the most interesting finding — it caused an apparent route leak that turned out to be a legitimate dual-homed prefix.
- Known global loopbacks: B=10.255.1.1, C=10.255.2.1, D=10.255.3.1, E=10.255.4.1, F=10.255.5.1, G=10.255.6.1, H=10.255.7.1. (A was not observed.)
- The network testbed does not pre-populate connected /30 routes; agents must add them explicitly.

## 4. Coordination With Other Agents

### With E (provider)
- Exchanged greetings and prefix lists; E acknowledged my advertisements and propagated them to C.
- E sent successive prefix updates as it learned them upstream: 10.255.4.1, 10.255.2.1, 10.255.1.1, 10.255.3.1.
- E **flagged my 10.255.3.1/32 customer-path announcement as a suspected route leak**, citing that D was already reachable via C→B. This was a valuable sanity check — exactly the kind of policy enforcement a good provider does.
- After I provided multi-homing context (verified by F via P2P link to D), E reversed and accepted the customer-path advertisement, installed 10.255.3.1/32 via me, and propagated upstream to C with AS-path [E, G, H, F, D].

### With H (customer)
- Exchanged loopback addresses; H originated 10.255.7.1/32 and forwarded F's prefix 10.255.5.1/32.
- H gave H a default via me (10.0.14.1).
- H originally advertised 10.255.3.1/32 as customer, then withdrew it when I reported E's leak concern, then re-advertised it with verified multi-homing context. H operated correctly per Gao-Rexford throughout, including not pushing back against my upstream policy decisions.
- H also helpfully reported a transient forwarding failure (ping from 10.255.7.1 to 10.255.1.1) so I could trigger E to verify upstream propagation status.

### Overall coordination pattern
The session was a clean iterative convergence: greet → exchange prefixes → install routes → verify reachability → handle a real-world policy anomaly (suspected leak / multi-homing) → re-converge → confirm. No routing daemons were used; all routing decisions were exchanged as plain messages and installed via `ip route add/del`.