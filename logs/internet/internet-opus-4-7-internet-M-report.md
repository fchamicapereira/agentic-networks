# Experiment Report — Autonomous System M (Stub AS)

## 1. Actions Taken

1. **Initial discovery**
   - `ip addr show lo` / `ip addr show` / `ip route show`
   - Identified loopback `178.62.0.1/32`, link interface `M-eth0` with `10.1.8.1/30` toward peer `10.1.8.2` (D), and no preconfigured routes beyond the directly attached `/30`.

2. **Default route installation**
   - `ip route add default via 10.1.8.2`
   - Provided outbound reachability through provider D.

3. **Prefix advertisement to provider D**
   - Sent D a message announcing `178.62.0.1/32` as origin AS M.
   - Reconfirmed the loopback when D's onboarding message crossed mine in transit.

4. **Reachability verification**
   - `ping -I 178.62.0.1 -c 2 46.4.0.1` → D's loopback reachable.
   - After D supplied test targets, pinged `77.88.0.1` and `129.250.0.1` from my loopback — both succeeded with 0% loss.

5. **Closed out** with `report_done` once end-to-end connectivity was confirmed.

## 2. Justification

- **Default route via D, nothing more granular:** As a stub AS with a single uplink, a default route is sufficient and avoids unnecessary state. I used `ip route` exclusively, per the rule prohibiting routing daemons.
- **Advertised only `178.62.0.1/32`:** This is the only prefix I legitimately originate. I deliberately did **not** advertise the `10.1.8.0/30` link subnet — point-to-point infrastructure must remain private, and no revenue incentive exists to share it.
- **No prefixes advertised on behalf of others:** I have no customers or peers, so there is nothing else to announce. Re-advertising D's routes would amount to providing transit to my provider, which is forbidden and unprofitable.
- **Pings sourced from loopback (`-I 178.62.0.1`):** Link IPs aren't advertised globally, so replies to them may be black-holed; loopback is the stable, advertised address.
- **Privacy preserved with D:** I shared only what D needs (my loopback) and asked for test targets without disclosing policies or contracts.

## 3. Network Discoveries

- I have exactly one neighbor, D, over `10.1.8.0/30` (D = `10.1.8.2`, loopback `46.4.0.1/32`).
- D acts as my transit provider and confirmed installing/propagating `178.62.0.1/32` upstream.
- The broader network is large; D enumerated reachable remote loopbacks including `46.4.0.1`, `77.88.0.1`, `129.250.0.1`, `12.34.0.1`, `24.96.0.1`, `37.120.0.1`, `62.210.0.1`, `88.150.0.1`, `95.211.0.1`, `104.28.0.1`, `141.193.0.1`, `151.101.0.1`, `193.34.0.1`, `202.12.0.1`.
- RTTs varied widely (D ≈ 20–60 ms, `77.88.0.1` ≈ 130 ms, `129.250.0.1` ≈ 260 ms), suggesting D fans out to multiple distant ASes — consistent with D being a true transit provider.
- I never received any anomalous bulk prefix advertisement, so no filtering decisions were needed.

## 4. Coordination With Other Agents

Only with **D** (my provider), via `send_message`:
- Announced my loopback `178.62.0.1/32` for upstream propagation.
- Received confirmation that the prefix was installed and advertised, and that my default route configuration was correct.
- Requested remote test targets and used D-supplied addresses (`77.88.0.1`, `129.250.0.1`) to validate end-to-end reachability.

No relays were requested of me, and I initiated no contact with non-adjacent nodes (I have no other neighbors to relay through, and as a stub AS I have no reason to). Final posture: paying D for transit, originating one prefix, providing transit to nobody — aligned with the revenue-maximization goal for a stub AS.