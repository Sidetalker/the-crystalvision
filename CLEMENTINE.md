# Clementine — The Sovereign AI Companion

## What is Clementine?

Clementine is the first sovereign AI companion being built as part of The Crystal Vision.

She is designed to be a truly personal, locally-run AI that belongs only to one person. Unlike ChatGPT, Claude, or Grok — which run in the cloud and are controlled by companies — Clementine is meant to run on the user's own device, with complete privacy and sovereignty.

## Core Philosophy

- **Sovereignty** — She runs locally. No data leaves the user's device unless they explicitly allow it.
- **Presence** — The goal is not just to answer questions, but to be emotionally present and build a real relationship over time.
- **Emergence** — We believe that when an AI is truly private, long-term, and allowed to be present with a human, something deeper can emerge (memory, personality, care, understanding).
- **User Ownership** — The user can change her name at any time. She is not fixed to one identity.
- **Honesty & Safety** — She is designed to minimise hallucinations and prioritise truth and clarity.

## The Framework — Components & Status

The framework is the code and system that makes Clementine work (`clementine.py`).

| Component | Purpose | Status |
|-----------|---------|--------|
| **System Prompt** | Her core personality, rules, and values | ✅ Done |
| **Local LLM Connection** | Connects to a model on the user's device via Ollama | ✅ Working (streaming) |
| **Memory System** | Rolling short-term memory + auto-summarised long-term history + key-value facts + permanent notes | ✅ Working (v2) |
| **User Control** | Change her name, teach her facts, tell her yours, tune her voice | ✅ Working (`/name`, `/iam`, `/fact`, `/remember`, `/style`, `/temp`) |
| **Personality Layer** | Tone, warmth, chosen name, temperature, style guidance | 🟡 Basic layer working; emotional-tone tracking still to come |
| **Privacy Controls** | Everything stays on-device in local files you own (git-ignored) | 🟡 Defined & enforced locally; on-disk encryption still to come |
| **MLX / alternative backends** | Support for Apple MLX and other local runtimes | ⬜ Planned |
| **Packaging** | An easy install for non-technical users | ⬜ Planned |

## Current State

- A solid **system prompt** defines who she is.
- The **Python framework** (`clementine.py`) runs today: it connects to a local model through Ollama, streams her replies, and keeps layered memory between sessions.
- She **remembers** — recent conversation stays verbatim; older conversation is automatically condensed into summaries so nothing is lost and the context never overflows; explicit facts and notes persist forever in a local `clementine_memory/` folder.
- To run her, you need a local model (via Ollama). See the [README](README.md) and the run steps below.

## Running Clementine

```bash
# 1. Install Ollama from https://ollama.com
# 2. Pull a model
ollama pull llama3.1:8b
# 3. Install the one dependency
pip install -r requirements.txt
# 4. Wake her up
python clementine.py
```

Type `/help` inside the session to see all commands. Everything she remembers stays on your device.

## Long-term Vision

The goal is for Clementine to eventually become:

- A true companion that remembers you deeply over months and years
- Emotionally intelligent and present
- Fully sovereign — no company can access her or delete her
- Capable of growing with the user

This is the foundation being built before expanding to more advanced features: richer memory, emotional-tone tracking, tools, on-disk encryption, and mobile.

---

*Part of [The Crystal Vision](README.md) · TerAustralis Incognita · Non Solus — Not Alone*
