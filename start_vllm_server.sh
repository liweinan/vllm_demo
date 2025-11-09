#!/bin/bash
# vLLM 服务器启动脚本
# 用于在容器内启动 vLLM OpenAI API 服务器

set -e

MODEL_PATH="${1:-/app/models/qwen2.5-1.5b-instruct}"
PORT="${2:-8001}"
HOST="${3:-0.0.0.0}"

echo "Starting vLLM server..."
echo "Model: $MODEL_PATH"
echo "Host: $HOST"
echo "Port: $PORT"

# 设置 HuggingFace 离线模式，强制使用本地文件，避免从网络下载
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# 使用 python -m 方式启动 vLLM OpenAI API 服务器
# 减少 max_model_len 以适应 KV cache 内存限制
# 禁用自定义操作以避免 CPU 版本的自定义操作缺失问题
# 通过 --compilation-config 设置 custom_ops=none
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

