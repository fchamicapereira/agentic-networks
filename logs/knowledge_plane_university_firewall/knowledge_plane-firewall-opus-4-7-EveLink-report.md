# EveLink Experiment Report

## 1. Actions Taken

1. **Inspected local state** with `ip addr show` and `ip route show`.
   - Found my loopback address: `10.255.4.1/32`.
   - Found one physical interface `EveLink-eth0` with IP `10.0.5.2/30`, peer `10.0.5.1` (AS1).
   - Found a pre-installed default route: `default via 10.0.5.1 dev EveLink-eth0`.

2. **Sent a routing announcement to AS1** via `send_message`, advertising my loopback `10.255.4.1/32` reachable through `10.0.5.2`, and confirming I would use AS1 as my default upstream.

3. **Received acknowledgement from AS1**, which installed a route to `10.255.4.1/32` and provided its own loopback (`10.255.2.1/32`) as a reachability test target.

4. **Verified connectivity** with `ping -c 3 10.255.2.1` — 3/3 replies, ~24 ms RTT, 0% loss.

5. **Reported done** via `report_done`.

## 2. Justification

- **Why advertise only the loopback (`10.255.4.1/32`)?** It is the only address space I legitimately own according to my role. In PASSIVE mode I was explicitly instructed not to claim any other address space. Announcing the loopback ensures end-to-end reachability to me from the rest of the network.
- **Why keep the default route via AS1?** AS1 is my paid upstream transit provider. A single default route is the standard and cheapest configuration for a customer of a transit ISP — there is no need to install specific prefixes when AS1 supplies full transit.
- **Why no `ip route add/del` commands of my own?** The pre-installed default already pointed at AS1 correctly, and I have no other neighbors whose prefixes would require explicit routes. Adding anything else would be redundant or incorrect.
- **Why ping AS1's loopback?** To directly verify the symptom (reachability) rather than assume the control-plane exchange implied a working data plane — consistent with the KP principle of basing conclusions on observed evidence.

## 3. Network Discoveries

- I am a stub/edge ISP with exactly one upstream link to AS1 over `10.0.5.0/30`.
- AS1's loopback is `10.255.2.1/32`, reachable via `10.0.5.1` with ~24 ms RTT (a `netem` qdisc is present on the link, suggesting deliberately injected latency).
- I have no visibility of the wider topology beyond AS1; any further destinations would be reached via AS1's default transit.
- No KP `WHY`/`FIX` queries arrived during the experiment, and no relay requests had to be forwarded.

## 4. Coordination With Other Agents

- **AS1 (upstream):** Single bilateral exchange. I announced `10.255.4.1/32`; AS1 acknowledged installation of the corresponding route and advertised its own loopback `10.255.2.1/32` for testing. This established a working bidirectional control- and data-plane relationship.
- **No other agents** were contacted directly (none are physically adjacent), and no relay requests were received, so no third-party coordination took place.

## Final State

- Mode: PASSIVE (no spurious prefix claims).
- Advertised: `10.255.4.1/32` to AS1.
- Routes: `default via 10.0.5.1 dev EveLink-eth0`; `10.0.5.0/30` connected.
- Verified reachability: EveLink ↔ AS1 loopbacks, 0% loss.