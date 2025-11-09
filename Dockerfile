# Multi-stage build: first stage uses lightweight base image + uv manages Python
# Uses debian:bookworm-slim as base, uv will automatically manage Python environment
FROM debian:bookworm-slim AS builder

# Configure apt proxy (if host has proxy)
# Note: only replace localhost, other proxy addresses (like squid.corp.redhat.com) remain unchanged
ARG BUILD_PROXY
RUN if [ -n "$BUILD_PROXY" ]; then \
        if echo "$BUILD_PROXY" | grep -q "localhost"; then \
            BUILD_PROXY_CONVERTED=$(echo "$BUILD_PROXY" | sed 's|localhost|host.docker.internal|g'); \
        else \
            BUILD_PROXY_CONVERTED="$BUILD_PROXY"; \
        fi && \
        echo "Configuring apt proxy: $BUILD_PROXY_CONVERTED" && \
        echo "Acquire::http::Proxy \"$BUILD_PROXY_CONVERTED\";" > /etc/apt/apt.conf.d/01proxy && \
        echo "Acquire::https::Proxy \"$BUILD_PROXY_CONVERTED\";" >> /etc/apt/apt.conf.d/01proxy; \
    fi

# Configure apt retry and timeout (independent layer, cacheable)
RUN echo 'Acquire::Retries "10";' >> /etc/apt/apt.conf.d/99-retries && \
    echo 'Acquire::http::Timeout "120";' >> /etc/apt/apt.conf.d/99-timeout && \
    echo 'Acquire::https::Timeout "120";' >> /etc/apt/apt.conf.d/99-timeout

# Update package list (independent layer, cacheable)
RUN apt-get update

# Install basic tools (no compilation tools needed, as we don't need to compile llama-cpp-python)
RUN apt-get install -y --no-install-recommends --fix-missing \
    ca-certificates \
    curl

# Clean apt cache (independent layer, cacheable)
RUN rm -rf /var/lib/apt/lists/*

# Copy proxy setup helper script
COPY docker-set-proxy.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-set-proxy.sh

# Install uv (independent layer, cacheable)
ARG BUILD_PROXY
RUN if [ -n "$BUILD_PROXY" ]; then \
        BUILD_PROXY_CONVERTED=$(/usr/local/bin/docker-set-proxy.sh "$BUILD_PROXY") && \
        echo "Using proxy to download uv: $BUILD_PROXY_CONVERTED" && \
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY || true && \
        export http_proxy="$BUILD_PROXY_CONVERTED" https_proxy="$BUILD_PROXY_CONVERTED" HTTP_PROXY="$BUILD_PROXY_CONVERTED" HTTPS_PROXY="$BUILD_PROXY_CONVERTED" && \
        curl --proxy "$BUILD_PROXY_CONVERTED" -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh && \
        sh /tmp/uv-install.sh && \
        rm -f /tmp/uv-install.sh; \
    else \
        echo "Not using proxy to download uv"; \
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY || true && \
        curl -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh && \
        sh /tmp/uv-install.sh && \
        rm -f /tmp/uv-install.sh; \
    fi

# Verify uv installation (independent layer, cacheable)
RUN export PATH="/root/.local/bin:$PATH" && \
    /root/.local/bin/uv --version

# Copy project files (copy config files first, convenient for uv sync)
WORKDIR /app
COPY pyproject.toml ./

# Install Python (independent layer, cacheable)
ARG BUILD_PROXY
RUN export PATH="/root/.local/bin:$PATH" && \
    if [ -n "$BUILD_PROXY" ]; then \
        BUILD_PROXY_CONVERTED=$(/usr/local/bin/docker-set-proxy.sh "$BUILD_PROXY") && \
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY || true && \
        export http_proxy="$BUILD_PROXY_CONVERTED" https_proxy="$BUILD_PROXY_CONVERTED" HTTP_PROXY="$BUILD_PROXY_CONVERTED" HTTPS_PROXY="$BUILD_PROXY_CONVERTED"; \
    fi && \
    echo "Installing Python 3.11 using uv..." && \
    uv python install 3.11 && \
    uv python list

# Use uv sync to create virtual environment and install dependencies (independent layer, only re-executes when dependencies change)
ARG BUILD_PROXY
RUN export PATH="/root/.local/bin:$PATH" && \
    if [ -n "$BUILD_PROXY" ]; then \
        BUILD_PROXY_CONVERTED=$(/usr/local/bin/docker-set-proxy.sh "$BUILD_PROXY") && \
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY || true && \
        export http_proxy="$BUILD_PROXY_CONVERTED" https_proxy="$BUILD_PROXY_CONVERTED" HTTP_PROXY="$BUILD_PROXY_CONVERTED" HTTPS_PROXY="$BUILD_PROXY_CONVERTED" && \
        echo "Configured uv proxy: $BUILD_PROXY_CONVERTED"; \
    fi && \
    echo "=== Installing dependencies using uv sync (no compilation needed, simplified build) ===" && \
    uv sync --verbose && \
    echo "=== uv sync complete ===" && \
    # Verify virtual environment and dependencies
    ls -la /app/.venv/bin/ | head -10 && \
    /app/.venv/bin/python --version && \
    /app/.venv/bin/pip list | head -20

# Final stage: only copy uv, Python and virtual environment, exclude compilation tools
FROM debian:bookworm-slim

# Configure apt proxy (if host has proxy)
ARG BUILD_PROXY
RUN if [ -n "$BUILD_PROXY" ]; then \
        if echo "$BUILD_PROXY" | grep -q "localhost"; then \
            BUILD_PROXY_CONVERTED=$(echo "$BUILD_PROXY" | sed 's|localhost|host.docker.internal|g'); \
        else \
            BUILD_PROXY_CONVERTED="$BUILD_PROXY"; \
        fi && \
        echo "Configuring apt proxy: $BUILD_PROXY_CONVERTED" && \
        echo "Acquire::http::Proxy \"$BUILD_PROXY_CONVERTED\";" > /etc/apt/apt.conf.d/01proxy && \
        echo "Acquire::https::Proxy \"$BUILD_PROXY_CONVERTED\";" >> /etc/apt/apt.conf.d/01proxy; \
    fi

# Configure apt retry and timeout (consistent with builder stage)
RUN echo 'Acquire::Retries "10";' >> /etc/apt/apt.conf.d/99-retries && \
    echo 'Acquire::http::Timeout "120";' >> /etc/apt/apt.conf.d/99-timeout && \
    echo 'Acquire::https::Timeout "120";' >> /etc/apt/apt.conf.d/99-timeout

# Update apt package list (independent layer, cacheable)
RUN apt-get update

# Copy uv, Python and virtual environment from builder stage
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/.venv /app/.venv

# Install runtime dependencies (independent layer, cacheable)
# Note: no compilation tools and runtime libraries (like libgomp1) needed, as we don't use llama-cpp-python
RUN apt-get install -y --no-install-recommends \
        ca-certificates || \
     (echo "First installation failed, retrying..." && \
      apt-get update && \
      apt-get install -y --no-install-recommends --fix-missing \
          ca-certificates) && \
    rm -rf /var/lib/apt/lists/* && \
    echo "Runtime dependencies installed (basic libraries only, no compilation tools)"

# Set PATH: ensure uv and Python in virtual environment are available
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"

# Verify uv, Python and virtual environment are correctly copied, and fix Python links
RUN /root/.local/bin/uv --version && \
    /root/.local/bin/uv python list && \
    if [ -d "/app/.venv" ]; then \
        echo "Checking virtual environment..." && \
        PYTHON_PATH=$(/root/.local/bin/uv python list | grep "3.11" | head -1 | awk '{print $NF}' || echo "") && \
        if [ -n "$PYTHON_PATH" ] && [ -f "$PYTHON_PATH/bin/python3" ]; then \
            echo "Found Python interpreter: $PYTHON_PATH/bin/python3" && \
            if [ -f "/app/.venv/bin/python3" ]; then \
                rm -f /app/.venv/bin/python3 && \
                ln -sf "$PYTHON_PATH/bin/python3" /app/.venv/bin/python3 && \
                rm -f /app/.venv/bin/python && \
                ln -sf python3 /app/.venv/bin/python && \
                echo "Fixed Python links"; \
            fi && \
            /app/.venv/bin/python --version && \
            echo "Virtual environment verification complete"; \
        else \
            echo "Warning: Cannot find Python interpreter, virtual environment may need to be recreated"; \
        fi; \
    else \
        echo "Error: Virtual environment directory does not exist"; \
    fi

# Set working directory
WORKDIR /app

# Copy application code and configuration files
COPY pyproject.toml ./
COPY *.py ./

# Expose port
# 8000: Chat server (HTTP API)
EXPOSE 8000

# Startup command specified by docker-compose.yml

