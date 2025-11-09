#!/bin/bash

# vLLM + LangChain Demo Build Script
# Supports environment variable proxy configuration, works with Dockerfile and docker-compose.yml
#
# Usage:
#   1. Set BUILD_PROXY in .env file (recommended)
#   2. Or set environment variable: export BUILD_PROXY=http://your-proxy:port
#   3. Run: ./build.sh
#
# docker-compose.yml will automatically read BUILD_PROXY and pass it to Dockerfile

set -e

echo "=== vLLM + LangChain Demo Build Script ==="
echo ""

# Load .env file (if exists)
if [ -f ".env" ]; then
    echo "✓ Loading .env file..."
    set -a
    source .env
    set +a
fi

# Display proxy configuration (if any)
if [ -n "$BUILD_PROXY" ]; then
    echo "✓ Using proxy: $BUILD_PROXY"
    if echo "$BUILD_PROXY" | grep -q "localhost"; then
        echo "  Note: Dockerfile will automatically convert localhost to host.docker.internal"
    fi
    echo ""
fi

# docker-compose will automatically read BUILD_PROXY environment variable and pass it to Dockerfile
echo "Starting Docker image build..."
echo "Note: vllm-server uses official image, chat-server needs to be built"
docker-compose build

echo ""
echo "=== Build Complete ==="
echo "Run services: docker-compose up"
echo "Note: Ensure model files are downloaded to ./models/ directory (HuggingFace format)"

