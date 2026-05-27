#!/bin/bash
ROUTES_DIR="/etc/nginx/routes"
STREAMS_DIR="/etc/nginx/streams"
CONFIG_FILE="/etc/nginx/config.json"
RESOLVER_IP=""
EMAIL=""

mkdir -p "/etc/nginx";
mkdir -p "$STREAMS_DIR";

test -f "$CONFIG_FILE" || { echo "Config file not found at $CONFIG_FILE"; exit 1; }
test "$(jq empty "$CONFIG_FILE" 2>&1)" == "" || { echo "Invalid JSON config file!"; exit 1; }

RESOLVER_IP=$(jq -r '.resolver' "$CONFIG_FILE")
EMAIL=$(jq -r '.email' "$CONFIG_FILE")


[ -z "$RESOLVER_IP" ] && { echo "Resolver IP not found in config!"; exit 1; }
[ -z "$EMAIL" ] && { echo "Email not found in config!"; exit 1; }


function getRouteConfig() {
    cat route.template | awk -v host="$1" -v upstream="$2"  -v resolver="$RESOLVER_IP" '
    {
        gsub(/HOST/, host);
        gsub(/UPSTREAM/, upstream);
        gsub(/RESOLVER/, resolver);
        print;
    }'
}

function getStreamConfig() {
    cat stream.template | awk -v port="$1" -v upstream="$2" -v resolver="$RESOLVER_IP" '
    {
        gsub(/PORT/, port);
        gsub(/UPSTREAM/, upstream);
        gsub(/RESOLVER/, resolver);
        print;
    }'
}

function createRoutes() {
    jq -r '.routes[] | select(.type == null or .type == "http") | "\(.host) \(.upstream)"' $CONFIG_FILE | while read -r host upstream; do
        test -f "$ROUTES_DIR/$host.conf" && { echo "Route for $host already exists, skipping..."; continue; }
        echo "Creating route for $host -> $upstream";
        getRouteConfig "$host" "$upstream" > "$ROUTES_DIR/$host.conf";
    done;
}

function createStreams() {
    jq -r '.routes[] | select(.type == "tcp") | "\(.host) \(.upstream)"' $CONFIG_FILE | while read -r host upstream; do
        test -f "$STREAMS_DIR/$host.conf" && { echo "Stream for $host already exists, skipping..."; continue; }
        port="${upstream##*:}"
        echo "Creating stream for $host on :$port -> $upstream";
        getStreamConfig "$port" "$upstream" > "$STREAMS_DIR/$host.conf";
    done;
}

function getCerts() {
    jq -r '.routes[] | select(.type == null or .type == "http") | "\(.host) \(.upstream)"' $CONFIG_FILE | while read -r host upstream; do
        echo "Getting cert for $host";
        certbot --nginx --agree-tos --non-interactive -m $EMAIL -d $host || {
            echo "Failed to get cert for $host";
            continue;
        }
        nginx -s reload;
        echo "Successfully obtained cert for $host";
    done;
}

function renewCerts() {
    echo "Attempting to renew certificates...";
    certbot renew --nginx --non-interactive && nginx -s reload;
}


function main() {
    createRoutes;
    createStreams;
    nginx;
    sleep 5;

    while true; do
        getCerts;
        renewCerts;
        echo "Sleeping for 24 hours before next cert renewal attempt.";
        sleep 86400;
    done
}

main


