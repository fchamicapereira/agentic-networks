#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")
IMAGE_NAME="agentic-networks"

usage() {
    echo "Usage: $0 <script.py> [args...]"
    echo "  Builds the Docker image and runs the given Python script inside it."
    exit 1
}

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

# --ulimit nofile: Mininet raises RLIMIT_NOFILE on startup; without this the container
# inherits a low hard limit and setrlimit fails with a harmless but noisy warning.
docker run --rm \
    --privileged \
    --ulimit nofile=65536:65536 \
    "${GPU_ARGS[@]}" \
    -v "$PROJECT_ROOT:/workspace" \
    -w /workspace \
    -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    -e TOGETHER_API_KEY="${TOGETHER_API_KEY:-}" \
    -e TQDM_DISABLE="${TQDM_DISABLE:-}" \
    "$IMAGE_NAME" \
    sudo -E /app/env/bin/python3 "$PYTHON_SCRIPT_REL" $SCRIPT_ARGS
