#!/bin/bash

# 启动 vLLM 和 Chat 服务器的脚本（本地开发）

echo "=== vLLM + LangChain Demo 启动脚本（本地开发）==="
echo ""
echo "注意：此脚本用于本地开发。生产环境请使用 docker-compose"
echo ""

# 检查模型文件（vLLM 需要 HuggingFace 格式，不是 GGUF）
if [ ! -d "./models" ] || [ -z "$(ls -A ./models 2>/dev/null)" ]; then
    echo "警告: 模型目录不存在或为空，请先下载模型文件"
    echo "vLLM 需要 HuggingFace 格式的模型，不是 GGUF 格式"
    echo "参考 README.md 中的说明"
    echo ""
fi

# 检查 vLLM 是否已安装
if ! command -v python &> /dev/null; then
    echo "错误: 未找到 Python，请先安装 Python"
    exit 1
fi

# 检查 vLLM 是否可用
if ! python -c "import vllm" 2>/dev/null; then
    echo "警告: vLLM 未安装，请先安装 vLLM"
    echo "安装命令: pip install vllm"
    echo "或者使用 Docker: docker-compose up"
    exit 1
fi

# 设置环境变量
export VLLM_SERVER_URL=${VLLM_SERVER_URL:-http://localhost:8001/v1}
export VLLM_MODEL_NAME=${VLLM_MODEL_NAME:-meta-llama/Llama-3.1-8B-Instruct}

# 启动 vLLM 服务器（后台）
echo "启动 vLLM 服务器（端口 8001）..."
echo "模型: $VLLM_MODEL_NAME"
python -m vllm.entrypoints.openai.api_server \
    --model "$VLLM_MODEL_NAME" \
    --port 8001 \
    --host 0.0.0.0 \
    --trust-remote-code &
VLLM_PID=$!
echo "vLLM 服务器 PID: $VLLM_PID"

# 等待 vLLM 服务器启动
echo "等待 vLLM 服务器启动..."
sleep 10

# 检查 vLLM 服务器是否运行
if ! kill -0 $VLLM_PID 2>/dev/null; then
    echo "错误: vLLM 服务器启动失败"
    exit 1
fi

# 启动 Chat 服务器（前台）
echo "启动 Chat 服务器（端口 8000）..."
echo "访问 http://localhost:8000/docs 查看 API 文档"
echo "按 Ctrl+C 停止所有服务"
echo ""

# 设置环境变量供 chat_server.py 使用
export VLLM_SERVER_URL="http://localhost:8001/v1"
python chat_server.py

# 清理：如果 Chat 服务器退出，停止 vLLM 服务器
echo ""
echo "正在停止 vLLM 服务器..."
kill $VLLM_PID 2>/dev/null || true
echo "所有服务已停止"

