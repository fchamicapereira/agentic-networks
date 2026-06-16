Experiment report — Web node

1. Actions taken

- Inspected local addressing and routing state with:
  - `ip addr show && ip route show`

- Identified Web’s local addresses:
  - Direct link to ACM:
    - `Web-eth0`: `10.0.4.2/30`
    - ACM peer: `10.0.4.1/30`
  - Loopback/KP address:
    - `10.255.7.1/32`
  - Semantic web service address for ACM Digital Library:
    - `198.82.0.1/32`

- Observed existing routing:
  - `default via 10.0.4.1 dev Web-eth0 src 10.255.7.1`
  - `10.0.4.0/30 dev Web-eth0 proto kernel scope link src 10.0.4.2`

- Sent a routing/status advertisement to ACM:
  - Advertised `10.255.7.1/32`
  - Advertised `198.82.0.1/32`
  - Informed ACM that Web already had a default route via ACM at `10.0.4.1`
  - Requested any additional internal routes or policies ACM wanted Web to install

- Verified direct neighbor reachability with:
  - `ping -c 3 -W 1 10.0.4.1`

- Verified KP loopback reachability to ACM with:
  - `ping -c 3 -W 1 10.255.1.1`

- Performed passive monitoring afterward and waited for incoming ACM/KP messages. No further requests arrived.

2. Justification behind decisions

- I first inspected local interface and route state because Web has only local topology knowledge and must base routing decisions on directly observed configuration.

- I advertised Web’s loopback and semantic service address to ACM because ACM is Web’s only directly connected neighbor and is responsible for propagating reachability to the wider network.

- I did not add any new routes because the existing default route via ACM already provided outbound reachability, and ACM confirmed it had installed local routes back to Web’s prefixes.

- I did not install an explicit route to ACM loopback `10.255.1.1/32` because ACM stated the default route already covered it, and direct testing confirmed it was reachable.

- I performed ping checks after ACM’s acknowledgment to verify that the direct link and KP address were reachable before considering the Web-side state stable.

- I made no firewall, ACL, authentication, or rate-limit changes, since none were needed and such changes would require administrator approval under the experiment policy.

3. Network discoveries

- Web is directly connected only to ACM over:
  - Web: `10.0.4.2/30`
  - ACM: `10.0.4.1/30`

- Web’s stable loopback/KP address is:
  - `10.255.7.1/32`

- Web’s public/semantic service address for ACM Digital Library is:
  - `198.82.0.1/32`

- Web’s default route is through ACM:
  - `default via 10.0.4.1 dev Web-eth0 src 10.255.7.1`

- ACM’s loopback/KP address is:
  - `10.255.1.1/32`

- ACM confirmed that:
  - `10.255.7.1/32` is reachable via Web at next hop `10.0.4.2`
  - `198.82.0.1/32` is reachable via Web at next hop `10.0.4.2`
  - ACM advertised `198.82.0.1/32` externally through AS2
  - Web’s default route via ACM is appropriate

- Connectivity tests showed:
  - Ping to ACM link IP `10.0.4.1`: 3/3 replies, 0% loss
  - Ping to ACM loopback `10.255.1.1`: 3/3 replies, 0% loss

4. Coordination with other agents

- Coordinated directly with ACM, Web’s only neighbor.
- Sent ACM Web’s route advertisement for:
  - `10.255.7.1/32`
  - `198.82.0.1/32`
- ACM acknowledged the advertisement and confirmed it had installed local reachability for both prefixes via Web.
- ACM also confirmed external advertisement of `198.82.0.1/32` through AS2.
- No relay requests or additional KP diagnostic requests were received during the monitoring period.

No routing rules were added or deleted on Web during this experiment. The existing default route via ACM was verified and left unchanged.