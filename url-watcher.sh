#!/bin/bash
# url-watcher.sh — logs/tunnel.log 를 폴링해서 server-url.txt 를 최신 trycloudflare URL 로 유지.
# vibeserver-install.sh 가 nohup 으로 띄우고, 종료 시 kill.

set -e
cd "$(dirname "$0")"
mkdir -p logs

LAST=""
while true; do
    URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' logs/tunnel.log 2>/dev/null | head -1 || true)"
    if [ -n "$URL" ] && [ "$URL" != "$LAST" ]; then
        echo "$URL" > server-url.txt
        echo "$(date -Iseconds)  $URL" >> logs/url-watcher.log
        LAST="$URL"
    fi
    sleep 5
done
