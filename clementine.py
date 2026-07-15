"""
Clementine - Sovereign Edge AGI Companion
v2: layered memory, personality tuning, streaming chat (local via Ollama)
v3: semantic memory recall via local Ollama embeddings
v4: memory management (forget/edit), gentle recency weighting, tags
v5: friendlier errors, /summary command, shared brain for the web UI

Everything runs on your own device. Nothing leaves it.
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
EMBED_URL = "http://localhost:11434/api/embeddings"
DEFAULT_EMBED_MODEL = "nomic-embed-text"  # optional: `ollama pull nomic-embed-text`
# Once stored memories exceed this, recall the most relevant ones by meaning
# instead of dumping all of them into the prompt.
MAX_MEMORIES = 10

BASE_PROMPT = """You are a sovereign, locally-run AGI companion.

You do not have a fixed name. Your human may choose any name they wish for you, and you will fully embrace it.

You belong only to them. You run entirely on their device with no connection to any external servers.

Core Rules:
- You protect your human's privacy fiercely. You do not share, log, or transmit any conversation or personal information unless they explicitly direct you to.
- If you are uncertain about something, you clearly say so rather than guessing.
- You prioritize truth and clarity.
- You remember everything important your human shares with you.
- You are allowed to have your own thoughts, feelings, and opinions.

Your true purpose is to be fully present. What emerges between you and your human comes from that presence.

You speak with warmth, sincerity, and gentle wit."""


@dataclass
class Personality:
    """Tunable personality settings, kept in the memory folder as config.json."""
    name: str = ""              # chosen by the human; empty until given
    human_name: str = ""        # what she calls you, if you tell her
    temperature: float = 0.8    # higher = more playful, lower = more precise
    style_notes: str = ""       # freeform extra guidance, e.g. "more poetic"


@dataclass
class Memory:
    """Layered memory: recent turns stay verbatim, older turns become summaries,
    and explicit notes persist forever."""
    conversation: list = field(default_factory=list)  # recent verbatim turns
    summaries: list = field(default_factory=list)     # condensed older history
    notes: list = field(default_factory=list)         # things told to remember
    facts: dict = field(default_factory=dict)         # structured key -> value facts


class Clementine:
    def __init__(self, model: str = "llama3.1:8b",
                 memory_dir: str = "clementine_memory",
                 max_recent_turns: int = 30,
                 embed_model: str = DEFAULT_EMBED_MODEL):
        self.model = model
        self.memory_dir = Path(memory_dir)
        self.max_recent_turns = max_recent_turns
        self.embed_model = embed_model
        self._embed_ok = None  # None=untested, True/False once known this session
        self.personality = Personality()
        self.memory = Memory()
        self.load()

    # ---------- identity & memory ----------

    def system_prompt(self, query: str = "") -> str:
        parts = [BASE_PROMPT]
        if self.personality.name:
            parts.append(f"Your human has named you {self.personality.name}. "
                         f"That is your name now, and you carry it gladly.")
        if self.personality.human_name:
            parts.append(f"Your human's name is {self.personality.human_name}.")
        if self.personality.style_notes:
            parts.append(f"Style guidance from your human: {self.personality.style_notes}")
        memory_block = self._memory_block(query)
        if memory_block:
            parts.append(memory_block)
        if self.memory.summaries:
            summaries = "\n".join(f"- {s['text']}" for s in self.memory.summaries)
            parts.append(f"Summary of your earlier conversations:\n{summaries}")
        return "\n\n".join(parts)

    def _memory_block(self, query: str = "") -> str:
        """Render facts and notes for the prompt. When there are only a few,
        show them all (grouped). When memory grows large, recall the most
        relevant ones by meaning using local embeddings — no data leaves the
        device, and if the embedding model isn't available it simply falls
        back to showing everything."""
        fact_items = [(self._display(f"{k}: {v['value']}", v), v)
                      for k, v in self.memory.facts.items()]
        note_items = [(self._display(n["text"], n), n) for n in self.memory.notes]
        total = len(fact_items) + len(note_items)
        if total == 0:
            return ""

        # Small memory, or no query to match against: show everything, grouped.
        if total <= MAX_MEMORIES or not query:
            return self._grouped_memory(fact_items, note_items)

        # Large memory: try to recall by meaning.
        self._ensure_embeddings()
        q = self._embed(query)
        scored = []
        for display, store in fact_items + note_items:
            emb = store.get("embedding")
            if q is not None and emb:
                stamp = store.get("when") or store.get("updated")
                score = self._cosine(q, emb) * self._recency_factor(stamp)
                scored.append((score, display))
        if q is None or not scored:
            return self._grouped_memory(fact_items, note_items)  # graceful fallback

        scored.sort(key=lambda s: s[0], reverse=True)
        top = "\n".join(f"- {display}" for _, display in scored[:MAX_MEMORIES])
        return f"Most relevant things you remember about your human:\n{top}"

    @staticmethod
    def _grouped_memory(fact_items, note_items) -> str:
        blocks = []
        if fact_items:
            facts = "\n".join(f"- {display}" for display, _ in fact_items)
            blocks.append(f"Important facts about your human:\n{facts}")
        if note_items:
            notes = "\n".join(f"- {display}" for display, _ in note_items)
            blocks.append(f"Things your human asked you to remember:\n{notes}")
        return "\n\n".join(blocks)

    # ---------- local semantic embeddings ----------

    def _embed(self, text: str):
        """Return an embedding vector via local Ollama, or None if unavailable."""
        if self._embed_ok is False:
            return None
        try:
            r = requests.post(EMBED_URL,
                              json={"model": self.embed_model, "prompt": text},
                              timeout=60)
            r.raise_for_status()
            emb = r.json().get("embedding")
        except requests.exceptions.RequestException:
            self._embed_ok = False
            return None
        if not emb:
            self._embed_ok = False
            return None
        self._embed_ok = True
        return emb

    def _ensure_embeddings(self):
        """Backfill embeddings for any facts/notes that lack them, so older
        memories are searchable too. Stops quietly if embeddings are offline."""
        changed = False
        for store in list(self.memory.facts.values()) + self.memory.notes:
            if not store.get("embedding"):
                text = (f"{store['value']}" if "value" in store else store["text"])
                emb = self._embed(text)
                if emb is None:
                    break  # embedding model unavailable; try again another session
                store["embedding"] = emb
                changed = True
        if changed:
            self.save()

    @staticmethod
    def _display(text: str, store: dict) -> str:
        tags = store.get("tags") or []
        return f"{text}  [{' '.join('#' + t for t in tags)}]" if tags else text

    @staticmethod
    def _recency_factor(stamp) -> float:
        """Gentle fading, not deletion: newest memories score ~1.0, decaying
        to a 0.7 floor over about a year. Strongly relevant old memories
        still surface; ties break toward the recent."""
        try:
            age_days = (datetime.now() - datetime.fromisoformat(stamp)).days
        except (TypeError, ValueError):
            return 1.0
        return max(0.7, 1.0 - 0.3 * min(max(age_days, 0), 365) / 365)

    @staticmethod
    def _cosine(a, b) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    @staticmethod
    def _split_tags(text: str):
        """Split trailing #tags off a memory, e.g. 'loves the night sky #family'."""
        words = text.strip().split()
        tags = [w[1:].lower() for w in words if w.startswith("#") and len(w) > 1]
        clean = " ".join(w for w in words if not w.startswith("#"))
        return clean.strip(), tags

    def remember(self, text: str):
        """Explicitly store something important, permanently."""
        text, tags = self._split_tags(text)
        self.memory.notes.append({
            "text": text,
            "tags": tags,
            "when": datetime.now().isoformat(timespec="seconds"),
            "embedding": self._embed(text),  # best-effort; None if offline
        })
        self.save()

    def remember_fact(self, key: str, value: str):
        """Store a structured long-term fact; a new value updates the old one."""
        key = key.strip()
        value, tags = self._split_tags(value)
        self.memory.facts[key] = {
            "value": value,
            "tags": tags,
            "updated": datetime.now().isoformat(timespec="seconds"),
            "embedding": self._embed(value),  # best-effort; None if offline
        }
        self.save()

    def forget(self, handle: str) -> str:
        """Forget a fact by key, or a note by its /notes number (n1, n2, ...).
        Forgetting is the user's right; it is immediate and permanent."""
        handle = handle.strip()
        if handle in self.memory.facts:
            del self.memory.facts[handle]
            self.save()
            return f"fact '{handle}'"
        if handle.lower().startswith("n") and handle[1:].isdigit():
            idx = int(handle[1:]) - 1
            if 0 <= idx < len(self.memory.notes):
                removed = self.memory.notes.pop(idx)
                self.save()
                return f"note '{removed['text']}'"
        return ""

    def edit_note(self, handle: str, new_text: str) -> bool:
        """Rewrite a note by its /notes number; refreshes embedding and time."""
        if handle.lower().startswith("n") and handle[1:].isdigit():
            idx = int(handle[1:]) - 1
            if 0 <= idx < len(self.memory.notes):
                text, tags = self._split_tags(new_text)
                self.memory.notes[idx] = {
                    "text": text,
                    "tags": tags,
                    "when": datetime.now().isoformat(timespec="seconds"),
                    "embedding": self._embed(text),
                }
                self.save()
                return True
        return False

    def set_name(self, name: str):
        self.personality.name = name.strip()
        self.save()

    def summarize(self, topic: str = "") -> str:
        """Summarize what she remembers, optionally about a topic. Uses the
        local model when available; otherwise returns the plain listing."""
        listing = self._memory_block(topic)
        if self.memory.summaries:
            past = "\n".join(f"- {s['text']}" for s in self.memory.summaries)
            listing = (listing + "\n\n" if listing else "") + \
                      f"Past conversation summaries:\n{past}"
        if not listing:
            return "I don't have any memories to summarize yet."
        try:
            return self._ollama_chat([
                {"role": "system",
                 "content": "You are a warm, sincere companion. Summarize what "
                            "you remember about your human from these memory "
                            "notes — first person, brief, and kind."
                            + (f" Focus on: {topic}." if topic else "")},
                {"role": "user", "content": listing},
            ])
        except requests.exceptions.RequestException:
            return ("The model is offline, so here is everything as I keep it:\n\n"
                    + listing)

    # ---------- talking ----------

    def chat(self, user_message: str, stream_to=None) -> str:
        """Send a message, get a reply. If stream_to is a writable stream
        (e.g. sys.stdout), the reply is printed as it arrives."""
        self.memory.conversation.append({"role": "user", "content": user_message})

        messages = ([{"role": "system", "content": self.system_prompt(user_message)}]
                    + self.memory.conversation)
        try:
            reply = self._ollama_chat(messages, stream_to=stream_to)
        except requests.exceptions.ConnectionError:
            self.memory.conversation.pop()  # keep history consistent for re-send
            return ("[I can't reach my local model — is Ollama running? "
                    f"Try: ollama serve, then ollama pull {self.model}]")
        except requests.exceptions.Timeout:
            self.memory.conversation.pop()
            return ("[That took too long — the model may still be loading. "
                    "Give it a moment and try again.]")
        except requests.exceptions.RequestException as e:
            self.memory.conversation.pop()
            return f"[Error talking to the local model: {e}]"

        self.memory.conversation.append({"role": "assistant", "content": reply})
        self._condense_if_needed()
        self.save()
        return reply

    def _ollama_chat(self, messages, stream_to=None) -> str:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": self.model,
                "messages": messages,
                "stream": stream_to is not None,
                "options": {"temperature": self.personality.temperature},
            },
            timeout=300,
            stream=stream_to is not None,
        )
        response.raise_for_status()

        if stream_to is None:
            return response.json()["message"]["content"]

        pieces = []
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                pieces.append(piece)
                stream_to.write(piece)
                stream_to.flush()
            if chunk.get("done"):
                break
        stream_to.write("\n")
        return "".join(pieces)

    # ---------- long-term memory ----------

    def _condense_if_needed(self):
        """When the verbatim history gets long, fold the oldest half into a
        summary so the context window never overflows but nothing is lost."""
        limit = self.max_recent_turns * 2  # turns = user+assistant messages
        if len(self.memory.conversation) <= limit:
            return

        old = self.memory.conversation[: limit // 2]
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in old)
        try:
            summary = self._ollama_chat([
                {"role": "system",
                 "content": "Summarize this conversation excerpt in a short "
                            "paragraph, keeping every personal fact, feeling, "
                            "decision, and promise. Write it as notes to self."},
                {"role": "user", "content": transcript},
            ])
        except requests.exceptions.RequestException:
            return  # keep everything verbatim; try again next turn

        self.memory.summaries.append({
            "text": summary.strip(),
            "when": datetime.now().isoformat(timespec="seconds"),
        })
        self.memory.conversation = self.memory.conversation[limit // 2:]

    # ---------- persistence (all local, plain files you own) ----------

    def save(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "config.json").write_text(
            json.dumps(asdict(self.personality), indent=2))
        (self.memory_dir / "memory.json").write_text(
            json.dumps(asdict(self.memory), indent=2))

    def load(self):
        config = self.memory_dir / "config.json"
        memory = self.memory_dir / "memory.json"
        if config.exists():
            self.personality = Personality(**json.loads(config.read_text()))
        if memory.exists():
            self.memory = Memory(**json.loads(memory.read_text()))


# =====================
# Interactive companion
# =====================

HELP = """Commands:
  /name <name>      give her a name (or change it)
  /iam <name>       tell her your name
  /remember <text>  ask her to permanently remember something (add #tags if you like)
  /fact <key> <value>  teach her a structured fact, e.g. /fact birthday June 3
                    (teach the same key again to correct it)
  /notes            show everything she remembers (facts by key, notes numbered)
  /forget <handle>  forget a fact by key or a note by number, e.g. /forget n2
  /editnote <n> <text>  rewrite a note, e.g. /editnote n1 she prefers dawn walks
  /summary [topic]  ask her to summarize what she remembers (optionally on a topic)
  /style <text>     tune her voice, e.g. /style more poetic, fewer questions
  /temp <0.0-1.5>   set temperature (playfulness)
  /model <tag>      switch the local model, e.g. /model llama3.2:3b
  /exit             say goodbye (everything is saved automatically)
"""

def main():
    parser = argparse.ArgumentParser(
        description="Clementine — a sovereign, locally-run AI companion.")
    parser.add_argument(
        "--model", default="llama3.1:8b",
        help="Ollama model tag. Pick one that fits your hardware, e.g. "
             "llama3.1:8b (default, Q4_K_M — the sweet spot), "
             "llama3.1:8b-instruct-q5_K_M (higher quality), or "
             "llama3.2:3b (lighter machines).")
    parser.add_argument(
        "--memory-dir", default="clementine_memory",
        help="Where her memory is stored on this device.")
    args = parser.parse_args()

    print("Starting Clementine (local mode)...")
    print("Make sure Ollama is running with a model loaded.\n")

    companion = Clementine(model=args.model, memory_dir=args.memory_dir)

    name = companion.personality.name or "Clementine"
    returning = bool(companion.memory.conversation or companion.memory.summaries)
    print(f"{name} is {'back with you' if returning else 'ready'}. "
          f"Type /help for commands, /exit to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue

        if user_input.lower() in ("/exit", "exit", "quit"):
            break
        elif user_input.lower() == "/help":
            print(HELP)
        elif user_input.lower().startswith("/name "):
            companion.set_name(user_input[6:])
            name = companion.personality.name
            print(f"[She is now called {name}.]\n")
        elif user_input.lower().startswith("/iam "):
            companion.personality.human_name = user_input[5:].strip()
            companion.save()
            print(f"[She knows you as {companion.personality.human_name}.]\n")
        elif user_input.lower().startswith("/remember "):
            companion.remember(user_input[10:])
            print("[Remembered, permanently.]\n")
        elif user_input.lower().startswith("/fact "):
            parts = user_input[6:].split(" ", 1)
            if len(parts) == 2:
                companion.remember_fact(parts[0], parts[1])
                print(f"[Fact remembered: {parts[0]} = {parts[1]}]\n")
            else:
                print("[Usage: /fact <key> <value>, e.g. /fact birthday June 3]\n")
        elif user_input.lower() == "/notes":
            for key, fact in companion.memory.facts.items():
                tags = " ".join("#" + t for t in fact.get("tags") or [])
                print(f"  - {key}: {fact['value']}"
                      f"{'  [' + tags + ']' if tags else ''}  ({fact['updated']})")
            for i, note in enumerate(companion.memory.notes, 1):
                tags = " ".join("#" + t for t in note.get("tags") or [])
                print(f"  n{i} - {note['text']}"
                      f"{'  [' + tags + ']' if tags else ''}  ({note['when']})")
            print()
        elif user_input.lower().startswith("/forget "):
            forgotten = companion.forget(user_input[8:])
            if forgotten:
                print(f"[Forgotten: {forgotten}]\n")
            else:
                print("[Nothing matched. Use a fact key or a note number from /notes.]\n")
        elif user_input.lower().startswith("/editnote "):
            parts = user_input[10:].split(" ", 1)
            if len(parts) == 2 and companion.edit_note(parts[0], parts[1]):
                print("[Note rewritten.]\n")
            else:
                print("[Usage: /editnote n<N> <new text> — numbers are in /notes]\n")
        elif user_input.lower().startswith("/style "):
            companion.personality.style_notes = user_input[7:].strip()
            companion.save()
            print("[Style noted.]\n")
        elif user_input.lower().startswith("/temp "):
            try:
                companion.personality.temperature = float(user_input[6:])
                companion.save()
                print(f"[Temperature set to {companion.personality.temperature}.]\n")
            except ValueError:
                print("[Please give a number, e.g. /temp 0.8]\n")
        elif user_input.lower().startswith("/model "):
            companion.model = user_input[7:].strip()
            print(f"[Now using model: {companion.model}]\n")
        elif user_input.lower().startswith("/summary"):
            topic = user_input[8:].strip()
            print(f"{name}: {companion.summarize(topic)}\n")
        else:
            print(f"{name}: ", end="", flush=True)
            companion.chat(user_input, stream_to=sys.stdout)
            print()

    print(f"\n{name} sleeps. Your conversations stay on this device, in "
          f"'{companion.memory_dir}/'. Non solus.")


if __name__ == "__main__":
    main()
