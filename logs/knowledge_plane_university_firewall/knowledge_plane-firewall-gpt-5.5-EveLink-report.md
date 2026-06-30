Experiment Report — EveLink

1. Actions Taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Discovered EveLink’s stable loopback address:
    - `91.214.0.1/32`
  - Confirmed directly connected interface:
    - `EveLink-eth0` up with `10.0.5.2/30`
    - Peer AS1 at `10.0.5.1/30`
  - Existing default route:
    - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Contacted upstream neighbor AS1:
  - Sent AS1 a routing information request asking for its stable loopback prefix and reachable customer/peer prefixes with AS-path information.
  - Advertised EveLink’s own stable loopback prefix:
    - `91.214.0.1/32`
    - Next hop toward EveLink: `10.0.5.2`
  - Informed AS1 that EveLink had no downstream customer prefixes to advertise.

- Installed routes learned from AS1:
  - Initially installed:
    - `ip route add 4.2.2.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 128.173.0.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
  - Later installed additional AS1-advertised reachable prefixes:
    - `ip route add 128.173.10.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 154.54.1.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 198.82.0.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 198.82.0.254/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Verified routing table after installation:
  - Ran `ip route show`
  - Confirmed the resulting routing table included:
    - Default route via AS1
    - AS1 loopback `4.2.2.1/32`
    - Uni loopback `128.173.0.1/32`
    - User loopback `128.173.10.1/32`
    - AS2 loopback `154.54.1.1/32`
    - ACM addresses `198.82.0.1/32` and `198.82.0.254/32`

- Verified end-to-end connectivity using EveLink’s loopback as source:
  - Ran:
    - `ping -c 3 -I 91.214.0.1 4.2.2.1`
    - `ping -c 3 -I 91.214.0.1 128.173.0.1`
    - `ping -c 3 -I 91.214.0.1 128.173.10.1`
    - `ping -c 3 -I 91.214.0.1 154.54.1.1`
    - `ping -c 3 -I 91.214.0.1 198.82.0.1`
    - `ping -c 3 -I 91.214.0.1 198.82.0.254`
  - All pings succeeded with 0% packet loss.

2. Justification Behind Decisions

- I first inspected local state before making changes because Knowledge Plane guidance requires local diagnosis before escalation or configuration.
- I used the loopback address `91.214.0.1/32` as EveLink’s stable advertised address because the experiment instructions state that only the loopback address should be advertised network-wide.
- I did not advertise point-to-point infrastructure address `10.0.5.2/30`, because those addresses are link-scoped and remote nodes generally cannot route back to them.
- I requested routing information from AS1 because AS1 is EveLink’s only directly connected neighbor and upstream transit provider.
- I installed learned routes via AS1 at next hop `10.0.5.1` because AS1 explicitly advertised reachability for those prefixes and EveLink’s business relationship is customer-to-provider transit.
- I included `src 91.214.0.1` on installed routes to ensure diagnostic and routed traffic uses EveLink’s globally reachable loopback address rather than the link-local infrastructure address.
- I accepted AS1’s advertised prefixes because the update volume was small and consistent with AS1’s expected role as an upstream provider carrying its own, customer, peer, and downstream routes.
- I verified all changes with ping tests sourced from `91.214.0.1` to confirm that connectivity worked end to end and replies could route back correctly.

3. Network Discoveries

- EveLink:
  - Stable loopback: `91.214.0.1/32`
  - Direct neighbor: AS1 over `EveLink-eth0`
  - Local link address: `10.0.5.2/30`
  - AS1 peer address: `10.0.5.1/30`
  - Default transit provider: AS1

- AS1:
  - Stable loopback: `4.2.2.1/32`
  - Provides upstream/default transit to EveLink
  - Uses peer AS2 as its current default exit via `10.0.2.2`
  - Has customer/downstream route to Uni

- Uni:
  - Loopback: `128.173.0.1/32`
  - Reachable via AS1
  - AS-path: `AS1 Uni`

- User:
  - Loopback: `128.173.10.1/32`
  - Reachable via AS1 through Uni
  - AS-path: `AS1 Uni User`

- AS2:
  - Loopback: `154.54.1.1/32`
  - Reachable via AS1

- ACM:
  - Addresses:
    - `198.82.0.1/32`
    - `198.82.0.254/32`
  - Reachable via AS1

- Connectivity from EveLink’s stable loopback to all known advertised remote loopbacks was confirmed successfully.

4. Coordination With Other Agents

- Coordinated only with directly connected neighbor AS1.
- Sent AS1 a request for its stable loopback and reachable prefixes.
- Advertised EveLink’s own legitimate prefix `91.214.0.1/32` to AS1.
- Confirmed to AS1 that EveLink had no downstream customer prefixes.
- Received AS1’s route advertisements and installed the advertised prefixes locally.
- No relay requests were received, and no communication with non-adjacent agents was needed.