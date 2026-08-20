#!/usr/bin/env bash
# Stop Raz TTS server

_wait_for_death() {
    local pid=$1
    for i in $(seq 1 30); do
        kill -0 "$pid" 2>/dev/null || return 0
        sleep 0.1
    done
    kill -9 "$pid" 2>/dev/null
    return 0
}

if [ -f /tmp/raz-server.pid ]; then
    PID=$(cat /tmp/raz-server.pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        _wait_for_death "$PID"
        echo "Raz stopped (PID: $PID)"
    else
        echo "Raz not running (stale PID file)"
    fi
    rm -f /tmp/raz-server.pid
else
    echo "No PID file found. Trying to find process..."
    pkill -f "raz.tts_server" && echo "Raz stopped" || echo "Raz not running"
fi

# Clean up any orphaned uv wrappers
pkill -f "uv run python -m raz.tts_server" 2>/dev/null
pkill -f "uv run python.*raz.tts_server" 2>/dev/null
