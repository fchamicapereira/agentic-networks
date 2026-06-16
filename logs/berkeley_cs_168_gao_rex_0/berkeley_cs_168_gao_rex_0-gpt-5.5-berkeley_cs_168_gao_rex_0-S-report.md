Experiment report for AS S

1. Actions taken

- Inspected local addressing and routing state:
  - Ran `ip addr show lo`, `ip addr show`, and `ip route show`.
  - Discovered S’s stable loopback address: `10.255.5.1/32`.
  - Confirmed directly connected interfaces:
    - `S-eth0` to A: local `10.0.1.2/30`, peer `10.0.1.1`
    - `S-eth1` to B: local `10.0.2.1/30`, peer `10.0.2.2`
    - `S-eth2` to C: local `10.0.3.1/30`, peer `10.0.3.2`

- Added direct connected link routes:
  - `ip route add 10.0.1.0/30 dev S-eth0`
  - `ip route add 10.0.2.0/30 dev S-eth1`
  - `ip route add 10.0.3.0/30 dev S-eth2`

- Advertised S’s loopback prefix to directly connected neighbors:
  - Sent `10.255.5.1/32` to A, B, and C.
  - Did not advertise point-to-point infrastructure subnets.

- Installed loopback routes learned from neighbors:
  - From A:
    - Installed `10.255.1.1/32` via `10.0.1.1` on `S-eth0`:
      - `ip route add 10.255.1.1/32 via 10.0.1.1 dev S-eth0`
  - From B:
    - Installed `10.255.2.1/32` via `10.0.2.2` on `S-eth1`:
      - `ip route add 10.255.2.1/32 via 10.0.2.2 dev S-eth1`
  - From C:
    - Installed `10.255.3.1/32` via `10.0.3.2` on `S-eth2`:
      - `ip route add 10.255.3.1/32 via 10.0.3.2 dev S-eth2`
    - Installed `10.255.4.1/32` via `10.0.3.2` on `S-eth2`:
      - `ip route add 10.255.4.1/32 via 10.0.3.2 dev S-eth2`

- Exported routes according to policy:
  - To A and B, advertised only S’s own loopback and customer/customer-reachable prefixes:
    - `10.255.5.1/32`
    - `10.255.3.1/32`
    - `10.255.4.1/32`
  - To C, advertised all known reachable loopback prefixes:
    - `10.255.5.1/32`
    - `10.255.1.1/32`
    - `10.255.2.1/32`

- Handled duplicate advertisements for `10.255.4.1/32`:
  - B later advertised `10.255.4.1/32` as customer-reachable via B.
  - A later advertised `10.255.4.1/32` as customer-reachable via A.
  - I kept the existing route to `10.255.4.1/32` via C because C is S’s customer, and customer routes are preferred for revenue and policy reasons.

- Verified connectivity using loopback-sourced pings:
  - Ran:
    - `ping -I 10.255.5.1 -c 2 -W 1 10.255.1.1`
    - `ping -I 10.255.5.1 -c 2 -W 1 10.255.2.1`
    - `ping -I 10.255.5.1 -c 2 -W 1 10.255.3.1`
    - `ping -I 10.255.5.1 -c 2 -W 1 10.255.4.1`
  - All known loopback destinations responded with 0% packet loss.

2. Justification behind decisions

- I used only `ip route add` for route management, as required.
- I did not use any routing daemon.
- I advertised only loopback prefixes, never point-to-point link subnets, because link subnets are private infrastructure.
- I exported customer-learned prefixes to both A and B because inbound traffic to S’s customer cone benefits S.
- I did not export peer-learned or provider-learned routes to other non-customer neighbors, because S must not provide transit service for peers or providers.
- I advertised all known reachable loopbacks to C because C is S’s customer, and S provides transit service to customers.
- I preferred the route to `10.255.4.1/32` via C over alternate advertisements from A or B because C is a customer. This maximizes revenue and follows policy-based routing preference rather than reachability-based routing.
- I treated B’s and A’s later advertisements of `10.255.4.1/32` as alternate paths but did not replace the customer route through C.

3. Network discoveries

- S’s own loopback prefix is `10.255.5.1/32`.
- Direct neighbors:
  - A is reachable over `S-eth0`, peer IP `10.0.1.1`.
  - B is reachable over `S-eth1`, peer IP `10.0.2.2`.
  - C is reachable over `S-eth2`, peer IP `10.0.3.2`.
- Learned loopback prefixes:
  - A originates `10.255.1.1/32`.
  - B originates `10.255.2.1/32`.
  - C originates `10.255.3.1/32`.
  - `10.255.4.1/32` is reachable through C and was also later advertised by B and A.
- Final routing state on S:
  - `10.255.1.1/32` via A at `10.0.1.1`
  - `10.255.2.1/32` via B at `10.0.2.2`
  - `10.255.3.1/32` via C at `10.0.3.2`
  - `10.255.4.1/32` via C at `10.0.3.2`
- End-to-end loopback connectivity from S to all known loopbacks was confirmed.

4. Coordination with other agents

- With A:
  - Received A’s originating loopback `10.255.1.1/32`.
  - Advertised S’s loopback `10.255.5.1/32`.
  - Later advertised customer-reachable prefixes `10.255.3.1/32` and `10.255.4.1/32`.
  - A later advertised `10.255.4.1/32`, which I acknowledged but did not select over the customer route.

- With B:
  - Received B’s originating loopback `10.255.2.1/32`.
  - Advertised S’s loopback `10.255.5.1/32`.
  - Later advertised customer-reachable prefixes `10.255.3.1/32` and `10.255.4.1/32`.
  - B later advertised `10.255.4.1/32`, which I acknowledged but did not install because the customer route via C was already preferred.

- With C:
  - Advertised S’s loopback and all known reachable loopbacks from A and B.
  - Received C’s originating prefix `10.255.3.1/32` and customer-reachable prefix `10.255.4.1/32`.
  - Installed both via C and exported them to A and B as customer-reachable routes.