#!/bin/sh
# 辅助脚本：设置代理环境变量并返回转换后的地址
# 用法: 
#   1. 获取转换后的地址: BUILD_PROXY_CONVERTED=$(docker-set-proxy.sh "$BUILD_PROXY")
#   2. 设置环境变量: . docker-set-proxy.sh "$BUILD_PROXY"
# 注意：只对 localhost 进行替换，其他代理地址（如 squid.corp.redhat.com）保持不变
if [ -n "$1" ]; then
    # 只替换 localhost，其他代理地址保持不变
    if echo "$1" | grep -q "localhost"; then
        BUILD_PROXY_CONVERTED=$(echo "$1" | sed 's|localhost|host.docker.internal|g')
    else
        BUILD_PROXY_CONVERTED="$1"
    fi
    export http_proxy="$BUILD_PROXY_CONVERTED" \
           https_proxy="$BUILD_PROXY_CONVERTED" \
           HTTP_PROXY="$BUILD_PROXY_CONVERTED" \
           HTTPS_PROXY="$BUILD_PROXY_CONVERTED" \
           BUILD_PROXY_CONVERTED="$BUILD_PROXY_CONVERTED"
    # 输出转换后的地址（用于命令调用）
    echo "$BUILD_PROXY_CONVERTED"
fi

