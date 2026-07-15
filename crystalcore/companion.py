"""
CrystalCore companion: the brain.

Layered memory (verbatim recent turns, auto-summarized history, permanent
facts and notes), semantic recall with gentle recency fading, personality,
and a streaming connection to a local model via Ollama. Everything runs on
the user's own device. Nothing leaves it.
"""

import json
import math
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import requests

from .memory import Memory, Personality

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


class Clementine:
    """The default persona of the CrystalCore framework."""

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
