#!/bin/bash

# Script to start vLLM and Chat servers (local development)

echo "=== vLLM + LangChain Demo Startup Script (Local Development) ==="
echo ""
echo "Note: This script is for local development. For production, use docker-compose"
echo ""

# Check model files (vLLM needs HuggingFace format, not GGUF)
if [ ! -d "./models" ] || [ -z "$(ls -A ./models 2>/dev/null)" ]; then
    echo "Warning: Model directory doesn't exist or is empty, please download model files first"
    echo "vLLM needs HuggingFace format models, not GGUF format"
    echo "Refer to README.md for instructions"
    echo ""
fi

# Check if vLLM is installed
if ! command -v python &> /dev/null; then
    echo "Error: Python not found, please install Python first"
    exit 1
fi

# Check if vLLM is available
if ! python -c "import vllm" 2>/dev/null; then
    echo "Warning: vLLM not installed, please install vLLM first"
    echo "Install command: pip install vllm"
    echo "Or use Docker: docker-compose up"
    exit 1
fi

# Set environment variables
export VLLM_SERVER_URL=${VLLM_SERVER_URL:-http://localhost:8001/v1}
export VLLM_MODEL_NAME=${VLLM_MODEL_NAME:-Qwen/Qwen2.5-1.5B-Instruct}

# Start vLLM server (background)
echo "Starting vLLM server (port 8001)..."
echo "Model: $VLLM_MODEL_NAME"
python -m vllm.entrypoints.openai.api_server \
    --model "$VLLM_MODEL_NAME" \
    --port 8001 \
    --host 0.0.0.0 \
    --trust-remote-code &
VLLM_PID=$!
echo "vLLM server PID: $VLLM_PID"

# Wait for vLLM server to start
echo "Waiting for vLLM server to start..."
sleep 10

# Check if vLLM server is running
if ! kill -0 $VLLM_PID 2>/dev/null; then
    echo "Error: vLLM server startup failed"
    exit 1
fi

# Start Chat server (foreground)
echo "Starting Chat server (port 8000)..."
echo "Visit http://localhost:8000/docs to view API documentation"
echo "Press Ctrl+C to stop all services"
echo ""

# Set environment variables for chat_server.py
export VLLM_SERVER_URL="http://localhost:8001/v1"
python chat_server.py

# Cleanup: if Chat server exits, stop vLLM server
echo ""
echo "Stopping vLLM server..."
kill $VLLM_PID 2>/dev/null || true
echo "All services stopped"

