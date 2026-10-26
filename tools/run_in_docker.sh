#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")
IMAGE_NAME="agentic-networks"

usage() {
    echo "Usage: $0 [--llm-proxy URL --llm-proxy-token TOKEN] <script.py> [args...]"
    echo "  Builds the Docker image and runs the given Python script inside it."
    echo "  --llm-proxy, --llm-proxy-token: reach the models through demo/llm_proxy.py, so the"
    echo "  container gets only the proxy's address and a run token, never the real keys."
    exit 1
}

LLM_PROXY=""
LLM_PROXY_TOKEN=""
while [ $# -gt 0 ]; do
    case "$1" in
        --llm-proxy) [ $# -ge 2 ] || usage; LLM_PROXY="$2"; shift 2 ;;
        --llm-proxy-token) [ $# -ge 2 ] || usage; LLM_PROXY_TOKEN="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) break ;;
    esac
done
if { [ -n "$LLM_PROXY" ] && [ -z "$LLM_PROXY_TOKEN" ]; } || { [ -z "$LLM_PROXY" ] && [ -n "$LLM_PROXY_TOKEN" ]; }; then
    echo "Error: --llm-proxy and --llm-proxy-token go together"
    exit 1
fi

if [ $# -lt 1 ]; then
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

# Model access. With --llm-proxy (see demo/llm_proxy.py), the container gets only the proxy's
# address and a throwaway run token: the real keys never enter it, so an agent's commands can't
# read them. Otherwise the keys are passed in directly, as before.
if [ -n "$LLM_PROXY" ]; then
    echo "Model access through $LLM_PROXY (no keys in the container)"
    KEY_ARGS=(
        -e ANTHROPIC_API_KEY="$LLM_PROXY_TOKEN" -e ANTHROPIC_BASE_URL="$LLM_PROXY/anthropic"
        -e OPENAI_API_KEY="$LLM_PROXY_TOKEN" -e OPENAI_BASE_URL="$LLM_PROXY/openai/v1"
        -e TOGETHER_API_KEY="$LLM_PROXY_TOKEN" -e TOGETHER_BASE_URL="$LLM_PROXY/together/v1"
    )
else
    KEY_ARGS=(
        -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
        -e OPENAI_API_KEY="${OPENAI_API_KEY:-}"
        -e TOGETHER_API_KEY="${TOGETHER_API_KEY:-}"
    )
fi

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
