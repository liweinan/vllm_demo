# Building vLLM on Linux x86_64 Server

## Quick Start

### 1. Copy Project to Linux Server

```bash
# On local Mac
cd ~/works/vllm_demo
rsync -avz --exclude '.git' --exclude 'models' --exclude '__pycache__' . anan@think.local:~/works/vllm_demo/
```

Or use git:

```bash
# On Linux server
cd ~/works
git clone <your-repo-url> vllm_demo
cd vllm_demo
```

### 2. Configure Environment Variables

```bash
# On Linux server
cd ~/works/vllm_demo
cp env.example .env
# Edit .env file, set proxy (if needed)
# BUILD_PROXY=http://your-proxy:port
```

### 3. Modify docker-compose.yml (Important)

On Linux x86_64, **do not need** `platform: linux/amd64`, as it's already native x86_64 architecture.

Edit `docker-compose.yml`, ensure `platform` line for `vllm-server` is commented out:

```yaml
vllm-server:
  # platform: linux/amd64  # Only needed on macOS, comment out on Linux x86_64
```

### 4. Build and Start

```bash
# Build vLLM server (first build takes 30-60 minutes)
docker-compose build vllm-server

# Or build all services
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f vllm-server
```

### 5. Verify

```bash
# Check service status
docker-compose ps

# Test health check
curl http://localhost:8000/health

# Test chat interface
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 2+3"}'
```

## Notes

1. **CPU Instruction Set**: Linux x86_64 server should correctly detect AVX2/AVX512, build should succeed
2. **Memory Requirements**: Building vLLM requires at least 8GB RAM, running needs more
3. **Build Time**: First build may take 30-60 minutes, depends on CPU performance
4. **Proxy Configuration**: If server needs proxy, ensure `BUILD_PROXY` is correctly configured in `.env`

## Troubleshooting

### If Build Fails (CPU Instruction Set Detection Failed)

Check CPU supported instruction sets:

```bash
grep flags /proc/cpuinfo | head -1
# Should see avx2 or avx512
```

If CPU doesn't support AVX2, vLLM CPU version cannot be built.

### If Out of Memory

Increase Docker memory limits, or use swap:

```bash
# Check available memory
free -h

# If needed, create swap file
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```
