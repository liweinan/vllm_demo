# 在 Linux x86_64 服务器上构建 vLLM

## 快速开始

### 1. 将项目复制到 Linux 服务器

```bash
# 在本地 Mac 上
cd ~/works/vllm_demo
rsync -avz --exclude '.git' --exclude 'models' --exclude '__pycache__' . anan@think.local:~/works/vllm_demo/
```

或者使用 git：

```bash
# 在 Linux 服务器上
cd ~/works
git clone <your-repo-url> vllm_demo
cd vllm_demo
```

### 2. 配置环境变量

```bash
# 在 Linux 服务器上
cd ~/works/vllm_demo
cp env.example .env
# 编辑 .env 文件，设置代理（如果需要）
# BUILD_PROXY=http://your-proxy:port
```

### 3. 修改 docker-compose.yml（重要）

在 Linux x86_64 上，**不需要** `platform: linux/amd64`，因为已经是原生 x86_64 架构。

编辑 `docker-compose.yml`，确保 `vllm-server` 的 `platform` 行被注释掉：

```yaml
vllm-server:
  # platform: linux/amd64  # 仅在 macOS 上需要，Linux x86_64 上注释掉
```

### 4. 构建和启动

```bash
# 构建 vLLM 服务器（首次构建需要 30-60 分钟）
docker-compose build vllm-server

# 或者构建所有服务
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f vllm-server
```

### 5. 验证

```bash
# 检查服务状态
docker-compose ps

# 测试健康检查
curl http://localhost:8000/health

# 测试聊天接口
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "计算 2+3"}'
```

## 注意事项

1. **CPU 指令集**：Linux x86_64 服务器应该能正确检测 AVX2/AVX512，构建应该能成功
2. **内存需求**：构建 vLLM 需要至少 8GB RAM，运行需要更多
3. **构建时间**：首次构建可能需要 30-60 分钟，取决于 CPU 性能
4. **代理配置**：如果服务器需要代理，确保 `.env` 中正确配置 `BUILD_PROXY`

## 故障排除

### 如果构建失败（CPU 指令集检测失败）

检查 CPU 支持的指令集：

```bash
grep flags /proc/cpuinfo | head -1
# 应该看到 avx2 或 avx512
```

如果 CPU 不支持 AVX2，vLLM CPU 版本无法构建。

### 如果内存不足

增加 Docker 的内存限制，或使用 swap：

```bash
# 检查可用内存
free -h

# 如果需要，创建 swap 文件
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

