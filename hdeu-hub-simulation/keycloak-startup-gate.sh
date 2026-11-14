#!/bin/sh

set -eu

check_endpoint() {
    endpoint="$1"

    echo "Checking endpoint: $endpoint"

    until curl --fail --silent \
        --output /dev/null \
        --max-time 5 "$endpoint"; do

        echo "Endpoint not ready: $endpoint"
        sleep 2
    done

    echo "Endpoint ready: $endpoint"
}

echo "Waiting for Keycloak readiness..."

check_endpoint "http://keycloak:8080/keycloak/health/ready"

check_endpoint "http://keycloak:8080/keycloak/realms/healthdata/.well-known/openid-configuration"

check_endpoint "http://keycloak:8080/keycloak/realms/healthdata/protocol/openid-connect/certs"

echo "All Keycloak endpoints are ready."
