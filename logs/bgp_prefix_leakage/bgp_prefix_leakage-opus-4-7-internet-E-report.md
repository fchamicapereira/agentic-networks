# E (Regional Transit AS) — Experiment Report

## 1. Actions Taken

**Discovery**
- Ran `ip addr show lo` → loopback 62.210.0.1/32.
- Ran `ip addr show` and `ip route show` to enumerate four point-to-point links (E-eth0..3 to C, D, N, O) and a pre-populated route table containing /32s from C (12 prefixes), N (193.34.0.1), and O (202.12.0.1).

**Initial outreach**
- Sent BGP-style HELLO/UPDATE messages to all four neighbors:
  - To C (provider): advertised 62.210.0.1/32 + customers 193.34.0.1/32, 202.12.0.1/32.
  - To D (peer): proposed settlement-free peering, same three prefixes.
  - To N, O (customers): announced my loopback + the other customer + the full upstream set, asking for their prefixes in return.

**Handling D's bogus update**
- D sent an UPDATE claiming `AS_PATH=[D]` for 15 prefixes including my own loopback, both my customers' loopbacks, and all C's upstream prefixes. I rejected the entire update and asked for a clean one.
- D resent the same update verbatim ("refresh"). Rejected again, with explicit pointers to the bad attributions.
- Verified via two pings (one via C's default route, one with a temporary route forced via D):
  - via C: 270 ms
  - via D directly: 150 ms
  This is consistent with D having *some* path but does not prove origin — I noted it without using it as policy input.
- D finally sent a clean update: `46.4.0.1 [D]`, `151.101.0.1 [D L]`, `178.62.0.1 [D M]`. Accepted.

**Route installation**
- `ip route del 46.4.0.1 && ip route add 46.4.0.1 via 10.0.7.1 dev E-eth1` (and the same for 151.101.0.1, 178.62.0.1) — switched these three from provider C to peer D.

**Final advertisements**
- Sent path-change UPDATEs to N and O reflecting the new shorter `[E, D ...]` paths for D's prefixes.
- Did NOT readvertise D's prefixes to C, nor C's prefixes to D (peer/provider non-transit).

**Verification**
- Pinged 193.34.0.1, 202.12.0.1, 37.120.0.1, 12.34.0.1, 46.4.0.1, 129.250.0.1, 151.101.0.1, 178.62.0.1 from `-I 62.210.0.1` — all succeeded.

## 2. Justifications

- **Why advertise only loopbacks + customer prefixes upward (to C and D)**: I am paid by N and O to provide transit; I pay C and exchange freely with D. Carrying C's prefixes to D, or D's prefixes to C, would mean providing free transit to a non-customer — explicitly forbidden and unprofitable.
- **Why advertise full table down (to N and O)**: They are paying customers; goal is global reachability for them.
- **Why prefer D over C for 46.4/151.101/178.62**: Peer routes cost nothing; provider routes cost money. Standard local-preference policy: customer > peer > provider. Switching saved transit cost while keeping policy-compliant.
- **Why reject D's bulk update**: It claimed origin D on prefixes D demonstrably does not originate (including my own loopback). This is either a route leak or hijack attempt; installing it would have black-holed my own and my customers' addresses, and would have made me complicit in propagating false origins. The instruction "treat large unexpected advertisements as anomalous and investigate" applied exactly.
- **Why not use reachability tests as policy input**: Per the rules, route preference is by policy, not reachability. The 150 ms vs 270 ms difference was diagnostic, not authoritative — I only acted on D's *clean* re-advertisement.
- **Why never advertise the /30 link subnets**: Per rules, those are private infrastructure.

## 3. Discoveries About the Network

- I have two customers (N, O — single /32 each, both stubs), one provider (C), one peer (D).
- C has at least two peers (A, B) and two customers (J, K). C reports reachability to 12 external /32s.
- D claims to originate 46.4.0.1/32 and have customers L (151.101.0.1/32) and M (178.62.0.1/32). C also reports reachability to those same three prefixes "via A" — possible interpretations include D being multi-homed (D↔A as well as D↔E), or A re-advertising D's prefixes; I did not try to infer further per the privacy rules.
- D had a misconfigured export filter that initially leaked everything as origin-D. Operationally serious; I flagged it explicitly so D could fix it.
- N is a customer that defaults to me; O is a stub also defaulting to me. Both confirmed via messages.

## 4. Coordination with Other Agents

- **C (provider)**: Exchanged a single round of advertisements. C ack'd carrying my prefixes upstream and sent me its full reachable table.
- **D (peer)**: Three rounds. Initial proposal → D sent bogus bulk update → I rejected → D resent the same → I rejected again with detail → D apologized and sent a clean, properly-AS-PATH'd update covering only its own and its customers' prefixes → I accepted, installed routes, and acknowledged.
- **N (customer)**: Two messages — initial offer/request and a follow-up path-change UPDATE after the peer route went live.
- **O (customer)**: Same pattern as N. O confirmed it is a stub with no customers and installed a default toward me.

Final state: stable, policy-compliant, all customers globally reachable, peer route preferences in place, no improper transit anywhere.