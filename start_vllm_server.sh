#!/bin/bash
# vLLM Server Startup Script
# Used to start vLLM OpenAI API server inside container

set -e

MODEL_PATH="${1:-/app/models/qwen2.5-1.5b-instruct}"
PORT="${2:-8001}"
HOST="${3:-0.0.0.0}"

echo "Starting vLLM server..."
echo "Model: $MODEL_PATH"
echo "Host: $HOST"
echo "Port: $PORT"

# Set HuggingFace offline mode, force using local files, avoid network download
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Start vLLM OpenAI API server using python -m
# Reduce max_model_len to fit KV cache memory limits
# Disable custom operations to avoid missing custom ops issues in CPU version
# Set custom_ops=none via --compilation-config
exec python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --port "$PORT" \
    --host "$HOST" \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 2048 \
    --max-num-batched-tokens 2048 \
    --max-num-seqs 16 \
    --disable-custom-all-reduce \
    --enforce-eager \
    --compilation-config '{"custom_ops": ["none"]}'

