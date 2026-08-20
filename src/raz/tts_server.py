import asyncio
import os
import threading
from contextlib import asynccontextmanager

import numpy as np
import sounddevice as sd
from fastapi import FastAPI
from pydantic import BaseModel

from raz.text_cleaner import clean_for_speech, should_speak, detect_language

tts_engine = None
current_voice = "em_alex"
current_speed = 1.2
current_mode = "smart"
enabled = True
playback_lock = threading.Lock()

VOICE_MAP_ES = {"f": "ef_dora", "m": "em_alex"}
VOICE_MAP_EN = {"f": "af_heart", "m": "am_adam"}


class SpeakRequest(BaseModel):
    text: str
    voice: str | None = None
    speed: float | None = None
    max_chars: int = 2000


class AutoSpeakRequest(BaseModel):
    text: str


class VoiceRequest(BaseModel):
    voice: str


class ModeRequest(BaseModel):
    mode: str


class SpeedRequest(BaseModel):
    speed: float


def _play_audio(audio: np.ndarray, sample_rate: int = 24000):
    with playback_lock:
        sd.play(audio, samplerate=sample_rate)
        sd.wait()


def _resolve_voice(text: str, voice: str) -> tuple[str, str | None]:
    """Pick voice and language based on text content and current voice."""
    lang = detect_language(text)
    voice_is_spanish = voice.startswith(("ef_", "em_"))
    voice_is_english = voice.startswith(("af_", "am_", "bf_", "bm_"))
    gender = "f" if voice[1] == "f" else "m"

    if lang == "es" and not voice_is_spanish:
        return VOICE_MAP_ES.get(gender, "em_alex"), "es"
    if lang == "en" and voice_is_spanish:
        return VOICE_MAP_EN.get(gender, "af_heart"), None

    tts_lang = "es" if voice_is_spanish else None
    return voice, tts_lang


PID_FILE = "/tmp/raz-server.pid"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts_engine
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    from kokoro_mlx import KokoroTTS
    print("Loading kokoro-mlx model...")
    tts_engine = KokoroTTS.from_pretrained()
    voices = tts_engine.list_voices()
    print(f"Raz ready. {len(voices)} voices, mode={current_mode}, voice={current_voice}")
    yield
    print("Raz shutting down.")
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


app = FastAPI(title="Raz TTS Server", lifespan=lifespan)


async def _synthesize_and_play(text: str, voice: str, speed: float, lang: str | None):
    result = tts_engine.generate(text, voice=voice, speed=speed, language=lang)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _play_audio, result.audio, result.sample_rate)
    try:
        import mlx.core as mx
        mx.clear_cache()
    except Exception:
        pass


@app.post("/speak")
async def speak(req: SpeakRequest):
    if not enabled:
        return {"status": "muted"}

    cleaned = clean_for_speech(req.text, max_chars=req.max_chars)
    if not cleaned:
        return {"status": "empty"}

    voice = req.voice or current_voice
    speed = req.speed if req.speed is not None else current_speed
    voice, lang = _resolve_voice(cleaned, voice)

    await _synthesize_and_play(cleaned, voice, speed, lang)
    return {"status": "ok", "voice": voice, "chars": len(cleaned)}


@app.post("/auto-speak")
async def auto_speak(req: AutoSpeakRequest):
    if not enabled:
        return {"status": "muted"}

    if current_mode == "off":
        return {"status": "off"}

    if current_mode == "smart":
        speak_it, cleaned = should_speak(req.text)
        if not speak_it:
            return {"status": "skipped", "reason": "smart filter"}
    else:
        cleaned = clean_for_speech(req.text)

    if not cleaned:
        return {"status": "empty"}

    voice, lang = _resolve_voice(cleaned, current_voice)
    await _synthesize_and_play(cleaned, voice, current_speed, lang)
    return {"status": "ok", "mode": current_mode, "voice": voice, "chars": len(cleaned)}


@app.get("/voices")
async def voices():
    all_voices = tts_engine.list_voices()
    grouped = {}
    prefixes = {
        "af": "English (American Female)", "am": "English (American Male)",
        "bf": "English (British Female)", "bm": "English (British Male)",
        "ef": "Spanish Female", "em": "Spanish Male",
        "ff": "French Female", "hf": "Hindi Female", "hm": "Hindi Male",
        "if": "Italian Female", "im": "Italian Male",
        "jf": "Japanese Female", "jm": "Japanese Male",
        "pf": "Portuguese Female", "pm": "Portuguese Male",
        "zf": "Mandarin Female", "zm": "Mandarin Male",
    }
    for v in all_voices:
        prefix = v[:2]
        label = prefixes.get(prefix, prefix)
        grouped.setdefault(label, []).append(v)
    return {"current": current_voice, "voices": grouped, "total": len(all_voices)}


@app.post("/voice")
async def set_voice(req: VoiceRequest):
    global current_voice
    all_voices = tts_engine.list_voices()
    if req.voice not in all_voices:
        return {"error": f"Unknown voice: {req.voice}", "available": all_voices}
    current_voice = req.voice
    return {"status": "ok", "voice": current_voice}


@app.post("/mode")
async def set_mode(req: ModeRequest):
    global current_mode
    if req.mode not in ("smart", "auto", "off"):
        return {"error": f"Unknown mode: {req.mode}. Use: smart, auto, off"}
    current_mode = req.mode
    return {"status": "ok", "mode": current_mode}


@app.post("/speed")
async def set_speed(req: SpeedRequest):
    global current_speed
    current_speed = max(0.5, min(2.0, req.speed))
    return {"status": "ok", "speed": current_speed}


@app.post("/toggle")
async def toggle():
    global enabled
    enabled = not enabled
    return {"enabled": enabled, "voice": current_voice}


@app.post("/on")
async def turn_on():
    global enabled
    enabled = True
    return {"enabled": True, "voice": current_voice}


@app.post("/off")
async def turn_off():
    global enabled
    enabled = False
    return {"enabled": False}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "enabled": enabled,
        "mode": current_mode,
        "voice": current_voice,
        "speed": current_speed,
        "model": "kokoro-mlx",
    }


def main():
    import uvicorn
    uvicorn.run("raz.tts_server:app", host="127.0.0.1", port=8787)


if __name__ == "__main__":
    main()
