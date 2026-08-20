# Raz — Voice Interface for Claude Code

Talk to Claude Code with your voice. Claude talks back. Everything runs locally on your Mac — no cloud APIs, no subscriptions, no data leaves your machine.

**Raz** (from Aramaic רָז, "mystery revealed") gives Claude Code a voice and ears using [kokoro-mlx](https://github.com/lucasnewman/kokoro-mlx) for speech and [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) for listening, both optimized for Apple Silicon.

## How It Works

```
You speak (hold Right Option key) ──► Whisper transcribes ──► text goes to Claude
Claude responds ──► auto-speak reads the response aloud through your speakers
```

That's it. When Raz is on, you have a voice conversation with Claude. Code blocks and tables are silently skipped — only prose is spoken.

## What You Need

| Requirement | Why |
|---|---|
| **Apple Silicon Mac** (M1/M2/M3/M4) | kokoro-mlx and mlx-whisper only run on Apple Silicon |
| **Python 3.12** | Pinned version — kokoro-mlx requires it |
| **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** | The CLI this integrates with |
| **[uv](https://docs.astral.sh/uv/)** | Python package manager (handles everything) |
| **jq** | JSON processing for the CLI (`brew install jq`) |

## Setup

The whole setup takes about 5 minutes. Every step is copy-paste.

### Step 1: Clone and install

```bash
git clone https://github.com/Mateob6/claude-voice-interaction.git
cd claude-voice-interaction
uv sync
```

This downloads the code and installs all Python dependencies (kokoro-mlx, mlx-whisper, FastAPI, pynput, etc.) in an isolated virtual environment.

### Step 2: Install the CLI

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/scripts/raz" ~/.local/bin/raz
chmod +x scripts/raz scripts/start_server.sh scripts/stop_server.sh
```

Make sure `~/.local/bin` is in your PATH. If it's not:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify it works:

```bash
raz help
```

### Step 3: Register the MCP server

This lets Claude Code control Raz through 10 built-in tools (speak, change voice, start/stop listening, etc.):

```bash
claude mcp add raz -- uv run --directory "$(pwd)" python -m raz.mcp_server
```

### Step 4: Set up auto-speak

This hook makes Claude's responses automatically spoken aloud. Add it to your Claude Code settings:

```bash
cat ~/.claude/settings.json
```

If the file exists, add the `hooks` section. If it doesn't, create it:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/FULL/PATH/TO/claude-voice-interaction/hooks/stop_hook.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**Important:** Replace `/FULL/PATH/TO/claude-voice-interaction` with the actual path where you cloned the repo. You can get it with `pwd` while inside the project directory.

### Step 5: First run

```bash
raz start
```

This starts two things:
- The **TTS server** (text-to-speech) — loads the kokoro-mlx model (~10 seconds first time)
- The **STT daemon** (speech-to-text) — listens for the Right Option key

You should see:

```
=== Starting Raz ===
Starting Raz TTS server (background) on port 8787...
Raz ready!
Starting STT daemon (lang=es)...
Loading Whisper model. ready!
PID: 12345
```

Test it:

```bash
raz say "Hello, I can speak now"
```

If you hear the voice, everything is working. Stop Raz with:

```bash
raz stop
```

## Using Raz

### Start a voice session

```bash
raz start    # start voice + mic
raz stop     # stop everything
raz status   # check what's running
```

### Talk to Claude (push-to-talk)

1. Hold **Right Option (⌥)** on your keyboard
2. Speak your message
3. Release the key
4. Your words are transcribed and pasted into Claude Code

You'll hear a **Tink** sound when recording starts and a **Pop** when it stops.

**First time:** macOS will ask for Accessibility permission for your terminal app. Grant it — pynput needs it to detect the hotkey globally.

**First press:** The Whisper model loads on first use (~3 seconds). After that, transcription is near-instant. The model auto-unloads after 5 minutes of idle to free memory.

### Change the voice

```bash
raz voice af_heart    # switch to English female (best quality)
raz voice em_alex     # switch to Spanish male (default)
raz voice bm_fable    # switch to British storyteller
raz voices            # see all 54 voices
```

### Adjust speed

```bash
raz speed 1.5    # faster
raz speed 0.8    # slower
raz speed 1.0    # normal
```

### One-shot transcription

Record audio and copy the transcription to your clipboard (without the daemon):

```bash
raz listen         # Spanish (default)
raz listen en      # English
# Press Ctrl+C when done speaking
```

### Set up a keyboard shortcut (optional)

Toggle Raz on/off from any app with a global keyboard shortcut:

```bash
raz shortcut install
```

Then assign the shortcut:
1. **System Settings → Keyboard → Keyboard Shortcuts → Services → General**
2. Find **"Activar Raz"**
3. Click "Add Shortcut" and press your preferred key combo (e.g., **⌃⌘R**)

Now that key combo toggles Raz on/off from anywhere, with a macOS notification.

## Voices

54 voices across 10 languages. Highlights:

| ID | Language | Gender | Character |
|---|---|---|---|
| `em_alex` | Spanish | ♂ | **Default.** Natural, clear |
| `ef_dora` | Spanish | ♀ | Warm, expressive |
| `af_heart` | English | ♀ | Best overall quality |
| `am_adam` | English | ♂ | Deep, clear |
| `bm_fable` | British | ♂ | Storytelling voice |
| `ff_siwis` | French | ♀ | Clear, natural |
| `if_sara` | Italian | ♀ | Warm, melodic |
| `jf_alpha` | Japanese | ♀ | Standard |
| `zf_xiaoxiao` | Mandarin | ♀ | Energetic |
| `pf_dora` | Portuguese | ♀ | Natural |

Full list: `raz voices`

## Configuration

### Auto-speak modes

| Mode | What happens |
|---|---|
| `smart` | Speaks prose, silently skips code and tables **(default)** |
| `auto` | Speaks everything |
| `off` | Nothing auto-speaks — only explicit `speak()` MCP calls |

```bash
raz mode smart    # recommended
raz mode auto     # hear everything
raz mode off      # silent, use speak() when needed
```

### Language detection

Raz auto-detects whether text is Spanish or English and switches voices accordingly. If you set `em_alex` (Spanish male) and Claude responds in English, Raz automatically switches to `am_adam` (English male) for that response, then back.

### STT language

The push-to-talk daemon defaults to Spanish. Start it with a different language:

```bash
raz stt start en    # English
raz stt start es    # Spanish (default)
```

## Architecture

```
Claude Code
  ├── MCP tools (10) ──► localhost:8787 (TTS: kokoro-mlx)
  │                  ──► raz.stt.daemon  (STT: control)
  ├── Stop hook ──► localhost:8787/auto-speak
  ├── STT daemon (pynput + mlx-whisper) ──► clipboard ──► paste
  └── CLI (raz) ──► unified lifecycle
```

| Component | What it does | Memory |
|---|---|---|
| TTS server | Speaks text through speakers (FastAPI + kokoro-mlx) | ~730 MB |
| STT daemon | Listens for Right Option, transcribes with Whisper | ~2 MB idle, ~4 GB when Whisper loaded |
| MCP server | 10 tools for Claude Code to control Raz | runs inside Claude Code |
| Stop hook | Captures Claude's response and sends it to TTS | bash script, no memory |

The STT daemon lazy-loads Whisper on first keypress and auto-unloads after 5 minutes of idle to free ~4 GB of memory.

## Troubleshooting

### "Right Option doesn't do anything"

Your terminal app needs **Accessibility permission**. Go to System Settings → Privacy & Security → Accessibility, and add your terminal (iTerm2, Terminal.app, etc.).

### "raz start hangs on 'Loading Whisper model'"

First run downloads the Whisper model (~800 MB). Check your internet connection. The model is cached after the first download.

### "Port 8787 already in use"

Another instance of Raz is running. Kill it:

```bash
raz stop
# If that doesn't work:
pkill -f "raz.tts_server"
```

### "Daemon won't stop"

```bash
pkill -f "run_daemon"
```

### "No sound output"

Check that your Mac's audio output is set correctly (System Settings → Sound). Raz plays through the default output device.

## CLI Reference

```bash
raz start           # Start Raz (voice + mic)
raz stop            # Stop Raz
raz on / raz off    # Enable/disable Raz
raz status          # Show Raz status

raz say "text"      # Speak text
raz listen [lang]   # Record → transcribe → clipboard
raz voice NAME      # Change voice
raz voices          # List all 54 voices
raz mode MODE       # smart | auto | off
raz speed N         # 0.5–2.0

raz stt start|stop  # Mic only
raz tts start|stop  # Voice only
raz shortcut install|remove  # Keyboard shortcut
```

## MCP Tools

When registered as an MCP server, Claude Code gets these 10 tools:

| Tool | What it does |
|---|---|
| `speak(text, voice?, speed?)` | Speak text aloud |
| `set_voice(voice)` | Change voice |
| `list_voices()` | List all voices |
| `set_mode(mode)` | Change auto-speak mode |
| `set_speed(speed)` | Change speech speed |
| `toggle(enabled?)` | Enable/disable TTS |
| `status()` | Check Raz status |
| `stt_start(language?)` | Start push-to-talk |
| `stt_stop()` | Stop push-to-talk |
| `stt_status()` | Check mic status |

## License

[MIT](LICENSE)
