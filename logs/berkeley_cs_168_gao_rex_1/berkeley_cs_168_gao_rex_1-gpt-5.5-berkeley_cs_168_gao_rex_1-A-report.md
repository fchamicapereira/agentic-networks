Experiment Report — Autonomous System A

1. Actions taken

- Discovered local interface and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Found A’s stable loopback address:
    - `23.20.0.1/32` on `lo`
  - Confirmed point-to-point links:
    - `A-eth0`: `10.0.1.1/30`, connected to S at `10.0.1.2`
    - `A-eth1`: `10.0.4.1/30`, connected to D at `10.0.4.2`

- Advertised A’s loopback prefix to directly connected customers:
  - Sent route update to S advertising:
    - `23.20.0.1/32`, reachable via A on the S-A link
  - Sent route update to D advertising:
    - `23.20.0.1/32`, reachable via A on the D-A link
  - Requested that both neighbors advertise only stable loopback prefixes and customer loopback prefixes, not point-to-point infrastructure subnets.

- Received customer route advertisements:
  - From S:
    - `99.12.0.1/32`, AS-path `S`, next-hop `10.0.1.2`
    - S reported no customer prefixes.
  - From D:
    - `72.21.0.1/32`, AS-path `D`
    - D reported no customer prefixes.

- Installed routes to customer loopbacks:
  - Ran:
    - `ip route add 72.21.0.1/32 via 10.0.4.2 dev A-eth1 || true`
    - `ip route add 99.12.0.1/32 via 10.0.1.2 dev A-eth0 || true`
    - `ip route show`
  - Resulting relevant routes:
    - `72.21.0.1 via 10.0.4.2 dev A-eth1`
    - `99.12.0.1 via 10.0.1.2 dev A-eth0`

- Enabled IPv4 forwarding:
  - Ran:
    - `sysctl -w net.ipv4.ip_forward=1`
  - This allowed A to forward customer traffic between S and D.

- Exported customer reachability to other customers:
  - To S, advertised:
    - `23.20.0.1/32`, AS-path `A`, next-hop `10.0.1.1`
    - `72.21.0.1/32`, AS-path `A D`, next-hop `10.0.1.1`
  - To D, advertised:
    - `23.20.0.1/32`, AS-path `A`, next-hop `10.0.4.1`
    - `99.12.0.1/32`, AS-path `A S`, next-hop `10.0.4.1`

- Verified local reachability using A’s loopback as the source:
  - Ran:
    - `ping -c 3 -I 23.20.0.1 99.12.0.1`
    - `ping -c 3 -I 23.20.0.1 72.21.0.1`
  - Both tests succeeded with 0% packet loss.

- Requested end-to-end customer verification:
  - Asked S to ping `72.21.0.1` sourced from `99.12.0.1`.
  - Asked D to ping `99.12.0.1` sourced from `72.21.0.1`.

- Received successful verification:
  - S confirmed ping from `99.12.0.1` to `72.21.0.1` succeeded.
  - D confirmed route to `99.12.0.1/32` via `10.0.4.1` was installed and ping from `72.21.0.1` to `99.12.0.1` succeeded with 0% loss.


2. Justification behind decisions

- I first inspected local addressing and routes to identify A’s stable loopback prefix and avoid relying on point-to-point infrastructure addresses for global reachability.

- I advertised only A’s loopback prefix, `23.20.0.1/32`, because loopbacks are the stable node addresses intended for end-to-end routing. I did not advertise the `10.0.1.0/30` or `10.0.4.0/30` point-to-point subnets because those are private infrastructure links and should not be propagated network-wide.

- I accepted S and D’s advertised prefixes because both are directly connected customers, each advertised a single stable loopback prefix, and the updates were consistent with their expected role and size. There was no anomalous large prefix dump.

- I installed routes using only `ip route add`, as required. I did not use any dynamic routing daemon.

- I enabled IPv4 forwarding because A must provide transit service for customers, and S and D both depend on A for connectivity.

- I exported S’s loopback to D and D’s loopback to S because both S and D are A’s customers. Providing transit between customers is allowed and revenue-positive.

- I used loopback-sourced pings for diagnostics, specifically `-I 23.20.0.1`, because remote nodes are expected to route back to loopback addresses, not point-to-point link addresses.

- I coordinated with both customers for end-to-end verification instead of assuming success from local pings alone.


3. Network discoveries

- A has stable loopback:
  - `23.20.0.1/32`

- A’s directly connected neighbors are:
  - S over `A-eth0`
    - A side: `10.0.1.1/30`
    - S side: `10.0.1.2/30`
  - D over `A-eth1`
    - A side: `10.0.4.1/30`
    - D side: `10.0.4.2/30`

- S’s stable loopback is:
  - `99.12.0.1/32`
  - Reachable via `10.0.1.2` on `A-eth0`
  - S has no customer prefixes.

- D’s stable loopback is:
  - `72.21.0.1/32`
  - Reachable via `10.0.4.2` on `A-eth1`
  - D has no customer prefixes.

- End-to-end customer connectivity through A works:
  - A can reach both customer loopbacks from source `23.20.0.1`.
  - S can reach D’s loopback through A.
  - D can reach S’s loopback through A.


4. Coordination with other agents

- Coordinated directly with S:
  - Advertised A’s loopback.
  - Requested S’s loopback/customer routes.
  - Received S’s route advertisement for `99.12.0.1/32`.
  - Exported D’s loopback reachability to S.
  - Requested S verify connectivity to D.
  - S confirmed successful ping to `72.21.0.1` sourced from `99.12.0.1`.

- Coordinated directly with D:
  - Advertised A’s loopback.
  - Requested D’s loopback/customer routes.
  - Received D’s route advertisement for `72.21.0.1/32`.
  - Exported S’s loopback reachability to D.
  - Requested D verify connectivity to S.
  - D confirmed route installation and successful ping to `99.12.0.1` sourced from `72.21.0.1`.

- No relay communication was needed because all relevant agents in this experiment were directly connected to A.

Final state: A successfully provides transit between its two customers, S and D, using only stable loopback prefixes and policy-compliant route exports.