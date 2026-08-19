"""
Raz STT Daemon — push-to-talk voice input for any app.
Hold Right Option (⌥) to record, release to transcribe and paste.
Auto-unloads Whisper after 5 min idle to free ~4 GB of memory.
"""
import os
import signal
import subprocess
import sys
import time
import threading

from pynput import keyboard

from raz.stt.engine import transcribe, unload, _ensure_loaded
from raz.stt.recorder import Recorder

PID_FILE = "/tmp/raz-daemon.pid"
LOG_FILE = "/tmp/raz-daemon.log"
HOTKEY = keyboard.Key.alt_r
BEEP_START = "/System/Library/Sounds/Tink.aiff"
BEEP_END = "/System/Library/Sounds/Pop.aiff"
IDLE_TIMEOUT = 300  # 5 minutes

recorder = Recorder()
language = "es"
last_activity = 0.0
model_loaded = False


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except OSError:
        pass


def _beep(sound: str):
    try:
        subprocess.Popen(
            ["afplay", sound],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


def _paste_text(text: str):
    env = os.environ.copy()
    env["LANG"] = "en_US.UTF-8"
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True, env=env)
    time.sleep(0.05)
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to keystroke "v" using command down',
    ], check=True)


def _idle_monitor():
    """Background thread that unloads Whisper after IDLE_TIMEOUT seconds of no activity."""
    global model_loaded
    while True:
        time.sleep(60)
        if model_loaded and last_activity > 0 and (time.time() - last_activity) > IDLE_TIMEOUT:
            _log(f"Idle {IDLE_TIMEOUT}s — unloading Whisper to free memory")
            unload()
            model_loaded = False


def on_press(key):
    if key == HOTKEY and not recorder.is_recording:
        _beep(BEEP_START)
        recorder.start()
        _log("Recording...")


def on_release(key):
    global last_activity, model_loaded
    if key == HOTKEY and recorder.is_recording:
        audio = recorder.stop()
        _beep(BEEP_END)

        if len(audio) < 4800:
            _log("Too short, skipped")
            return

        if not model_loaded:
            _log("Loading Whisper model...")
            _ensure_loaded()
            model_loaded = True
            _log("Model ready")

        last_activity = time.time()
        _log(f"Transcribing {len(audio)/16000:.1f}s of audio...")
        try:
            text = transcribe(audio, language=language)
        except Exception as e:
            _log(f"Transcription error: {e}")
            return

        if text:
            _log(f"Result: {text}")
            _paste_text(text)
        else:
            _log("Empty transcription")


def run_daemon(lang: str = "es"):
    """Run the daemon in foreground. Use nohup/& in the CLI for background."""
    global language, last_activity, model_loaded
    language = lang

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    _log(f"Raz STT daemon started (lang={language}, hotkey=Right Option, idle={IDLE_TIMEOUT}s)")

    # Lazy loading — don't pre-load Whisper, wait for first keypress
    _log("Listening for hotkey (Whisper loads on first use)...")
    model_loaded = False
    last_activity = time.time()

    # Start idle monitor thread
    monitor = threading.Thread(target=_idle_monitor, daemon=True)
    monitor.start()

    def handle_signal(signum, frame):
        _log("Daemon stopping")
        if model_loaded:
            unload()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


def stop_daemon(quiet: bool = False) -> dict:
    if not os.path.exists(PID_FILE):
        if not quiet:
            print("Raz daemon not running.")
        return {"stopped": False, "reason": "not running"}
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        if not quiet:
            print(f"Raz daemon stopped (PID: {pid})")
        result = {"stopped": True, "pid": pid}
    except ProcessLookupError:
        if not quiet:
            print("Raz daemon not running (stale PID).")
        result = {"stopped": False, "reason": "stale PID", "pid": pid}
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    return result


def daemon_status(quiet: bool = False) -> dict:
    if not os.path.exists(PID_FILE):
        if not quiet:
            print("Raz daemon: not running")
        return {"running": False}
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, 0)
        if not quiet:
            print(f"Raz daemon: running (PID: {pid}, hotkey: Right Option ⌥, idle timeout: {IDLE_TIMEOUT}s)")
        return {"running": True, "pid": pid, "hotkey": "Right Option ⌥", "idle_timeout": IDLE_TIMEOUT}
    except ProcessLookupError:
        if not quiet:
            print("Raz daemon: not running (stale PID)")
        os.remove(PID_FILE)
        return {"running": False, "reason": "stale PID"}


if __name__ == "__main__":
    run_daemon()
