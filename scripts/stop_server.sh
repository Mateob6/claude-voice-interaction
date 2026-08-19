#!/usr/bin/env bash
# Stop Raz TTS server

if [ -f /tmp/raz-server.pid ]; then
    PID=$(cat /tmp/raz-server.pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "Raz stopped (PID: $PID)"
        rm -f /tmp/raz-server.pid
    else
        echo "Raz not running (stale PID file)"
        rm -f /tmp/raz-server.pid
    fi
else
    echo "No PID file found. Trying to find process..."
    pkill -f "raz.tts_server" && echo "Raz stopped" || echo "Raz not running"
fi
