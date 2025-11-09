# vLLM + LangChain 极简示例

这是一个基于 vLLM + LangChain 的极简示例，展示了如何构建一个完整的工具调用系统：
- **vLLM 服务器**：提供 LLM 推理服务（通过 OpenAI API 兼容接口）
- **FastAPI Chat 服务器**：提供聊天服务，使用 LangChain Agent 自动处理工具调用

## 相关项目

- https://github.com/fastapi/fastapi
- https://github.com/vllm-project/vllm
- https://github.com/langchain-ai/langchain
- https://github.com/huggingface/transformers

## 使用模型

- https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct

## 参考文档

- https://docs.vllm.ai/
- https://python.langchain.com/
- https://python.langchain.com/docs/modules/agents/
- https://www.ibm.com/think/topics/react-agent

## 功能特性

- 🤖 **真实的LLM推理**：使用 vLLM 提供高性能 LLM 推理服务
- 💬 **友好对话**：支持自然语言对话，可以友好地回复问候和闲聊
- 🛠️ **智能工具调用**：使用 LangChain ReAct Agent 自动处理工具调用
- 🔌 **LangChain 集成**：直接定义 LangChain Tool，无需 MCP 协议
- 🐳 Docker 容器化部署：支持多服务架构（vLLM 服务器 + Chat 服务器）
- 🌐 HTTP API 接口，支持 curl 交互
- ⚡ 基于 vLLM 的高性能推理（支持 GPU 和 CPU）
- 🛡️ 完善的错误处理和友好的错误提示

## 快速开始

### 1. 下载模型

项目使用 **Llama 3.1 8B-Instruct** 模型（HuggingFace 格式）。

**重要**：vLLM 需要 **HuggingFace 格式**的模型，不支持 GGUF 格式。

**特点**：
- 模型大小：约16GB（完整模型）或更小的量化版本
- 内存需求：约8-16GB RAM（取决于模型大小）
- 工具调用：支持原生 tool_calls
- 推理速度：高性能（GPU 模式）或中等（CPU 模式）
- **优势**：高性能推理，支持并发请求

**下载方法**：

```bash
# 方法1：使用 huggingface-cli（推荐）
pip install huggingface_hub
mkdir -p models
huggingface-cli download meta-llama/Llama-3.1-8B-Instruct \
    --local-dir ./models/llama-3.1-8b-instruct

# 方法2：使用 git lfs
git lfs install
git clone https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct ./models/llama-3.1-8b-instruct
```

**注意**：
- 模型文件需要放在 `./models/` 目录下
- 模型路径可以通过环境变量 `VLLM_MODEL_NAME` 配置
- 如果使用量化版本，需要确保 vLLM 支持该格式

### 2. 构建和启动

#### 方法一：使用构建脚本（推荐）

```bash
# 1. 配置代理（可选）
cp env.example .env
# 编辑 .env 文件，设置你的代理配置和模型名称

# 2. 使用构建脚本
./build.sh

# 3. 启动服务
docker-compose up
```

#### 方法二：手动构建

```bash
# 无代理环境
docker-compose build
docker-compose up

# 企业代理环境
export BUILD_PROXY=http://your-proxy:port
docker-compose build
docker-compose up
```

#### 配置说明

- **BUILD_PROXY**: Docker 构建时的代理设置
- **VLLM_MODEL_NAME**: vLLM 使用的模型名称（默认：`meta-llama/Llama-3.1-8B-Instruct`）
- **VLLM_SERVER_URL**: vLLM 服务器地址（默认：`http://vllm-server:8001/v1`）

服务将在以下地址启动：
- **vLLM 服务器**：`http://localhost:8001`（提供 OpenAI API 兼容接口）
- **Chat 服务器**：`http://localhost:8000`（提供聊天服务）

**启动验证**：
启动后查看日志，应该看到：
- vLLM 服务器：`Uvicorn running on http://0.0.0.0:8001`
- Chat 服务器：`vLLM客户端创建成功`
- Chat 服务器：`工具创建完成，共 3 个工具`
- Chat 服务器：`Agent初始化完成，工具调用将由LangChain自动处理`

**运行时日志**：
- LangChain Agent 会自动处理工具调用，日志会显示工具调用过程
- 使用 `verbose=True` 可以看到详细的工具调用和响应信息

**注意**：
- 需要先下载 Llama 3.1 8B 模型文件（HuggingFace 格式）
- 工具调用由 LangChain ReAct Agent 自动处理，无需手工解析
- Agent 最大迭代次数设置为 3 次，避免响应时间过长
- vLLM 主要针对 GPU 优化，CPU 模式性能较差

### 3. 测试接口

#### 健康检查

```bash
curl http://localhost:8000/health
```

**预期输出**:
```json
{
  "status": "healthy",
  "agent_loaded": true,
  "vllm_available": true,
  "tools_count": 3
}
```

**注意**：如果 `agent_loaded` 为 `false`，说明 Agent 初始化失败；如果 `vllm_available` 为 `false`，说明无法连接到 vLLM 服务器。

#### 查看可用工具

```bash
curl http://localhost:8000/tools
```

#### 聊天测试

**注意**: 
1. 如果中文显示为 Unicode 转义字符（如 `\u6211`），可以使用 `jq` 或 `python3 -m json.tool` 来正确显示
2. 请确保使用**英文引号**，而不是中文引号（""）

```bash
# 问候对话（自然语言回复）
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}' | jq .
# 预期输出:
# {
#   "raw_response": "你好！我是一个数学计算助手...",
#   "tools_available": ["add_numbers", "multiply_numbers", "calculate_expression"]
# }

# 简单加法（工具调用）
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "计算 5 + 3"}' | jq .
# 预期输出:
# {
#   "raw_response": "...",
#   "tools_available": ["add_numbers", "multiply_numbers", "calculate_expression"]
# }

# 乘法运算（工具调用）
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "计算 4 * 7"}' | jq .
# 预期输出:
# {
#   "raw_response": "...",
#   "tools_available": ["add_numbers", "multiply_numbers", "calculate_expression"]
# }

# 表达式计算（工具调用）
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "计算 2+3*4"}' | jq .
# 预期输出:
# {
#   "raw_response": "...",
#   "tools_available": ["add_numbers", "multiply_numbers", "calculate_expression"]
# }
```

**功能说明**：
- 🧮 **计算请求**：当用户询问数学计算问题时，LLM 会自动调用相应的工具进行计算
- 💬 **友好对话**：当用户问候或闲聊时，LLM 会以自然语言友好回复（不会调用工具）
- 🔍 **智能识别**：LLM 会自动识别用户意图，决定是使用工具还是直接回复
- ⚡ **快速响应**：最大迭代次数限制为 3 次，确保响应时间合理
- 📝 **完整响应**：返回完整原始输出（`raw_response`）

**替代方案**（如果系统没有安装 `jq`）：
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "计算 5 + 3"}' | python3 -m json.tool
```

## 项目架构

### 🔍 架构关系

```
┌─────────────────────────────────────────────────────────────┐
│                  User Request (curl)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           FastAPI Chat Server (Port 8000)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LangChain Agent + vLLM Client                      │   │
│  │  - Analyze user request                              │   │
│  │  - Generate tool call                                 │   │
│  │  - Generate final response based on tool result      │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                │
│                            │ HTTP Request                   │
│                            │ (OpenAI API Compatible)        │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LangChain Tools (Direct Definition)                │   │
│  │  - add_numbers()                                     │   │
│  │  - multiply_numbers()                                │   │
│  │  - calculate_expression()                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP Request
                            │ POST /v1/chat/completions
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         vLLM Server (Port 8001)                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  vLLM OpenAI API Server                              │   │
│  │  - Load model (HuggingFace format)                   │   │
│  │  - Handle inference requests                          │   │
│  │  - Return responses                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**关键说明**：
- **vLLM 服务器**（端口8001）：提供 OpenAI API 兼容接口，处理 LLM 推理请求
- **FastAPI Chat 服务器**（端口8000）：使用 LangChain Agent，直接定义工具，通过 HTTP 调用 vLLM 服务器
- **工作流程**：用户请求 → Chat 服务器 → LangChain Agent 分析 → 调用工具 → 调用 vLLM → 返回结果 → 生成最终回复

### 🚀 数据流示例

**User Request: "Calculate 25 + 17"**

```
1. User → Chat Server (POST /chat)
   {"message": "Calculate 25 + 17"}

2. Chat Server → LangChain Agent
   Agent analysis: "Need to call add_numbers tool"
   Generate tool call: add_numbers(a=25, b=17)

3. Chat Server → Tool Execution
   Execute: add_numbers(25, 17) → return 42

4. Chat Server → vLLM Server (POST /v1/chat/completions)
   Request: Generate response with tool result

5. vLLM Server → Chat Server
   Return: LLM generated response

6. Chat Server → User
   {"raw_response": "计算结果: 42", "tools_available": [...]}
```

## 项目结构

```
vllm_demo/
├── Dockerfile              # Chat 服务器 Docker 配置
├── Dockerfile.vllm        # vLLM 服务器 Docker 配置
├── docker-compose.yml      # Docker Compose 配置（两个服务：vllm-server + chat-server）
├── pyproject.toml         # Python 项目配置和依赖（使用 uv 管理）
├── docker-set-proxy.sh    # 代理配置辅助脚本
├── build.sh               # 构建脚本（支持环境变量配置）
├── start_servers.sh       # 本地启动脚本（同时启动两个服务）
├── env.example            # 环境配置示例文件
├── chat_server.py         # FastAPI Chat 服务器（端口8000）
├── models/                # 模型文件目录（Volume 挂载）
└── README.md              # 使用说明
```

## 技术栈

- **vLLM**: >= 0.2.0（高性能 LLM 推理引擎）
- **LangChain**: >= 0.1.0（Agent 框架和工具管理）
- **LangChain OpenAI**: >= 0.1.0（OpenAI API 兼容客户端）
- **AI 模型**: Llama 3.1 8B-Instruct（HuggingFace 格式）
- **Web 框架**: FastAPI >= 0.104.0（Chat 服务器）
- **HTTP 客户端**: httpx >= 0.25.0
- **ASGI 服务器**: uvicorn >= 0.24.0
- **容器化**: Docker + Docker Compose
- **代理处理**: 自动代理配置脚本

## 模型信息

### Llama 3.1 8B-Instruct（默认，推荐）

- **参数量**: 8B
- **格式**: HuggingFace（不支持 GGUF）
- **内存需求**: 约8-16GB RAM（取决于量化）
- **工具调用**: 支持原生 tool_calls
- **推理**: GPU 推理（推荐）或 CPU 推理（性能较差）
- **速度**: 高性能（GPU）或中等（CPU）
- **优势**: 高性能推理，支持并发请求

## 运行模式

项目**默认使用真实LLM模式**，需要下载模型文件才能运行。模型文件会在启动时自动加载，并进行真实的推理计算。

### 真实LLM模式（默认）

项目使用真实的 Llama 3.1 8B 模型进行推理：
- ✅ **真实LLM推理**：使用 vLLM 实际调用模型
- ✅ **智能工具调用**：使用 LangChain ReAct Agent 自动处理工具调用
- ✅ **原生tool_calls支持**：Llama 3.1 8B 支持原生 tool_calls
- ✅ **友好对话**：支持自然语言对话，可以友好回复问候和闲聊
- ✅ **错误处理**：完善的参数验证和错误提示
- ⚠️ **需要模型文件**：必须下载模型文件到 `./models/` 目录才能运行
- ⚠️ **需要 vLLM 服务器**：vLLM 服务器必须独立运行

如果模型文件不存在或 vLLM 服务器未运行，服务将无法启动并显示错误信息。

## 注意事项

1. **模型文件必需**: 必须下载 Llama 3.1 8B 模型文件（HuggingFace 格式）到 `./models/` 目录，否则服务无法启动
2. **内存要求**: 建议至少 8-16GB 可用内存（取决于模型大小）
3. **网络连接**: 首次下载模型需要良好的网络连接
4. **代理环境**: 企业网络环境需要配置代理，详见构建说明
5. **请求格式**: 使用 curl 时请确保 JSON 使用英文引号，例如 `'{"message": "你好"}'`
6. **工具调用**: 工具调用由 LangChain Agent 自动处理，无需手工解析或配置
7. **GPU 支持**: vLLM 主要针对 GPU 优化，CPU 模式性能较差
8. **模型格式**: vLLM 需要 HuggingFace 格式，不支持 GGUF 格式

## 故障排除

### vLLM 服务器连接失败

如果 Chat 服务器无法连接到 vLLM 服务器：
1. 确保 vLLM 服务器已启动（`vllm-server` 服务）
2. 检查 `VLLM_SERVER_URL` 环境变量是否正确（Docker 内部使用 `http://vllm-server:8001/v1`，本地使用 `http://localhost:8001/v1`）
3. 查看日志确认两个服务都在运行
4. Chat 服务器启动时会自动重试连接（最多15次，每次间隔2秒）

### 模型文件不存在

如果服务启动失败，提示模型文件不存在：
1. 确保已下载模型文件到 `./models/` 目录（HuggingFace 格式）
2. 检查模型路径是否正确（通过 `VLLM_MODEL_NAME` 环境变量配置）
3. 验证文件权限，确保可读
4. 查看服务器日志了解详细错误信息

### GPU 支持

如果需要 GPU 支持：
1. 确保 Docker 支持 GPU（安装 nvidia-docker2）
2. 在 `docker-compose.yml` 中取消注释 GPU 配置
3. 确保系统有可用的 NVIDIA GPU

### 内存不足

如果遇到内存不足，可以尝试：
- 使用更小的量化版本模型
- 减少 vLLM 的并发请求数
- 关闭其他占用内存的程序

### JSON格式错误

如果遇到 `400 Bad Request` 或 JSON 格式错误：
- 确保使用**英文引号**，不要使用中文引号
- 检查JSON格式是否正确，例如：`'{"message": "你好"}'`
- 查看错误响应中的详细提示和示例

### 端口冲突

如果端口被占用：
- **8000 端口（Chat 服务器）**：在 `docker-compose.yml` 中修改 `chat-server` 的端口映射
- **8001 端口（vLLM 服务器）**：在 `docker-compose.yml` 中修改 `vllm-server` 的端口映射，并更新 `chat_server.py` 中的 `VLLM_SERVER_URL` 环境变量

## 与原项目的区别

### 架构差异

- **原项目**：FastMCP 服务器（MCP 协议）+ Chat 服务器（LlamaIndex）
- **新项目**：vLLM 服务器（OpenAI API）+ Chat 服务器（LangChain）

### 技术栈差异

- **原项目**：llama-cpp-python + LlamaIndex + FastMCP
- **新项目**：vLLM + LangChain（直接定义工具，无需 MCP）

### 模型格式差异

- **原项目**：GGUF 格式（量化模型）
- **新项目**：HuggingFace 格式（完整模型或量化版本）

### 性能差异

- **原项目**：CPU 推理，适合资源受限环境
- **新项目**：GPU 推理（推荐）或 CPU 推理，高性能，支持并发

