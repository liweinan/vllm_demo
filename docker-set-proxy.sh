#!/bin/sh
# Helper script: set proxy environment variables and return converted address
# Usage: 
#   1. Get converted address: BUILD_PROXY_CONVERTED=$(docker-set-proxy.sh "$BUILD_PROXY")
#   2. Set environment variables: . docker-set-proxy.sh "$BUILD_PROXY"
# Note: Only replace localhost, other proxy addresses (like squid.corp.redhat.com) remain unchanged
if [ -n "$1" ]; then
    # Only replace localhost, other proxy addresses remain unchanged
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
    # Output converted address (for command calls)
    echo "$BUILD_PROXY_CONVERTED"
fi

