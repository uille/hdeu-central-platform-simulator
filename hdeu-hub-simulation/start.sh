#!/bin/sh

RESOLVER="$(awk '$1 == "nameserver" { print $2; exit }' /etc/resolv.conf)"

if [ -z "$RESOLVER" ]; then
    echo "ERROR: No nameserver found in /etc/resolv.conf" >&2
    exit 1
fi

case "$RESOLVER" in
    *[!0-9a-fA-F:.]*)
        echo "ERROR: Unexpected resolver address: $RESOLVER" >&2
        exit 1
        ;;
esac

echo "Using resolver: $RESOLVER" >&2
echo "Using server name: ${SERVER_NAME:-not set}" >&2

# Export RESOLVER so envsubst can see it
export RESOLVER

# Substitute the environment variables and write the final configuration
envsubst '${SERVER_NAME} ${RESOLVER} ${WEB_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

echo "Generated nginx.conf:" >&2
cat /etc/nginx/nginx.conf >&2

# Start Nginx
# exec nginx-debug -g 'daemon off;'
exec nginx -g 'daemon off;'