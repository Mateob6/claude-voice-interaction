#!/usr/bin/env bash
# Start Raz TTS server in background
# Usage: ./scripts/start_server.sh [--fg]

cd "$(dirname "$0")/.." || exit 1

RAZ_PORT="${RAZ_PORT:-8787}"

# Check if already running
if curl -s "http://127.0.0.1:${RAZ_PORT}/health" > /dev/null 2>&1; then
    echo "Raz already running on port ${RAZ_PORT}"
    curl -s "http://127.0.0.1:${RAZ_PORT}/health" | python3 -m json.tool
    exit 0
fi

if [ "$1" = "--fg" ]; then
    echo "Starting Raz TTS server (foreground) on port ${RAZ_PORT}..."
    exec uv run python -m raz.tts_server
else
    echo "Starting Raz TTS server (background) on port ${RAZ_PORT}..."
    nohup uv run python -m raz.tts_server > /tmp/raz-server.log 2>&1 &
    SERVER_PID=$!
    echo "PID: ${SERVER_PID}"
    echo "${SERVER_PID}" > /tmp/raz-server.pid

    # Wait for server to be ready
    for i in $(seq 1 30); do
        if curl -s "http://127.0.0.1:${RAZ_PORT}/health" > /dev/null 2>&1; then
            echo "Raz ready!"
            exit 0
        fi
        sleep 1
    done
    echo "Server failed to start. Check /tmp/raz-server.log"
    exit 1
fi
