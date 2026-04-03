#!/usr/bin/bash

docker run --rm -it --runtime nvidia --gpus all -p 8000:8000 --ipc=host \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    vllm/vllm-openai:latest \
    --model Qwen/Qwen2.5-72B-Instruct-AWQ \
    --tensor-parallel-size 2 \
    --enable-auto-tool-choice --tool-call-parser hermes