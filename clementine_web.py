"""
Clementine — local web interface

Runs only on your own machine (bound to 127.0.0.1, never exposed).
Shares the same brain and memory folder as the terminal version, so you
can switch between them freely. Nothing leaves your device.

    pip install -r requirements.txt
    python clementine_web.py            # then open http://127.0.0.1:5000
"""

import argparse

from flask import Flask, jsonify, render_template_string, request

from clementine import Clementine

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ name }} — sovereign companion</title>
<style>
  :root{--bg:#000004;--ink:#E9EBF4;--muted:#A6ACC4;--purple:#A78BFA;
        --card:#07070F;--line:rgba(233,235,244,.12)}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;
       display:flex;flex-direction:column;height:100vh}
  header{padding:14px 20px;border-bottom:1px solid var(--line);
         display:flex;justify-content:space-between;align-items:center}
  header b{color:var(--purple)}
  header small{color:var(--muted)}
  main{flex:1;display:flex;min-height:0}
  #chatcol{flex:2;display:flex;flex-direction:column;min-width:0}
  #log{flex:1;overflow-y:auto;padding:20px}
  .msg{max-width:70ch;margin:0 0 14px;padding:10px 14px;border-radius:12px;
       white-space:pre-wrap;line-height:1.55}
  .you{background:#141420;margin-left:auto}
  .her{background:var(--card);border:1px solid var(--line)}
  .her b{color:var(--purple)}
  form#send{display:flex;gap:10px;padding:14px 20px;border-top:1px solid var(--line)}
  input,button,textarea{font:inherit;color:var(--ink);background:#0D0D18;
       border:1px solid var(--line);border-radius:8px;padding:10px}
  input{flex:1}
  button{cursor:pointer;background:var(--purple);color:#050208;border:none;
         font-weight:600;padding:10px 18px}
  button.small{padding:2px 9px;font-weight:400;background:transparent;
               color:var(--muted);border:1px solid var(--line)}
  aside{flex:1;max-width:340px;border-left:1px solid var(--line);
        padding:16px;overflow-y:auto}
  aside h2{font-size:.95rem;color:var(--muted);margin-bottom:10px;
           text-transform:uppercase;letter-spacing:.08em}
  .mem{display:flex;justify-content:space-between;gap:8px;align-items:start;
       padding:8px 0;border-bottom:1px solid var(--line);font-size:.92rem}
  .mem .tags{color:var(--purple);font-size:.8rem}
  #teach{display:flex;flex-direction:column;gap:8px;margin-top:14px}
  footer{padding:10px 20px;color:var(--muted);font-size:.8rem;
         border-top:1px solid var(--line)}
  @media(max-width:760px){aside{display:none}}
</style>
</head>
<body>
<header><div><b>{{ name }}</b> · sovereign companion</div>
<small>local only · 127.0.0.1</small></header>
<main>
  <div id="chatcol">
    <div id="log"></div>
    <form id="send">
      <input id="box" autocomplete="off" placeholder="Say something…" autofocus>
      <button>Send</button>
    </form>
  </div>
  <aside>
    <h2>Her memory</h2>
    <div id="mems"></div>
    <form id="teach">
      <input id="teachtext" placeholder="Teach her something… (#tags ok)">
      <input id="teachkey" placeholder="Optional fact key (e.g. birthday)">
      <button>Remember</button>
    </form>
  </aside>
</main>
<footer>Everything on this page stays on your device. Her memory lives in a
local folder you own. Non solus.</footer>
<script>
const log = document.getElementById('log');
function bubble(who, text){
  const d = document.createElement('div');
  d.className = 'msg ' + (who === 'you' ? 'you' : 'her');
  d.textContent = text;                 // textContent: nothing is ever HTML
  log.appendChild(d); log.scrollTop = log.scrollHeight;
  return d;
}
async function refreshMems(){
  const r = await fetch('/api/memories'); const data = await r.json();
  const box = document.getElementById('mems'); box.innerHTML = '';
  for (const m of [...data.facts, ...data.notes]){
    const row = document.createElement('div'); row.className = 'mem';
    const left = document.createElement('div');
    left.textContent = (m.handle.startsWith('n') && /^n\\d+$/.test(m.handle)
                        ? m.handle + ' · ' : '') + m.text;
    if (m.tags.length){
      const t = document.createElement('div'); t.className = 'tags';
      t.textContent = m.tags.map(x => '#' + x).join(' ');
      left.appendChild(t);
    }
    const btn = document.createElement('button');
    btn.className = 'small'; btn.textContent = 'forget';
    btn.onclick = async () => {
      await fetch('/api/forget', {method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({handle: m.handle})});
      refreshMems();
    };
    row.appendChild(left); row.appendChild(btn); box.appendChild(row);
  }
}
document.getElementById('send').onsubmit = async (e) => {
  e.preventDefault();
  const boxEl = document.getElementById('box');
  const msg = boxEl.value.trim(); if (!msg) return;
  boxEl.value = ''; bubble('you', msg);
  const thinking = bubble('her', '…');
  const r = await fetch('/api/chat', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({message: msg})});
  const data = await r.json();
  thinking.textContent = data.reply;
  refreshMems();
};
document.getElementById('teach').onsubmit = async (e) => {
  e.preventDefault();
  const text = document.getElementById('teachtext').value.trim();
  const key = document.getElementById('teachkey').value.trim();
  if (!text) return;
  await fetch('/api/teach', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text, key})});
  document.getElementById('teachtext').value = '';
  document.getElementById('teachkey').value = '';
  refreshMems();
};
refreshMems();
</script>
</body>
</html>"""


def create_app(companion: Clementine) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def home():
        return render_template_string(
            PAGE, name=companion.personality.name or "Clementine")

    @app.post("/api/chat")
    def chat():
        message = ((request.get_json(silent=True) or {}).get("message") or "").strip()
        if not message:
            return jsonify({"error": "empty message"}), 400
        return jsonify({"reply": companion.chat(message)})

    @app.get("/api/memories")
    def memories():
        facts = [{"handle": k, "text": f"{k}: {v['value']}",
                  "tags": v.get("tags") or []}
                 for k, v in companion.memory.facts.items()]
        notes = [{"handle": f"n{i}", "text": n["text"],
                  "tags": n.get("tags") or []}
                 for i, n in enumerate(companion.memory.notes, 1)]
        return jsonify({"facts": facts, "notes": notes})

    @app.post("/api/teach")
    def teach():
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        key = (data.get("key") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "empty"}), 400
        if key:
            companion.remember_fact(key, text)
        else:
            companion.remember(text)
        return jsonify({"ok": True})

    @app.post("/api/forget")
    def forget():
        handle = ((request.get_json(silent=True) or {}).get("handle") or "").strip()
        forgotten = companion.forget(handle)
        return jsonify({"ok": bool(forgotten), "forgotten": forgotten})

    return app


def main():
    parser = argparse.ArgumentParser(
        description="Clementine's local web interface (127.0.0.1 only).")
    parser.add_argument("--model", default="llama3.1:8b",
                        help="Ollama model tag (same choices as the CLI).")
    parser.add_argument("--memory-dir", default="clementine_memory",
                        help="Her memory folder (shared with the CLI).")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    companion = Clementine(model=args.model, memory_dir=args.memory_dir)
    app = create_app(companion)
    name = companion.personality.name or "Clementine"
    print(f"{name} is at home: open http://127.0.0.1:{args.port}")
    print("Local only — nothing leaves this device. Ctrl+C to say goodnight.")
    # Never bind beyond localhost, never enable the debugger: sovereignty
    # means this page is reachable from this machine alone.
    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
