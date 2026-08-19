# Raz

**Local voice interface for Claude Code on Apple Silicon.**

Talk to Claude, and Claude talks back — no cloud APIs, no subscriptions, everything runs on your Mac.

Raz uses [kokoro-mlx](https://github.com/lucasnewman/kokoro-mlx) for text-to-speech and [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) for speech-to-text, both optimized for Apple Silicon. It integrates with Claude Code through MCP tools and a Stop hook for automatic speech.

## Features

- **54 voices** across 10 languages (Spanish, English, French, Italian, Portuguese, Hindi, Japanese, Mandarin, British English)
- **Smart auto-speak** — Claude speaks prose responses automatically, silently skips code blocks and tables
- **Push-to-talk** — hold Right Option (⌥) to speak, release to transcribe and paste
- **Auto-language detection** — switches between Spanish and English voices based on text content
- **10 MCP tools** — full programmatic control from Claude Code (7 TTS + 3 STT)
- **Memory-conscious** — Whisper loads on first use, auto-unloads after 5 min idle
- **Global keyboard shortcut** — toggle Raz on/off with ⌃⌘R from any app

## Requirements

- **Apple Silicon Mac** (M1/M2/M3/M4)
- **Python 3.12** (pinned — kokoro-mlx requirement)
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** CLI
- **[uv](https://docs.astral.sh/uv/)** package manager
- **jq** (`brew install jq`)

## Installation

### 1. Clone and install dependencies

```bash
git clone https://github.com/Mateob6/raz.git
cd raz
uv sync
```

### 2. Install the CLI

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/scripts/raz" ~/.local/bin/raz
chmod +x scripts/raz scripts/start_server.sh scripts/stop_server.sh
```

Make sure `~/.local/bin` is in your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Register the MCP server

```bash
claude mcp add raz -- uv run --directory "$(pwd)" python -m raz.mcp_server
```

### 4. Configure the auto-speak hook

Add to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/raz/hooks/stop_hook.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Replace `/path/to/raz` with the actual path where you cloned the repo.

### 5. Update RAZ_DIR in the CLI

Edit `scripts/raz` and update `RAZ_DIR` to point to your clone location:

```bash
RAZ_DIR="$HOME/path/to/raz"  # Change this
```

### 6. Test it

```bash
raz start    # Starts TTS server + STT daemon
raz say "Hello, I'm Raz"
raz stop
```

## Usage

```bash
# Lifecycle
raz start           # Start Raz (voice + mic)
raz stop            # Stop Raz
raz on / raz off    # Enable/disable Raz
raz status          # Show Raz status

# Speaking
raz say "text"      # Speak text
raz voice af_heart  # Change voice
raz voices          # List all 54 voices
raz mode smart      # Auto-speak mode: smart (default), auto, off
raz speed 1.2       # Speech speed (0.5-2.0)

# Listening
raz listen          # Record, transcribe, copy to clipboard (Ctrl+C to stop)
raz stt start       # Start push-to-talk daemon (Right Option key)
raz stt stop        # Stop daemon

# Fine-grained
raz tts start|stop  # TTS server only
raz stt start|stop  # STT daemon only
```

### Push-to-talk

Hold **Right Option (⌥)** to record, release to transcribe. The transcribed text is automatically pasted into the active app.

- Audio feedback: Tink on start, Pop on stop
- Whisper loads on first use (~3s), auto-unloads after 5 min idle
- Default language: Spanish. Change with `raz stt start en`
- Requires macOS Accessibility permission for your terminal app

### Global keyboard shortcut (optional)

Set up ⌃⌘R to toggle Raz from any app:

```bash
raz shortcut install
```

Then go to **System Settings → Keyboard → Keyboard Shortcuts → Services → General**, find "Activar Raz", and assign ⌃⌘R (Ctrl+Cmd+R).

## Auto-speak modes

| Mode | Behavior |
|------|----------|
| `smart` | Speaks prose, silently skips code blocks and tables **(default)** |
| `auto` | Speaks everything |
| `off` | Nothing auto-speaks. Only explicit `speak()` calls |

## Architecture

```
Claude Code
  ├── MCP tools (10) ──httpx──► localhost:8787 (TTS server, kokoro-mlx)
  │                  ──import──► raz.stt.daemon (STT control)
  ├── Stop hook ──► localhost:8787/auto-speak
  ├── STT daemon (pynput + mlx-whisper) ──► clipboard ──► paste
  └── CLI (raz) ──► unified lifecycle
```

## Voices

54 voices across 10 languages. Some highlights:

| ID | Language | Gender | Notes |
|----|----------|--------|-------|
| `em_alex` | Spanish | ♂ | **Default.** Natural, clear |
| `ef_dora` | Spanish | ♀ | Warm, expressive |
| `af_heart` | English | ♀ | Best quality overall |
| `am_adam` | English | ♂ | Deep, clear |
| `bm_fable` | British | ♂ | Storytelling voice |
| `ff_siwis` | French | ♀ | Clear, natural |
| `if_sara` | Italian | ♀ | Warm, melodic |

Run `raz voices` for the full list.

## Memory usage

| Component | Active | Idle |
|-----------|--------|------|
| TTS server (kokoro-mlx) | ~730 MB | ~730 MB |
| STT daemon (no Whisper) | ~2 MB | ~2 MB |
| STT daemon (Whisper loaded) | ~4 GB | auto-unloads to ~2 MB after 5 min |

The TTS model stays in memory while the server runs. Whisper loads lazily on first push-to-talk and auto-unloads after idle.

## MCP tools

| Tool | Description |
|------|-------------|
| `speak(text, voice?, speed?)` | Speak text aloud |
| `set_voice(voice)` | Change active voice |
| `list_voices()` | List voices by language |
| `set_mode(mode)` | Change auto-speak mode |
| `set_speed(speed)` | Change speech speed |
| `toggle(enabled?)` | Enable/disable TTS |
| `status()` | Full status (TTS + STT) |
| `stt_start(language?)` | Start push-to-talk daemon |
| `stt_stop()` | Stop STT daemon |
| `stt_status()` | STT daemon status |

## License

[MIT](LICENSE)
