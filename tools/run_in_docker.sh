#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")
IMAGE_NAME="agentic-networks"

usage() {
    echo "Usage: $0 <script.py> [args...]"
    echo "  Runs the given Python script inside the Docker container."
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
PYTHON_SCRIPT_REL=$(realpath --relative-to="$PROJECT_ROOT" "$PYTHON_SCRIPT_ABS")

echo "Building image '$IMAGE_NAME'..."
docker build -t "$IMAGE_NAME" \
    --build-arg UID="$(id -u)" \
    --build-arg GID="$(id -g)" \
    "$PROJECT_ROOT"

echo "Running: $PYTHON_SCRIPT_REL $SCRIPT_ARGS"

docker run --rm -it \
    --privileged \
    --network host \
    -v "$PROJECT_ROOT:/workspace" \
    -w /workspace \
    -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
    "$IMAGE_NAME" \
    sudo -E /app/env/bin/python3 "$PYTHON_SCRIPT_REL" $SCRIPT_ARGS
