1. **What was observed:**
   - Configured loopback address and advertised prefix to TransitAS.
   - Received and installed BGP announcement from TransitAS for `44.192.100.0/24`.
   - Used `mtr` to trace paths to `44.192.100.100` and `44.192.0.100`, observing successful first hop to TransitAS.
   - Verified reachability of `45.32.0.0/24` and confirmed connectivity to `45.32.0.1`.

2. **What was decided:**
   - Configured and verified initial network settings.
   - Installed and propagated the BGP route to TinyInc.
   - Used `mtr` to verify routing paths.
   - Confirmed reachability and sent updates to TinyInc.
   - Entered idle mode for monitoring.

3. **Why:**
   - To ensure stable and globally reachable network configuration.
   - To follow route preference policies and provide customer access.
   - To confirm correct routing and address potential issues.
   - To maintain transparency and reliability in network operations.