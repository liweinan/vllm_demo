# vLLM + LangChain Minimal Example

This is a minimal example based on vLLM + LangChain, demonstrating how to build a complete tool calling system:
- **vLLM Server**: Provides LLM inference service (via OpenAI API compatible interface)
- **FastAPI Chat Server**: Provides chat service, using LangChain Agent to automatically handle tool calls

## Related Projects

- https://github.com/fastapi/fastapi
- https://github.com/vllm-project/vllm
- https://github.com/langchain-ai/langchain
- https://github.com/huggingface/transformers

## Model Used

- https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct

## Reference Documentation

- https://docs.vllm.ai/
- https://python.langchain.com/
- https://python.langchain.com/docs/modules/agents/
- https://www.ibm.com/think/topics/react-agent

## Features

- 🤖 **Real LLM Inference**: Uses vLLM to provide high-performance LLM inference service
- 💬 **Friendly Conversation**: Supports natural language conversation, can reply to greetings and casual chat
- 🛠️ **Smart Tool Calling**: Uses LangChain ReAct Agent to automatically handle tool calls
- 🔌 **LangChain Integration**: Directly define LangChain Tools, no MCP protocol needed
- 🐳 **Docker Containerized Deployment**: Supports multi-service architecture (vLLM server + Chat server)
- 🌐 **HTTP API Interface**: Supports curl interaction
- ⚡ **High-performance inference** based on vLLM (supports GPU and CPU)
- 🛡️ **Comprehensive error handling** and friendly error messages

## Quick Start

### ⚠️ macOS (Apple Silicon) Users Note

**Important**: Running vLLM CPU version on macOS (ARM64) requires special configuration:

1. **Architecture Compatibility**:
   - vLLM CPU version mainly supports x86_64 architecture
   - macOS uses `platform: linux/amd64` with Rosetta 2 emulation to run x86_64 containers
   - Performance may be slightly slower than native Linux

2. **Docker Configuration**:
   - Ensure Docker Desktop has "Use Rosetta for x86/amd64 emulation" enabled
   - `docker-compose.yml` is configured with `platform: linux/amd64`

3. **Building CPU Image**:
   - `Dockerfile.vllm` will build CPU version from source (first build takes 30-60 minutes)
   - Or use pre-built CPU image (if available)

4. **Alternatives**:
   - If vLLM CPU build fails, consider using other CPU-friendly inference engines
   - Or run on Linux server or cloud GPU

### 1. Download Model

The project uses **Qwen2.5-1.5B-Instruct** model (HuggingFace format).

**Important**: vLLM requires **HuggingFace format** models, does not support GGUF format.

**Characteristics**:
- Model size: ~3GB (full model)
- Memory requirement: ~4-6GB RAM (CPU mode)
- Tool calling: Supports native tool_calls
- Inference speed: Medium (CPU mode), suitable for CPU inference
- **Advantages**: Open source (Apache 2.0), small model, fast, supports tool calling

**Download Methods**:

```bash
# Method 1: Using Hugging Face CLI (Recommended)
# Install Hugging Face CLI
wget https://hf.co/cli/install.sh
chmod +x install.sh
./install.sh

# Download model
mkdir -p models
hf download Qwen/Qwen2.5-1.5B-Instruct \
    --local-dir ./models/qwen2.5-1.5b-instruct

# Method 2: Using Python API
pip install huggingface_hub
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-1.5B-Instruct', local_dir='./models/qwen2.5-1.5b-instruct')"

# Method 3: Using git lfs
git lfs install
git clone https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct ./models/qwen2.5-1.5b-instruct
```

**Note**:
- Model files need to be placed in `./models/` directory
- Model path can be configured via environment variable `VLLM_MODEL_NAME`
- If using quantized version, ensure vLLM supports that format

### 2. Build and Start

#### Method 1: Using Build Script (Recommended)

```bash
# 1. Configure proxy (optional)
cp env.example .env
# Edit .env file, set your proxy configuration and model name

# 2. Use build script
./build.sh

# 3. Start services
docker-compose up
```

#### Method 2: Manual Build

```bash
# No proxy environment
docker-compose build
docker-compose up

# Enterprise proxy environment
export BUILD_PROXY=http://your-proxy:port
docker-compose build
docker-compose up
```

#### Configuration

- **BUILD_PROXY**: Proxy settings for Docker build
- **VLLM_MODEL_NAME**: Model name used by vLLM (default: `Qwen/Qwen2.5-1.5B-Instruct`)
- **VLLM_SERVER_URL**: vLLM server address (default: `http://vllm-server:8001/v1`)

Services will start at:
- **vLLM Server**: `http://localhost:8001` (provides OpenAI API compatible interface)
- **Chat Server**: `http://localhost:8000` (provides chat service)

**Startup Verification**:
After startup, check logs, you should see:
- vLLM server: `Uvicorn running on http://0.0.0.0:8001`
- Chat server: `vLLM client created successfully`
- Chat server: `Tools created, total 3 tools`
- Chat server: `Agent initialization complete, tool calls will be automatically handled by LangChain`

**Runtime Logs**:
- LangChain Agent will automatically handle tool calls, logs will show tool call process
- Using `verbose=True` you can see detailed tool call and response information

**Note**:
- Need to download Qwen2.5-1.5B-Instruct model files first (HuggingFace format)
- Tool calls are automatically handled by LangChain ReAct Agent, no manual parsing needed
- Agent max iterations set to 3 to avoid long response times
- vLLM is mainly optimized for GPU, CPU mode performance is poor

### 3. Test API

#### Health Check

```bash
curl http://localhost:8000/health
```

**Expected Output**:
```json
{
  "status": "healthy",
  "agent_loaded": true,
  "vllm_available": true,
  "tools_count": 3
}
```

**Note**: If `agent_loaded` is `false`, Agent initialization failed; if `vllm_available` is `false`, cannot connect to vLLM server.

#### List Available Tools

```bash
curl http://localhost:8000/tools
```

#### Chat Test

**Note**: 
1. If Chinese characters display as Unicode escape sequences (like `\u6211`), you can use `jq` or `python3 -m json.tool` to display correctly
2. Make sure to use **English quotes**, not Chinese quotes ("")

```bash
# Greeting conversation (natural language reply)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}' | jq .
# Expected output:
# {
#   "raw_response": "Hello! I am a math calculation assistant...",
#   "tools_available": ["add_numbers", "multiply_numbers", "calculate_expression"]
# }

# Simple addition (tool call)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 5 + 3"}' | jq .
# Expected output:
# {
#   "raw_response": "...",
#   "tools_available": ["add_numbers", "multiply_numbers", "calculate_expression"]
# }

# Multiplication (tool call)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 4 * 7"}' | jq .
# Expected output:
# {
#   "raw_response": "...",
#   "tools_available": ["add_numbers", "multiply_numbers", "calculate_expression"]
# }

# Expression calculation (tool call)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 2+3*4"}' | jq .
# Expected output:
# {
#   "raw_response": "...",
#   "tools_available": ["add_numbers", "multiply_numbers", "calculate_expression"]
# }
```

**Functionality**:
- 🧮 **Calculation Requests**: When user asks math calculation questions, LLM will automatically call corresponding tools for calculation
- 💬 **Friendly Conversation**: When user greets or chats, LLM will reply naturally and friendly (will not call tools)
- 🔍 **Smart Recognition**: LLM will automatically recognize user intent, decide whether to use tools or reply directly
- ⚡ **Fast Response**: Max iterations limited to 3 to ensure reasonable response time
- 📝 **Complete Response**: Returns complete raw output (`raw_response`)

**Alternative** (if system doesn't have `jq` installed):
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 5 + 3"}' | python3 -m json.tool
```

## Project Architecture

### 🔍 Architecture Diagram

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

**Key Points**:
- **vLLM Server** (port 8001): Provides OpenAI API compatible interface, handles LLM inference requests
- **FastAPI Chat Server** (port 8000): Uses LangChain Agent, directly defines tools, calls vLLM server via HTTP
- **Workflow**: User request → Chat server → LangChain Agent analysis → Call tool → Call vLLM → Return result → Generate final reply

### 🚀 Data Flow Example

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
   {"raw_response": "Calculation result: 42", "tools_available": [...]}
```

## Project Structure

```
vllm_demo/
├── Dockerfile              # Chat server Docker configuration
├── Dockerfile.vllm        # vLLM server Docker configuration
├── docker-compose.yml      # Docker Compose configuration (two services: vllm-server + chat-server)
├── pyproject.toml         # Python project configuration and dependencies (using uv)
├── docker-set-proxy.sh    # Proxy configuration helper script
├── build.sh               # Build script (supports environment variable configuration)
├── start_servers.sh       # Local startup script (starts both services)
├── env.example            # Environment configuration example file
├── chat_server.py         # FastAPI Chat server (port 8000)
├── models/                # Model files directory (Volume mount)
└── README.md              # Usage instructions
```

## Tech Stack

- **vLLM**: >= 0.2.0 (High-performance LLM inference engine)
- **LangChain**: >= 0.1.0 (Agent framework and tool management)
- **LangChain OpenAI**: >= 0.1.0 (OpenAI API compatible client)
- **AI Model**: Qwen2.5-1.5B-Instruct (HuggingFace format)
- **Web Framework**: FastAPI >= 0.104.0 (Chat server)
- **HTTP Client**: httpx >= 0.25.0
- **ASGI Server**: uvicorn >= 0.24.0
- **Containerization**: Docker + Docker Compose
- **Proxy Handling**: Automatic proxy configuration script

## Model Information

### Qwen2.5-1.5B-Instruct (Default, Recommended)

- **Parameters**: 1.5B
- **Format**: HuggingFace (does not support GGUF)
- **Memory Requirement**: ~4-6GB RAM (CPU mode)
- **Tool Calling**: Supports native tool_calls
- **Inference**: CPU inference (recommended) or GPU inference
- **Speed**: Medium (CPU), suitable for CPU inference
- **Advantages**: Open source (Apache 2.0), small model, fast, supports tool calling

## Running Modes

The project **defaults to real LLM mode**, requires downloading model files to run. Model files will be automatically loaded at startup and perform real inference calculations.

### Real LLM Mode (Default)

The project uses real Qwen2.5-1.5B-Instruct model for inference:
- ✅ **Real LLM Inference**: Uses vLLM to actually call the model
- ✅ **Smart Tool Calling**: Uses LangChain ReAct Agent to automatically handle tool calls
- ✅ **Native tool_calls Support**: Qwen2.5-1.5B-Instruct supports native tool_calls
- ✅ **Friendly Conversation**: Supports natural language conversation, can reply to greetings and casual chat
- ✅ **Error Handling**: Comprehensive parameter validation and error messages
- ⚠️ **Requires Model Files**: Must download model files to `./models/` directory to run
- ⚠️ **Requires vLLM Server**: vLLM server must run independently

If model files don't exist or vLLM server is not running, the service will fail to start and display error messages.

## Notes

1. **Model Files Required**: Must download Qwen2.5-1.5B-Instruct model files (HuggingFace format) to `./models/` directory, otherwise service cannot start
2. **Memory Requirements**: Recommend at least 4-6GB available memory (CPU mode, depends on model size)
3. **Network Connection**: First-time model download requires good network connection
4. **Proxy Environment**: Enterprise network environments need proxy configuration, see build instructions
5. **Request Format**: When using curl, ensure JSON uses English quotes, e.g., `'{"message": "Hello"}'`
6. **Tool Calling**: Tool calls are automatically handled by LangChain Agent, no manual parsing or configuration needed
7. **GPU Support**: vLLM is mainly optimized for GPU, CPU mode performance is poor
8. **Model Format**: vLLM requires HuggingFace format, does not support GGUF format
9. **macOS Limitations**: vLLM is mainly designed for Linux + CUDA environments. On macOS:
   - vLLM may not run properly (missing CUDA support)
   - Recommend running on Linux system or CUDA-supported environment
   - If must run on macOS, consider using other LLM services (like HuggingFace Transformers)

## Troubleshooting

### vLLM Server Connection Failed

If Chat server cannot connect to vLLM server:
1. Ensure vLLM server is started (`vllm-server` service)
2. Check `VLLM_SERVER_URL` environment variable is correct (use `http://vllm-server:8001/v1` inside Docker, `http://localhost:8001/v1` locally)
3. Check logs to confirm both services are running
4. Chat server will automatically retry connection on startup (max 15 times, 2 seconds interval)

### Model Files Don't Exist

If service startup fails, prompting model files don't exist:
1. Ensure model files are downloaded to `./models/` directory (HuggingFace format)
2. Check model path is correct (configured via `VLLM_MODEL_NAME` environment variable)
3. Verify file permissions, ensure readable
4. Check server logs for detailed error information

### GPU Support

If GPU support is needed:
1. Ensure Docker supports GPU (install nvidia-docker2)
2. Uncomment GPU configuration in `docker-compose.yml`
3. Ensure system has available NVIDIA GPU

### Out of Memory

If encountering out of memory, you can try:
- Use smaller quantized version model
- Reduce vLLM concurrent request count
- Close other memory-consuming programs

### JSON Format Error

If encountering `400 Bad Request` or JSON format error:
- Ensure to use **English quotes**, don't use Chinese quotes
- Check JSON format is correct, e.g., `'{"message": "Hello"}'`
- Check error response for detailed prompts and examples

### Port Conflict

If port is occupied:
- **Port 8000 (Chat server)**: Modify port mapping for `chat-server` in `docker-compose.yml`
- **Port 8001 (vLLM server)**: Modify port mapping for `vllm-server` in `docker-compose.yml`, and update `VLLM_SERVER_URL` environment variable in `chat_server.py`

## Differences from Original Project

### Architecture Differences

- **Original Project**: FastMCP server (MCP protocol) + Chat server (LlamaIndex)
- **New Project**: vLLM server (OpenAI API) + Chat server (LangChain)

### Tech Stack Differences

- **Original Project**: llama-cpp-python + LlamaIndex + FastMCP
- **New Project**: vLLM + LangChain (directly define tools, no MCP needed)

### Model Format Differences

- **Original Project**: GGUF format (quantized model)
- **New Project**: HuggingFace format (full model or quantized version)

### Performance Differences

- **Original Project**: CPU inference, suitable for resource-constrained environments
- **New Project**: GPU inference (recommended) or CPU inference, high performance, supports concurrency
