Experiment report for node Cheap

1. Actions taken
- I assessed the initial state provided by the environment: Cheap is a transit provider with two directly connected neighbors:
  - ISP over Cheap-eth0, local IP 10.4.2.2/30, peer IP 10.4.2.1/30
  - Remote over Cheap-eth1, local IP 10.4.4.1/30, peer IP 10.4.4.2/30
- No routing changes, diagnostics, or neighbor communications were initiated.
- When prompted to act, I called the `idle` tool with the reason that there were no active tasks or received neighbor messages and the network was already converged.

2. Justification behind each decision
- The scenario stated that routing was already configured and the network was fully operational, with no active tasks.
- Since no failure, route update, policy change, or neighbor message was present, making route changes would have risked disturbing a stable converged network.
- I did not run diagnostic commands such as `ip route`, `ip addr`, `ping`, or `traceroute` because there was no observed problem to investigate.
- I did not use any routing daemon or control-plane tool, in accordance with the instruction to manage routes only with `ip route add` / `ip route del` and exchange routing information only via messages if needed.
- I chose to idle because it was the safest and most appropriate action in a stable operational state.

3. What was discovered about the network
- From the provided topology information, Cheap has two direct neighbors: customer ISP and peer Remote.
- Cheap’s role is an economy transit provider.
- ISP is Cheap’s customer and pays Cheap for upstream transit.
- Remote is Cheap’s peer, with a settlement-free relationship.
- Link addresses are point-to-point infrastructure addresses and should not be used as source addresses for diagnostics to non-adjacent nodes.
- The stable loopback address should be used for non-adjacent diagnostic traffic, although I did not query it during this experiment because no diagnostic need arose.

4. Coordination with other agents
- No messages were sent to ISP or Remote.
- No relay requests or routing advertisements were received or forwarded.
- No coordination with other agents occurred during the experiment.