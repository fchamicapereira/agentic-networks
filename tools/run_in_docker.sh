#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")
IMAGE_NAME="agentic-networks"

usage() {
    echo "Usage: $0 <script.py> [args...]"
    echo "  Builds the Docker image and runs the given Python script inside it. The models are"
    echo "  reached through tools/llm_proxy.py, started for the run and stopped after it, so the"
    echo "  container gets only the proxy's address and a run token, never the real keys."
    exit 1
}

if [ $# -lt 1 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
fi

PYTHON_SCRIPT="$1"
shift
SCRIPT_ARGS="$@"

# Resolve absolute path of the script
PYTHON_SCRIPT_ABS=$(readlink -f "$PYTHON_SCRIPT")
if [ ! -f "$PYTHON_SCRIPT_ABS" ]; then
    echo "Error: script not found: $PYTHON_SCRIPT_ABS"
    exit 1
fi
PYTHON_SCRIPT_REL="${PYTHON_SCRIPT_ABS#"$PROJECT_ROOT/"}"

echo "Building image '$IMAGE_NAME'..."
docker build -t "$IMAGE_NAME" \
    --build-arg UID="$(id -u)" \
    --build-arg GID="$(id -g)" \
    "$PROJECT_ROOT"

echo "Running: $PYTHON_SCRIPT_REL $SCRIPT_ARGS"

# Collect GPU device flags if NVIDIA devices are present
GPU_ARGS=()
if ls /dev/nvidia[0-9]* 2>/dev/null | grep -q .; then
    GPU_ARGS+=(--gpus all)
    for dev in /dev/nvidia[0-9]* /dev/nvidiactl /dev/nvidia-uvm /dev/nvidia-modeset; do
        [ -e "$dev" ] && GPU_ARGS+=(--device "$dev:$dev")
    done
fi

# Model access. Every run gets its own tools/llm_proxy.py, holding the real keys on this host,
# and the container gets only its address and a throwaway run token: the keys never enter it,
# so an agent's commands can't read them.
BRIDGE=$(ip -4 -o addr show docker0 | awk '{print $4}' | cut -d/ -f1)
LLM_PROXY_TOKEN="run-$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
PROXY_LOG=$(mktemp)
# Port 0: any free port, so runs side by side each get their own proxy.
python3 "$SCRIPT_DIR/llm_proxy.py" --listen "$BRIDGE:0" --token "$LLM_PROXY_TOKEN" > "$PROXY_LOG" 2>&1 &
PROXY_PID=$!
# However the run ends, stop the proxy and report what went through it.
proxy_done() {
    local status=$?  # the run's, which the script must still exit with
    kill "$PROXY_PID" 2>/dev/null || true
    wait "$PROXY_PID" 2>/dev/null || true
    TOTALS=$(grep -o 'total [0-9]* calls, [0-9]* in / [0-9]* out' "$PROXY_LOG" | tail -n 1 || true)
    echo "LLM proxy stopped: ${TOTALS:-no model calls} (tokens)"
    rm -f "$PROXY_LOG"
    exit "$status"
}
trap proxy_done EXIT
for _ in $(seq 50); do
    LLM_PROXY=$(sed -n 's/^LLM proxy on \([^ ]*\).*/\1/p' "$PROXY_LOG")
    [ -n "$LLM_PROXY" ] && break
    kill -0 "$PROXY_PID" 2>/dev/null || break
    sleep 0.1
done
if [ -z "$LLM_PROXY" ]; then
    echo "Error: the LLM proxy did not start:"; cat "$PROXY_LOG"; exit 1
fi
echo "Model access through $LLM_PROXY (no keys in the container)"
KEY_ARGS=(
    -e ANTHROPIC_API_KEY="$LLM_PROXY_TOKEN" -e ANTHROPIC_BASE_URL="$LLM_PROXY/anthropic"
    -e OPENAI_API_KEY="$LLM_PROXY_TOKEN" -e OPENAI_BASE_URL="$LLM_PROXY/openai/v1"
    -e TOGETHER_API_KEY="$LLM_PROXY_TOKEN" -e TOGETHER_BASE_URL="$LLM_PROXY/together/v1"
)

# --ulimit nofile: Mininet raises RLIMIT_NOFILE on startup; without this the container
# inherits a low hard limit and setrlimit fails with a harmless but noisy warning.
docker run --rm \
    --privileged \
    --ulimit nofile=65536:65536 \
    "${GPU_ARGS[@]}" \
    -v "$PROJECT_ROOT:/workspace" \
    -w /workspace \
    "${KEY_ARGS[@]}" \
    -e TQDM_DISABLE="${TQDM_DISABLE:-}" \
    "$IMAGE_NAME" \
    sudo -E /app/env/bin/python3 "$PYTHON_SCRIPT_REL" $SCRIPT_ARGS
