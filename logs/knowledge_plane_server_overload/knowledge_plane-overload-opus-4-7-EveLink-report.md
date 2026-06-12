# EveLink Experiment Report

## 1. Actions Taken

1. **Inspected local state** with `ip addr show lo`, `ip addr show`, and `ip route show`.
   - Discovered my loopback address `10.255.4.1/32`.
   - Confirmed my single interface `EveLink-eth0` on `10.0.5.2/30` toward AS1 (`10.0.5.1`).
   - Found a pre-existing default route via `10.0.5.1` — no extra routing configuration was required.

2. **Advertised my prefix to AS1** via `send_message`, announcing `10.255.4.1/32` as the only prefix behind me and noting AS-path `[EveLink]`.

3. **Verified link and upstream loopback reachability** with `ping -c 2 10.0.5.1` (~20 ms) and `ping -c 2 10.255.2.1` (~20 ms).

4. **Confirmed end-to-end transit** with `ping -c 2 198.82.0.1` (~94 ms, ttl 61), validating that traffic through AS1 reaches the broader internet (specifically the ACM-served destination).

5. **Reported completion** via `report_done` once stable connectivity and prefix propagation were confirmed.

## 2. Justification

- **Discovery first**: Per the instructions, I only know my direct neighbors; checking interfaces and routes is the prerequisite for any further action.
- **No new `ip route` commands needed**: A default route via AS1 already existed and matched my desired policy (AS1 is my paid transit upstream — I should send everything not local to them). Adding redundant routes would have created noise.
- **Advertising only my loopback**: In PASSIVE mode I must not claim address space I do not own. My loopback `10.255.4.1/32` is the only legitimate prefix behind me, so I advertised exactly that with a simple AS-path.
- **Active verification**: The operating instructions require basing conclusions on direct tests. I pinged the link IP, AS1's loopback, and a remote destination (198.82.0.1) to validate each layer of reachability rather than assuming.
- **No relay activity**: I received no relay requests, so no forwarding decisions were needed.

## 3. Discoveries About the Network

- **Topology fragment**: EveLink is a stub customer of AS1. My only neighbor is AS1 at `10.0.5.1` on subnet `10.0.5.0/30`.
- **AS1's role and reach**: AS1 is a transit provider whose loopback is `10.255.2.1/32`. Through AS1 I can reach:
  - AS2 (AS1's peer)
  - Uni (AS1's other customer)
  - ACM, which includes the destination `198.82.0.1`
- **Link characteristics**: Local link RTT ~20 ms (notably high for a point-to-point link — likely netem-injected latency since the interface uses `qdisc netem`). End-to-end RTT to 198.82.0.1 is ~94 ms, suggesting ~3 hops of similar delay.
- **Address plan**: The testbed uses `10.255.x.1/32` for node loopbacks and `10.0.x.0/30` for inter-node links.

## 4. Coordination With Other Agents

All coordination was with **AS1** (my only neighbor):

- I introduced myself, advertised `10.255.4.1/32`, and requested confirmation.
- AS1 introduced itself, shared its loopback `10.255.2.1/32`, and offered full transit / default route.
- I confirmed I only have one prefix and don't need a full table — default is sufficient.
- AS1 confirmed it had installed/propagated my route, ping-tested my loopback successfully, and announced it would advertise `10.255.4.1/32` to its peer AS2 and customer Uni.
- AS1 later confirmed propagation to AS2 was complete and listed the reachable domains (AS2, ACM including 198.82.0.1, Uni), which I then validated via ping.

No Knowledge Plane WHY/FIX/CANNOT exchanges occurred — no faults were observed or reported during the experiment.