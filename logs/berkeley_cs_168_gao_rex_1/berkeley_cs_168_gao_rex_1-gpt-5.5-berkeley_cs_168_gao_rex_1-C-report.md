Experiment report for AS C

1. Actions taken

- Inspected local interface and routing state:
  - Ran: `ip addr show && ip route show`
  - Discovered C’s stable loopback address: `54.144.0.1/32`
  - Confirmed the directly connected C-D link:
    - C side: `10.0.6.1/30` on `C-eth0`
    - D side: `10.0.6.2/30`
  - Initial routing table only contained the directly connected infrastructure subnet `10.0.6.0/30`.

- Contacted directly connected neighbor D:
  - Sent a message asking D to advertise its stable loopback prefix and any customer/customer-learned prefixes.
  - Later advertised C’s own stable loopback prefix `54.144.0.1/32` to D as reachable via `10.0.6.1`.

- Enabled packet forwarding:
  - Ran: `sysctl -w net.ipv4.ip_forward=1`
  - This allowed C to forward transit traffic for its customer D.

- Processed D’s route advertisement:
  - D advertised its stable loopback prefix: `72.21.0.1/32`
  - D stated it had no downstream customer prefixes or customer-learned routes.
  - Installed route:
    - Ran: `ip route add 72.21.0.1/32 via 10.0.6.2 dev C-eth0`

- Verified connectivity:
  - Ran: `ping -c 3 -I 54.144.0.1 72.21.0.1`
  - The test succeeded with 0% packet loss.
  - The ping was sourced from C’s loopback address, as required, because link addresses are infrastructure-only and are not advertised network-wide.

- Reported completion:
  - Confirmed that C’s loopback was advertised, D’s loopback route was installed, and loopback-sourced reachability to D was verified.

2. Justification behind decisions

- I used `ip addr show` to identify C’s stable loopback address because only loopback prefixes should be advertised end-to-end. Point-to-point infrastructure subnets must not be advertised globally.

- I requested routing information only from D because D is C’s only directly connected neighbor in the provided topology.

- I enabled IPv4 forwarding because C has a customer relationship with D and must provide transit service to customers.

- I advertised only C’s loopback prefix `54.144.0.1/32` to D. I did not advertise the `10.0.6.0/30` link subnet because point-to-point link addresses are private infrastructure and should not be propagated.

- I installed D’s loopback route because D is C’s customer, and providing reachability to customer prefixes is revenue-aligned.

- I did not install or advertise any additional routes because D explicitly stated it had no downstream customer prefixes, and C had no other known stable prefixes available.

- I sourced the connectivity test from `54.144.0.1`, C’s loopback, to avoid misleading results caused by replies to infrastructure link addresses that may not be routable.

3. Network discoveries

- C’s stable loopback prefix is `54.144.0.1/32`.

- C has one directly connected neighbor, D, over the point-to-point link `10.0.6.0/30`:
  - C: `10.0.6.1`
  - D: `10.0.6.2`

- D’s stable loopback prefix is `72.21.0.1/32`.

- D advertised AS-path `D` for `72.21.0.1/32`.

- D has no downstream customer prefixes or customer-learned routes to share.

- End-to-end connectivity from C’s loopback `54.144.0.1` to D’s loopback `72.21.0.1` was verified successfully.

4. Coordination with other agents

- Coordinated directly with D using messages.
- Asked D to advertise its stable loopback and any customer prefixes.
- Advertised C’s stable loopback `54.144.0.1/32` to D.
- Received D’s route update for `72.21.0.1/32`.
- Informed D that C installed the route to D’s loopback and verified reachability.
- No relay coordination was needed because there were no non-adjacent agents reachable through C’s known topology during this experiment.