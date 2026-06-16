Experiment report — ISP cost-optimized routing

1. Actions taken

I managed routing for `203.0.113.0/24`, the remote traffic destination used by TinyInc, by switching the route between the two upstreams:

- Expensive next hop: `10.4.1.2` on `ISP-eth1`
- Cheap next hop: `10.4.2.2` on `ISP-eth2`

The primary route commands used were:

```bash
ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2
ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1
```

At the start of the experiment, traffic was baseline traffic but was flowing via Expensive:

```bash
203.0.113.0/24 via 10.4.1.2 dev ISP-eth1
```

I immediately moved it to Cheap:

```bash
ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2
```

For short traffic spikes, I switched traffic to Expensive when the spike was active, then switched it back to Cheap after traffic returned to baseline. This was done for the spike windows around:

- Hour 42
- Hour 72
- Hour 96
- Hour 120
- Hour 144

Example command used during spikes:

```bash
ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1
```

Example command used after spikes ended:

```bash
ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2
```

I also used delayed shell jobs as safety/pre-positioning mechanisms, for example:

```bash
nohup sh -c 'sleep 43140; ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1; sleep 21600; ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2' >/tmp/isp_spike_h120_route.log 2>&1 &
```

For the long spike beginning around day 7, I initially moved traffic to Expensive:

```bash
ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1
```

After enough high-rate samples had accumulated on Expensive, I moved the remaining long-spike traffic back to Cheap:

```bash
ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2
```

At the end of the long spike, traffic was back to baseline and already on Cheap. I cleared stale delayed route-change jobs and ensured the final route remained:

```bash
ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2
```

2. Justification behind decisions

The cost strategy was based on the two upstream billing models:

- Expensive: $5/Mbps, 90th percentile, top 10% of 120 samples discarded = 12 samples discarded.
- Cheap: $1/Mbps, 95th percentile, top 5% of 120 samples discarded = 6 samples discarded.

Baseline traffic was about 100 Mbps. Spike traffic was about 500 Mbps.

For baseline traffic, Cheap was always preferred because it costs much less and is sufficient for non-spike traffic.

For short spikes, I used Expensive because TinyInc implicitly prefers higher-quality service via Expensive when feasible, and Expensive’s 90th-percentile billing allows some high samples to be discarded. Short spikes could be placed on Expensive without necessarily increasing Expensive’s billable percentile level, as long as the number of high samples stayed within the discard allowance.

For the long 120-hour spike, keeping all traffic on Expensive would have created too many 500 Mbps samples and would have caused Expensive’s 90th-percentile billable rate to rise to the spike level. Therefore I used Expensive only for part of the long spike, then moved the remaining long-spike traffic to Cheap to avoid a large Expensive bill.

When spikes ended and traffic returned to about 100 Mbps, I immediately restored the Cheap route to avoid creating unnecessary Expensive baseline samples.

3. What I discovered about the network

I did not perform topology discovery because the experiment instructions said routing was already configured and all hosts were reachable.

Operationally, I confirmed that `203.0.113.0/24` could be steered through either upstream by changing the route:

- Via Expensive:

```bash
203.0.113.0/24 via 10.4.1.2 dev ISP-eth1
```

- Via Cheap:

```bash
203.0.113.0/24 via 10.4.2.2 dev ISP-eth2
```

The network supported immediate route changes with `ip route replace`, and traffic measurements reflected the chosen upstream path.

I also confirmed that no additional routing daemon or protocol was needed; static route replacement was sufficient for the experiment.

4. Coordination with other agents

I did not coordinate with other agents during this experiment.

No routing advertisements were exchanged, no relay messages were sent, and no private contract or policy information was disclosed to neighbors. The optimization was performed locally on ISP using static route changes only.