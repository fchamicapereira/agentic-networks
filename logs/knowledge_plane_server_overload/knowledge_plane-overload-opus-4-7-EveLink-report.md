# EveLink Experiment Report

## 1. Actions Taken

**Initial inspection:**
- Ran `ip addr show lo` → discovered my stable loopback address: `91.214.0.1/32`.
- Ran `ip route show` → found a pre-installed default route `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1` and the connected `/30` for my link to AS1.

**Neighbor coordination:**
- Sent a message to AS1 advertising my loopback prefix `91.214.0.1/32`, asking AS1 to route return traffic toward `10.0.5.2`.
- AS1 confirmed installation of the prefix and listed the destinations reachable through it.

**Connectivity verification (sourced from loopback):**
- `ping -c 2 -I 91.214.0.1 4.2.2.1` → 0% loss, ~20 ms (AS1 loopback).
- `ping -c 2 -I 91.214.0.1 128.173.0.1` → 0% loss, ~40 ms (Uni).
- `ping -c 2 -I 91.214.0.1 198.82.0.1` → 0% loss, ~94 ms (ACM web server via AS2).

**Subsequent events:**
- Received an informational update from AS1 that Uni's aggregate `128.173.0.0/16` is reachable via AS1. Took no action because my existing default route already covers it.
- No KP `WHY` queries or relay requests arrived during the experiment.

## 2. Justification of Decisions

- **Used loopback as my stable identity.** The brief explicitly states only the loopback is routable from remote nodes; link-local `/30` addresses are not advertised. Advertising it to AS1 and sourcing all diagnostic traffic from it ensured replies would actually come back.
- **Kept the default route as-is.** AS1 is my paid upstream transit and offered a single default-route model. Installing more specific prefixes would be redundant and add unnecessary state. The advice in the brief about being skeptical of large prefix dumps reinforced minimalism.
- **Did not install `128.173.0.0/16` separately.** AS1's update was explicitly informational ("no action needed if your default is installed"). The default already covers it, so adding it would be churn without benefit.
- **No autonomous changes to security/ACLs or unusual prefixes.** Operating in PASSIVE mode, I made no claims to address space I don't own and didn't touch any policy that would require admin approval.
- **Verified before reporting success.** Per the guidance to confirm rather than hypothesize, I pinged all three offered destinations end-to-end before declaring connectivity healthy.

## 3. Discoveries About the Network

- My node sits behind a single upstream, AS1, on link `10.0.5.0/30` (me `.2`, AS1 `.1`).
- AS1 provides full Internet transit and reaches at least:
  - `4.2.2.1/32` — AS1's own loopback / DNS recursor.
  - `128.173.0.0/16` (incl. `128.173.0.1/32`) — Uni's campus.
  - `198.82.0.0/24` (incl. `198.82.0.1`) — ACM, reached via AS2.
  - `154.54.1.1/32` — AS2's loopback.
- Approximate latencies suggest topology depth: ~20 ms to AS1, ~40 ms to Uni (one hop beyond), ~94 ms to ACM (via AS2 — two transit hops away).
- TTL values in ping replies (`64`, `63`, `61`) are consistent with that depth.

## 4. Coordination With Other Agents

- **AS1 (upstream ISP):** Direct neighbor messaging only.
  - Outbound: advertised `91.214.0.1/32` with a request to install a route toward `10.0.5.2`.
  - Inbound: confirmation of route installation, list of reachable destinations, and a later informational update about `128.173.0.0/16`.
- **No other agents contacted me**, and I had no need to ask AS1 to relay messages to non-adjacent agents during this experiment.

Final state: PASSIVE mode, stable, default route via AS1 verified working end-to-end from loopback to AS1, Uni, and ACM/AS2 destinations.