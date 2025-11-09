# 多阶段构建：第一阶段使用轻量级基础镜像 + uv 管理 Python
# 使用 debian:bookworm-slim 作为基础，uv 会自动管理 Python 环境
FROM debian:bookworm-slim AS builder

# 配置 apt 代理（如果宿主机有代理）
# 注意：只对 localhost 进行替换，其他代理地址（如 squid.corp.redhat.com）保持不变
ARG BUILD_PROXY
RUN if [ -n "$BUILD_PROXY" ]; then \
        if echo "$BUILD_PROXY" | grep -q "localhost"; then \
            BUILD_PROXY_CONVERTED=$(echo "$BUILD_PROXY" | sed 's|localhost|host.docker.internal|g'); \
        else \
            BUILD_PROXY_CONVERTED="$BUILD_PROXY"; \
        fi && \
        echo "配置 apt 代理: $BUILD_PROXY_CONVERTED" && \
        echo "Acquire::http::Proxy \"$BUILD_PROXY_CONVERTED\";" > /etc/apt/apt.conf.d/01proxy && \
        echo "Acquire::https::Proxy \"$BUILD_PROXY_CONVERTED\";" >> /etc/apt/apt.conf.d/01proxy; \
    fi

# 配置 apt 重试和超时（独立层，可缓存）
RUN echo 'Acquire::Retries "10";' >> /etc/apt/apt.conf.d/99-retries && \
    echo 'Acquire::http::Timeout "120";' >> /etc/apt/apt.conf.d/99-timeout && \
    echo 'Acquire::https::Timeout "120";' >> /etc/apt/apt.conf.d/99-timeout

# 更新包列表（独立层，可缓存）
RUN apt-get update

# 安装基础工具（无需编译工具，因为不需要编译 llama-cpp-python）
RUN apt-get install -y --no-install-recommends --fix-missing \
    ca-certificates \
    curl

# 清理 apt 缓存（独立层，可缓存）
RUN rm -rf /var/lib/apt/lists/*

# 复制代理设置辅助脚本
COPY docker-set-proxy.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-set-proxy.sh

# 安装 uv（独立层，可缓存）
ARG BUILD_PROXY
RUN if [ -n "$BUILD_PROXY" ]; then \
        BUILD_PROXY_CONVERTED=$(/usr/local/bin/docker-set-proxy.sh "$BUILD_PROXY") && \
        echo "使用代理下载 uv: $BUILD_PROXY_CONVERTED" && \
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY || true && \
        export http_proxy="$BUILD_PROXY_CONVERTED" https_proxy="$BUILD_PROXY_CONVERTED" HTTP_PROXY="$BUILD_PROXY_CONVERTED" HTTPS_PROXY="$BUILD_PROXY_CONVERTED" && \
        curl --proxy "$BUILD_PROXY_CONVERTED" -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh && \
        sh /tmp/uv-install.sh && \
        rm -f /tmp/uv-install.sh; \
    else \
        echo "不使用代理下载 uv"; \
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY || true && \
        curl -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh && \
        sh /tmp/uv-install.sh && \
        rm -f /tmp/uv-install.sh; \
    fi

# 验证 uv 安装（独立层，可缓存）
RUN export PATH="/root/.local/bin:$PATH" && \
    /root/.local/bin/uv --version

# 复制项目文件（先复制配置文件，便于 uv sync）
WORKDIR /app
COPY pyproject.toml ./

# 安装 Python（独立层，可缓存）
ARG BUILD_PROXY
RUN export PATH="/root/.local/bin:$PATH" && \
    if [ -n "$BUILD_PROXY" ]; then \
        BUILD_PROXY_CONVERTED=$(/usr/local/bin/docker-set-proxy.sh "$BUILD_PROXY") && \
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY || true && \
        export http_proxy="$BUILD_PROXY_CONVERTED" https_proxy="$BUILD_PROXY_CONVERTED" HTTP_PROXY="$BUILD_PROXY_CONVERTED" HTTPS_PROXY="$BUILD_PROXY_CONVERTED"; \
    fi && \
    echo "使用 uv 安装 Python 3.11..." && \
    uv python install 3.11 && \
    uv python list

# 使用 uv sync 创建虚拟环境并安装依赖（独立层，只有依赖改变时才重新执行）
ARG BUILD_PROXY
RUN export PATH="/root/.local/bin:$PATH" && \
    if [ -n "$BUILD_PROXY" ]; then \
        BUILD_PROXY_CONVERTED=$(/usr/local/bin/docker-set-proxy.sh "$BUILD_PROXY") && \
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY || true && \
        export http_proxy="$BUILD_PROXY_CONVERTED" https_proxy="$BUILD_PROXY_CONVERTED" HTTP_PROXY="$BUILD_PROXY_CONVERTED" HTTPS_PROXY="$BUILD_PROXY_CONVERTED" && \
        echo "已配置 uv 代理: $BUILD_PROXY_CONVERTED"; \
    fi && \
    echo "=== 使用 uv sync 安装依赖（无需编译，简化构建）===" && \
    uv sync --verbose && \
    echo "=== uv sync 完成 ===" && \
    # 验证虚拟环境和依赖
    ls -la /app/.venv/bin/ | head -10 && \
    /app/.venv/bin/python --version && \
    /app/.venv/bin/pip list | head -20

# 最终阶段：只复制 uv、Python 和虚拟环境，不包含编译工具
FROM debian:bookworm-slim

# 配置 apt 代理（如果宿主机有代理）
ARG BUILD_PROXY
RUN if [ -n "$BUILD_PROXY" ]; then \
        if echo "$BUILD_PROXY" | grep -q "localhost"; then \
            BUILD_PROXY_CONVERTED=$(echo "$BUILD_PROXY" | sed 's|localhost|host.docker.internal|g'); \
        else \
            BUILD_PROXY_CONVERTED="$BUILD_PROXY"; \
        fi && \
        echo "配置 apt 代理: $BUILD_PROXY_CONVERTED" && \
        echo "Acquire::http::Proxy \"$BUILD_PROXY_CONVERTED\";" > /etc/apt/apt.conf.d/01proxy && \
        echo "Acquire::https::Proxy \"$BUILD_PROXY_CONVERTED\";" >> /etc/apt/apt.conf.d/01proxy; \
    fi

# 配置 apt 重试和超时（与 builder 阶段一致）
RUN echo 'Acquire::Retries "10";' >> /etc/apt/apt.conf.d/99-retries && \
    echo 'Acquire::http::Timeout "120";' >> /etc/apt/apt.conf.d/99-timeout && \
    echo 'Acquire::https::Timeout "120";' >> /etc/apt/apt.conf.d/99-timeout

# 更新 apt 包列表（独立层，可缓存）
RUN apt-get update

# 从builder阶段复制 uv、Python 和虚拟环境
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/.venv /app/.venv

# 安装运行时依赖（独立层，可缓存）
# 注意：不需要编译工具和运行时库（如 libgomp1），因为不使用 llama-cpp-python
RUN apt-get install -y --no-install-recommends \
        ca-certificates || \
     (echo "第一次安装失败，重试..." && \
      apt-get update && \
      apt-get install -y --no-install-recommends --fix-missing \
          ca-certificates) && \
    rm -rf /var/lib/apt/lists/* && \
    echo "运行时依赖安装完成（仅基础库，无编译工具）"

# 设置 PATH：确保 uv 和虚拟环境中的 Python 可用
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"

# 验证 uv、Python 和虚拟环境已正确复制，并修复 Python 链接
RUN /root/.local/bin/uv --version && \
    /root/.local/bin/uv python list && \
    if [ -d "/app/.venv" ]; then \
        echo "检查虚拟环境..." && \
        PYTHON_PATH=$(/root/.local/bin/uv python list | grep "3.11" | head -1 | awk '{print $NF}' || echo "") && \
        if [ -n "$PYTHON_PATH" ] && [ -f "$PYTHON_PATH/bin/python3" ]; then \
            echo "找到 Python 解释器: $PYTHON_PATH/bin/python3" && \
            if [ -f "/app/.venv/bin/python3" ]; then \
                rm -f /app/.venv/bin/python3 && \
                ln -sf "$PYTHON_PATH/bin/python3" /app/.venv/bin/python3 && \
                rm -f /app/.venv/bin/python && \
                ln -sf python3 /app/.venv/bin/python && \
                echo "已修复 Python 链接"; \
            fi && \
            /app/.venv/bin/python --version && \
            echo "虚拟环境验证完成"; \
        else \
            echo "警告: 无法找到 Python 解释器，虚拟环境可能需要重新创建"; \
        fi; \
    else \
        echo "错误: 虚拟环境目录不存在"; \
    fi

# 设置工作目录
WORKDIR /app

# 复制应用代码和配置文件
COPY pyproject.toml ./
COPY *.py ./

# 暴露端口
# 8000: Chat服务器（HTTP API）
EXPOSE 8000

# 启动命令由docker-compose.yml指定

