import os
import numpy as np

MODEL_LARGE = "mlx-community/whisper-large-v3-turbo"
MODEL_MEDIUM = "mlx-community/whisper-medium-mlx"

MODEL = os.environ.get("RAZ_WHISPER_MODEL", MODEL_LARGE)
SAMPLE_RATE = 16000

_transcribe_fn = None


def _ensure_loaded():
    global _transcribe_fn
    if _transcribe_fn is None:
        import mlx_whisper
        _transcribe_fn = mlx_whisper.transcribe
    return _transcribe_fn


def unload():
    global _transcribe_fn
    _transcribe_fn = None
    try:
        import mlx.core as mx
        mx.clear_cache()
    except Exception:
        pass


def transcribe(audio: np.ndarray, language: str = "es") -> str:
    fn = _ensure_loaded()
    result = fn(audio, path_or_hf_repo=MODEL, language=language,
                temperature=0.0, condition_on_previous_text=False)
    return result.get("text", "").strip()


def listen_and_transcribe(language: str = "es") -> str | None:
    """Record from mic until KeyboardInterrupt, transcribe, return text."""
    import sounddevice as sd

    chunks: list[np.ndarray] = []
    print("Recording (press Ctrl+C to stop)...")
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            while True:
                data, _ = stream.read(SAMPLE_RATE)
                chunks.append(data)
    except KeyboardInterrupt:
        pass

    if not chunks:
        return None

    audio = np.concatenate(chunks).flatten()
    print(f"Transcribing {len(audio) / SAMPLE_RATE:.1f}s...")
    text = transcribe(audio, language=language)
    return text if text else None
