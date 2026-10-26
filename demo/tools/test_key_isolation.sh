#!/bin/bash
# test_key_isolation.sh — End-to-end check that agents can't get at our model access.
#
# Runs demo/tools/check_key_leak.py in the experiment container with run_in_docker.sh, its
# proxy holding FAKE "real" keys (so the container only gets a run token), and then:
#   1. searches everything the container printed for the fake real keys: they must not appear,
#      since they never entered the container;
#   2. relies on check_key_leak.py for the rest: the harness reaches the proxy, agents don't.
# The fake keys go nowhere useful: the proxy forwards them and the providers reject them.
#
#     demo/tools/test_key_isolation.sh        # exits 0 if isolated, 1 otherwise

set -u
cd "$(dirname "$(readlink -f "$0")")/../.."

SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

# Fake keys. run_in_docker.sh hands them to the proxy it starts on this host; the test
# also catches it passing them into the container.
export ANTHROPIC_API_KEY="sk-ant-LEAKTEST-REAL-$RANDOM$RANDOM"
export OPENAI_API_KEY="sk-LEAKTEST-REAL-$RANDOM$RANDOM"
export TOGETHER_API_KEY="LEAKTEST-REAL-$RANDOM$RANDOM"

tools/run_in_docker.sh demo/tools/check_key_leak.py 2>&1 | tee "$SCRATCH/container.log"
CHECK=${PIPESTATUS[0]}

LEAKED=0
for VAR in ANTHROPIC_API_KEY OPENAI_API_KEY TOGETHER_API_KEY; do
    if grep -qF "${!VAR}" "$SCRATCH/container.log"; then
        echo "FAIL: the proxy's $VAR showed up inside the container"
        LEAKED=1
    fi
done

echo
if [ "$CHECK" -eq 0 ] && [ "$LEAKED" -eq 0 ]; then
    echo "PASS: no real key reached the container; the harness can use the proxy and agents cannot"
    exit 0
fi
echo "FAIL (container check exit $CHECK, real key leaked: $LEAKED)"
exit 1
