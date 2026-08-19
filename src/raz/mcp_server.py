"""Raz MCP Server — unified voice control tools for Claude Code.

TTS tools proxy to the Raz HTTP server (localhost:8787).
STT tools control the push-to-talk daemon directly.
"""
import asyncio
import json

import httpx
from mcp.server import MCPServer

from raz.stt.daemon import daemon_status, stop_daemon

RAZ_URL = "http://127.0.0.1:8787"

server = MCPServer(
    name="raz",
    instructions=(
        "Raz is a local voice interface using kokoro-mlx (TTS) and mlx-whisper (STT) on Apple Silicon. "
        "TTS: 54 voices across 10 languages with auto-language detection. "
        "STT: push-to-talk via Right Option key, transcribes and pastes. "
        "Three auto-speak modes: 'smart' (speaks prose, skips code — default), "
        "'auto' (speaks everything), 'off' (nothing auto-speaks). "
        "Use speak() for explicit speech. Use stt_start/stt_stop to control the microphone. "
        "The TTS server must be running (start with `raz start`). "
        "Auto-language detection switches between Spanish and English voices automatically."
    ),
)


async def _request(method: str, path: str, body: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                r = await client.get(f"{RAZ_URL}{path}")
            else:
                r = await client.post(f"{RAZ_URL}{path}", json=body or {})
            return r.json()
    except httpx.ConnectError:
        return {"error": "Raz TTS server not running. Start it with: raz start"}


# --- TTS tools ---


@server.tool()
async def speak(text: str, voice: str | None = None, speed: float | None = None) -> str:
    """Speak text aloud through the speakers. Always works regardless of mode.

    Args:
        text: The text to speak. Markdown is automatically stripped.
        voice: Voice ID (e.g. em_alex, ef_dora, af_heart). Omit to auto-detect language.
        speed: Speed multiplier (0.8=slower, 1.0=normal, 1.2=faster). Omit to use current.
    """
    body: dict = {"text": text}
    if voice:
        body["voice"] = voice
    if speed is not None:
        body["speed"] = speed
    result = await _request("POST", "/speak", body)
    return json.dumps(result, ensure_ascii=False)


@server.tool()
async def set_voice(voice: str) -> str:
    """Change the active TTS voice.

    Args:
        voice: Voice ID. Spanish: em_alex (male), ef_dora (female). English: af_heart (female, best), am_adam (male). British: bm_fable (narrator). 54 voices total across 10 languages.
    """
    result = await _request("POST", "/voice", {"voice": voice})
    return json.dumps(result, ensure_ascii=False)


@server.tool()
async def set_mode(mode: str) -> str:
    """Change the auto-speak mode.

    Args:
        mode: 'smart' (speaks conversational, skips code-heavy — default), 'auto' (speaks everything), 'off' (nothing auto-speaks).
    """
    result = await _request("POST", "/mode", {"mode": mode})
    return json.dumps(result, ensure_ascii=False)


@server.tool()
async def set_speed(speed: float) -> str:
    """Change the speech speed.

    Args:
        speed: Multiplier from 0.5 (very slow) to 2.0 (very fast). Default is 1.0.
    """
    result = await _request("POST", "/speed", {"speed": speed})
    return json.dumps(result, ensure_ascii=False)


@server.tool()
async def list_voices() -> str:
    """List all 54 available TTS voices grouped by language."""
    result = await _request("GET", "/voices")
    return json.dumps(result, ensure_ascii=False)


@server.tool()
async def toggle(enabled: bool | None = None) -> str:
    """Enable or disable TTS entirely.

    Args:
        enabled: True to enable, False to disable. Omit to toggle.
    """
    if enabled is True:
        result = await _request("POST", "/on")
    elif enabled is False:
        result = await _request("POST", "/off")
    else:
        result = await _request("POST", "/toggle")
    return json.dumps(result, ensure_ascii=False)


@server.tool()
async def status() -> str:
    """Check Raz status: active/inactive, voice, mode, speed, mic on/off."""
    tts = await _request("GET", "/health")
    stt = daemon_status(quiet=True)
    result = {
        "status": "active" if tts.get("status") == "ok" else "inactive",
        "enabled": tts.get("enabled", False),
        "voice": tts.get("voice", "unknown"),
        "mode": tts.get("mode", "smart"),
        "speed": tts.get("speed", 1.0),
        "mic": "on" if stt.get("running") else "off",
    }
    if stt.get("pid"):
        result["mic_pid"] = stt["pid"]
    if tts.get("error"):
        result = {"status": "inactive", "mic": "on" if stt.get("running") else "off", "error": tts["error"]}
    return json.dumps(result, ensure_ascii=False)


# --- STT tools ---


@server.tool()
async def stt_start(language: str = "es") -> str:
    """Start the STT push-to-talk daemon. Hold Right Option (⌥) to record, release to transcribe and paste.

    Args:
        language: Language code for transcription. Default 'es' (Spanish). Use 'en' for English.
    """
    current = daemon_status(quiet=True)
    if current["running"]:
        return json.dumps({"status": "already running", "pid": current["pid"]})

    proc = await asyncio.create_subprocess_exec(
        "raz", "stt", "start", language,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode().strip()
    if proc.returncode == 0:
        new_status = daemon_status(quiet=True)
        return json.dumps({"status": "started", **new_status})
    return json.dumps({"status": "error", "output": output})


@server.tool()
async def stt_stop() -> str:
    """Stop the STT push-to-talk daemon."""
    result = stop_daemon(quiet=True)
    return json.dumps(result)


@server.tool()
async def stt_status() -> str:
    """Check STT daemon status: running, PID, hotkey, idle timeout."""
    result = daemon_status(quiet=True)
    return json.dumps(result)


if __name__ == "__main__":
    server.run()
