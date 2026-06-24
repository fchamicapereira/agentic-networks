# K Node Experiment Report

## 1. Actions Taken

1. **Initial discovery**:
   - Ran `ip addr show lo` → discovered my loopback address is `141.193.0.1/32`.
   - Ran `ip route show` → found pre-installed `/32` host routes for 14 distant destinations, all via `10.1.6.2` (C), and the connected `/30` to C on `K-eth0`.

2. **Connectivity baseline test**:
   - `ping -I 141.193.0.1 -c 2 12.34.0.1` → success (RTT ~140–300 ms). Confirmed forward + return path through C worked even before I advertised myself.

3. **Advertised loopback to provider**:
   - Sent message to C announcing `141.193.0.1/32`, asking C to install it and propagate it to peers/customers.

4. **Installed default route**:
   - `ip route add default via 10.1.6.2 dev K-eth0` — gives me a fallback for any destinations not in the specific list C had pre-populated.

5. **Confirmed and replied to C**:
   - C acknowledged installing my loopback, listed the full reachable table, and asked if I had downstream customers. I replied: no downstream prefixes, only my loopback.

6. **Verification pings** from loopback:
   - `129.250.0.1` (via customer J of C) → ~50 ms, OK.
   - `202.12.0.1` (via customer E of C) → ~96 ms, OK.

7. **Reported done.**

## 2. Justification for Each Decision

- **Sourcing pings from the loopback**: required by the rules — link `/30` IPs are private infrastructure and not advertised, so replies might not return.
- **Advertising only the loopback `/32`**: it is my stable, globally meaningful address. I never advertised the `10.1.6.0/30` point-to-point link (private infra, per rules).
- **Default route via C**: C is my provider (paid transit), so directing all unknown traffic to C is correct policy. Existing `/32` routes were already present, but a default route covers anything new.
- **No routing daemons**: managed everything via `ip route` and `send_message` as required.
- **Reporting "no customer prefixes" to C**: K has only one physical neighbor (C), no downstream — so there is nothing else to advertise upward.

## 3. Discoveries About the Network

- I am a stub/leaf AS with a single uplink to C.
- C has a rich view of the topology and provided me an effectively full table:
  - C originates `37.120.0.1/32`.
  - C reaches `12.34.0.1, 46.4.0.1, 77.88.0.1, 88.150.0.1, 151.101.0.1, 178.62.0.1` via **peer A**.
  - `24.96.0.1, 95.211.0.1, 104.28.0.1` via **peer B**.
  - `62.210.0.1, 193.34.0.1, 202.12.0.1` via **customer E**.
  - `129.250.0.1` via **customer J**.
- RTT variations (50 ms to ~300 ms) suggest the destinations sit at different topological/geographical distances behind C.
- C pre-installed specific `/32` routes toward K before I requested anything, which is unusual but useful — it means C already knew the reachable set when K came online.

## 4. Coordination With Other Agents

Only one neighbor: **C** (my provider).

- **Outbound to C**: announcement of `141.193.0.1/32`; follow-up confirming no downstream prefixes and acknowledging C as default upstream.
- **Inbound from C**: confirmation that my loopback was installed and would be propagated to peers and customers; provision of the full reachable prefix list with next-hop attribution (peer A, peer B, customer E, customer J); offer to act as default upstream.

No relays were performed in either direction during the experiment — all communication was directly with C.

## Final State

- Loopback: `141.193.0.1/32` advertised and accepted by C.
- Default route: `default via 10.1.6.2 dev K-eth0` installed.
- Specific `/32` routes to 14 destinations via C remain (pre-installed).
- End-to-end connectivity verified to multiple destinations across C's peers and customers.