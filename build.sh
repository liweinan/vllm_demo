#!/bin/bash

# vLLM + LangChain Demo 构建脚本
# 支持环境变量配置代理，与 Dockerfile 和 docker-compose.yml 配合使用
#
# 使用方法：
#   1. 在 .env 文件中设置 BUILD_PROXY（推荐）
#   2. 或设置环境变量：export BUILD_PROXY=http://your-proxy:port
#   3. 运行: ./build.sh
#
# docker-compose.yml 会自动读取 BUILD_PROXY 并传递给 Dockerfile

set -e

echo "=== vLLM + LangChain Demo 构建脚本 ==="
echo ""

# 加载 .env 文件（如果存在）
if [ -f ".env" ]; then
    echo "✓ 加载 .env 文件..."
    set -a
    source .env
    set +a
fi

# 显示代理配置（如果有）
if [ -n "$BUILD_PROXY" ]; then
    echo "✓ 使用代理: $BUILD_PROXY"
    if echo "$BUILD_PROXY" | grep -q "localhost"; then
        echo "  注意: Dockerfile 会自动将 localhost 转换为 host.docker.internal"
    fi
    echo ""
fi

# docker-compose 会自动读取 BUILD_PROXY 环境变量并传递给 Dockerfile
echo "开始构建 Docker 镜像..."
echo "注意：vllm-server 使用官方镜像，chat-server 需要构建"
docker-compose build

echo ""
echo "=== 构建完成 ==="
echo "运行服务: docker-compose up"
echo "注意：确保模型文件已下载到 ./models/ 目录（HuggingFace 格式）"

