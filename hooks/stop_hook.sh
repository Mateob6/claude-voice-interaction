#!/usr/bin/env bash
# Raz Stop Hook — auto-speak Claude's responses via kokoro-mlx TTS server
# Receives JSON on stdin with last_assistant_message field
# POSTs to Raz TTS server (localhost:8787) in background, non-blocking

RAZ_PORT="${RAZ_PORT:-8787}"
RAZ_URL="http://127.0.0.1:${RAZ_PORT}/auto-speak"

INPUT=$(cat)

MESSAGE=$(echo "$INPUT" | jq -r '.last_assistant_message // empty')

if [ -z "$MESSAGE" ]; then
    exit 0
fi

# POST to TTS server in background so we don't block Claude Code
curl -s -X POST "$RAZ_URL" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg text "$MESSAGE" '{"text": $text}')" \
    > /dev/null 2>&1 &

exit 0
