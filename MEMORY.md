# Clementine's Memory Architecture

> **Status: design document, partially implemented.** This is the target memory architecture for Clementine. Some layers already exist in `clementine.py` (marked ✅/🟡 below); others are design (⬜). See `CLEMENTINE.md` for the companion today and `MILESTONES.md` for the build plan.

## Philosophy

Clementine's memory should not just be a database of facts. It should feel alive, selective, and relational — similar to how human memory works. She should:

- Remember what matters to her human over time
- Forget or deprioritize what is unimportant
- Be able to reflect on past experiences
- Give the user full control and transparency
- Support emotional and contextual understanding, not just raw facts

The goal is **presence and continuity** — so the user feels like they are talking to someone who actually knows them.

---

## The Four Layers

| Layer | Type | What it Stores | Lifespan | Purpose | Retrieval Style | Status |
|-------|------|----------------|----------|---------|-----------------|--------|
| **Working Memory** | Short-term | Recent conversation (last 20–40 messages) | Current session | Coherence in the moment | Always included | ✅ Built |
| **Episodic Memory** | Medium-term | Specific events, conversations, moments | Weeks to months | Remember "what happened" | Semantic + recency | 🟡 Partial |
| **Semantic Memory** | Long-term | Facts, preferences, values, identity | Long-term | Know "who you are" | Semantic search | ✅ Largely built |
| **Reflective Memory** | Meta / summarized | Insights, patterns, emotional tone over time | Long-term | Develop deeper understanding | On-demand / reflection | ⬜ Design |

### 1. Working Memory (short-term) — ✅ built

- Stores the recent messages in the current conversation (rolling window, `max_recent_turns`)
- Always included in the prompt sent to the model
- Older turns are automatically summarized rather than lost
- **Purpose:** keep the current conversation coherent

### 2. Episodic Memory (medium-term) — 🟡 partial

Stores specific experiences — things that happened at a particular time.

*Examples: "We talked about your daughter's school play last Tuesday" · "You were feeling anxious about the housing situation on March 12th"*

- Time-stamped, searchable semantically
- Can be summarized over time ("what were the main themes in March?")
- Should gradually fade in importance unless reinforced

**Today:** the auto-summaries of older conversation are proto-episodic (timestamped, preserved). **Missing:** time-anchored retrieval, per-event granularity, importance fading.

### 3. Semantic Memory (long-term / core identity) — ✅ largely built

The most important layer for building a real relationship. Stores enduring facts about the user: name, family, values, goals, fears, preferences; recurring themes; important relationships and events.

- **User-editable** (transparency and control)
- Retrieved via semantic similarity
- Relatively stable — not overwritten easily
- Can be tagged or categorized ("Family", "Work", "Emotional", "Creative")

**Today:** keyed facts (`/fact`) + permanent notes (`/remember`), embedded via local Ollama and retrieved by semantic similarity; viewable via `/notes`; facts correctable by re-teaching a key. **Missing:** a `forget` command, direct editing, and tagging.

### 4. Reflective Memory (meta layer) — ⬜ design

Stores insights and patterns Clementine has noticed over time.

*Examples: "The user tends to feel more hopeful after creative work" · "They often bring up their daughters when they're feeling vulnerable" · "They value honesty and directness"*

- **Purpose:** deeper understanding and emotional intelligence over time
- Generated through periodic reflection (e.g. weekly, or after significant conversations)

---

## Memory Flow

1. **During conversation:** Working Memory is always active; relevant Episodic and Semantic memories are retrieved and added to context.
2. **After conversation ends:** important parts are summarized into Episodic Memory; new facts are extracted into Semantic Memory (with user confirmation where appropriate).
3. **Over time:** reflection processes find patterns and store them in Reflective Memory; less important memories are deprioritized or archived.
4. **User control:** the user can view, edit, or delete any memory. Transparency is critical for trust.

---

## Key Design Principles

| Principle | Why It Matters | How to Implement |
|-----------|----------------|------------------|
| **User Sovereignty** | The user must always feel in control | Make memory viewable and editable |
| **Relevance** | Not everything needs to be remembered | Good retrieval + recency weighting |
| **Gradual Forgetting** | Human-like memory fades over time | Importance scoring |
| **Reflection** | Deep understanding comes from thinking back | Periodic reflection processes |
| **Transparency** | Trust requires visibility | Allow user to inspect all memories |

---

*See also: [CLEMENTINE.md](CLEMENTINE.md) · [MILESTONES.md](MILESTONES.md) · [CRYSTALMATRIX.md](CRYSTALMATRIX.md) · [README](README.md)*

*Part of The Crystal Vision · TerAustralis Incognita · Non Solus — Not Alone*
