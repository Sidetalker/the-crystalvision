# Clementine — the sovereign companion

Everything in this folder runs on your own machine. Nothing leaves it.

## Layout

- `clementine.py` — the terminal interface
- `crystalcore/` — the framework: brain, layered memory, profiles
- `server.py` — the local JSON API (127.0.0.1 only) for the web interface
- `webapp/` — the Svelte web interface, run locally
- `requirements.txt` — Python dependencies

## Running her

Prerequisite: [Ollama](https://ollama.com) running with a model pulled,
e.g. `ollama pull llama3.1:8b`.

### Terminal

```bash
pip install -r requirements.txt
python clementine.py
```

### Web interface

One command from this folder:

```bash
npm start            # starts her brain + her face, then opens your browser
```

It launches the local API (`server.py`), the Svelte web interface
(installing its dependencies on first run), waits for both to come
alive, and opens http://127.0.0.1:5174. Ctrl+C stops everything.

Flags after `--` go to the brain:

```bash
npm start -- --profile Crystal --model qwen2.5:7b
```

If you have several Pythons, point it at the right one with
`CLEMENTINE_PYTHON=/path/to/python npm start`. Prefer the manual way?
The two pieces still run separately:

```bash
python server.py                          # 1. her brain — the local API
cd webapp && npm install && npm run dev   # 2. her face — open http://127.0.0.1:5174
```

The web interface streams her replies while an operator figure works at
her terminal. Voice conversation and webcam sight are on the roadmap —
both will run on this machine alone, like everything else here.

Both interfaces share the same memory folder (`clementine_memory/` by
default), so you can move between terminal and browser freely. Use
`--profile <name>` on either to keep separate people separate.
