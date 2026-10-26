#!/bin/bash
# test_key_isolation.sh — End-to-end check that agents can't get at our model access.
#
# Starts demo/llm_proxy.py holding FAKE "real" keys, runs demo/tools/check_key_leak.py in the
# experiment container through the proxy (so the container only gets a run token), and then:
#   1. searches everything the container printed for the fake real keys: they must not appear,
#      since they never entered the container;
#   2. relies on check_key_leak.py for the rest: the harness reaches the proxy, agents don't.
# The fake keys go nowhere useful: the proxy forwards them and the providers reject them.
#
#     demo/tools/test_key_isolation.sh        # exits 0 if isolated, 1 otherwise

set -u
cd "$(dirname "$(readlink -f "$0")")/../.."

SCRATCH=$(mktemp -d)
trap 'kill "$PROXY_PID" 2>/dev/null; rm -rf "$SCRATCH"' EXIT

# Fake keys for the proxy. They are in this script's environment, so run_in_docker.sh sees
# them too: the test also catches it passing them into the container.
export ANTHROPIC_API_KEY="sk-ant-LEAKTEST-REAL-$RANDOM$RANDOM"
export OPENAI_API_KEY="sk-LEAKTEST-REAL-$RANDOM$RANDOM"
export TOGETHER_API_KEY="LEAKTEST-REAL-$RANDOM$RANDOM"
TOKEN="run-LEAKTEST-token-$RANDOM$RANDOM"
BRIDGE=$(ip -4 -o addr show docker0 | awk '{print $4}' | cut -d/ -f1)
PORT=8767

python3 demo/llm_proxy.py --listen "$BRIDGE:$PORT" --token "$TOKEN" > "$SCRATCH/proxy.log" 2>&1 &
PROXY_PID=$!
sleep 1
if ! kill -0 "$PROXY_PID" 2>/dev/null; then
    echo "The proxy did not start:"; cat "$SCRATCH/proxy.log"; exit 1
fi

tools/run_in_docker.sh --llm-proxy "http://$BRIDGE:$PORT" --llm-proxy-token "$TOKEN" \
    demo/tools/check_key_leak.py 2>&1 | tee "$SCRATCH/container.log"
CHECK=${PIPESTATUS[0]}

echo
echo "Proxy log:"
sed 's/^/  /' "$SCRATCH/proxy.log"

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
