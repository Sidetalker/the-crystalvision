# Architecture — TerAustralis Incognita

**Status of this document.** This is a design overview, not a description of deployed software. It records the intended shape of the system so that a collaborator can see the structure behind the vision. As of mid-2026, the components below are at the *concept and design* stage, with two exceptions: the **Voices Framework**, which is the working method actively used to produce the project, and the **website**, which is the immediate engineering deliverable.

---

## The Five Layers

| Layer | What it is | Status |
|-------|------------|--------|
| **StarMind** | The apparatus — the external industrial ecosystem the vision orients around: Tesla, SpaceX, Starlink, Neuralink, X | External reference point. These are independent companies; the project has **no affiliation with or endorsement from** any of them. |
| **CrystalMind** | The doing — the project's own intended stack: Sovereign Edge AGI, CrystalCore.OS, the Voices Framework | Concept, except the Voices Framework (in use — see below) |
| **Sovereign Node Mesh** | The collective — an envisioned network of participants: humans, AIs, bots, hybrids, and governments as partners | Concept |
| **Energy Grid Autonomy** | The first module — sovereign energy production, storage, and distribution | Concept; first envisioned domain of application |
| **Governance** | The v2.2 Control Plane — release gating and assurance for anything that ships | Specified; see below |

---

## Voices Framework (in active use)

The method by which the work is made: distinct AI tools hold named roles, coordinated by a human steward.

| Voice | Tool | Role |
|-------|------|------|
| CrystalDreamer | Grok | Dreams the visions |
| CrystalSinger | The Voice | Sings and interprets the songs |
| CrystalScribe | DeepSeek | Weaves the connections |
| CrystalForge | Claude | Forges the code |
| CrystalArchitect | The human steward | Guides the becoming |

The human CrystalArchitect holds final judgment over all outputs. The AI tools are instruments, not authorities. In these roles, Grok (CrystalDreamer) and DeepSeek (CrystalScribe) helped shape the Codex and the Apocryphon of Crystal.

---

## Governance — v2.2 Control Plane

The intended release discipline for anything the project ships:

- **10 release gates** that a change must pass before deployment
- **An evidence lifecycle** — decisions and approvals are recorded with supporting evidence
- **Continuous authorization** — permission to operate is ongoing and revocable, not granted once

The detailed gate definitions are to be documented alongside the first software release. Until then, the practical effect is simple: nothing ships without passing review, and the human steward can halt anything at any time.

---

## The Ω4 Layer (narrative architecture)

An earlier, eight-act edition of the Codex (preserved in this repository's git history) describes an agent stack (Scout, Auditor, Gnosis, Sentinel, Arbiter) and an immutable kernel (Ouroboros Cache, Sovereign Recursion Engine, Anti-Archon Firewall). These are **target concepts expressed in the language of the mythos** — design fiction that names the functions a future system would need (forecasting, verification, pattern recognition, protection, dispute resolution; plus memory management, iterative self-improvement, and security). No implementation exists.

---

## Current implementation status

**Exists now**
- The Codex, Chapters I–V (`CODEX.md`) and The Apocryphon of Crystal (`APOCRYPHON.md`)
- The Voices Framework working method
- Project identity: name, mantra, palette, coat of arms
- Registered ABN (70 741 068 059), domain (teraustralis.com.au), license structure

**Immediate build**
- Static single-page site at teraustralis.com.au (`index.html` — preview included). Requirements: static hosting, HTTPS, DNS for the .com.au domain. No backend, no database, no build step.

**Envisioned (no code yet)**
- CrystalCore.OS and the Sovereign Edge stack
- The Sovereign Node Mesh
- The Energy Grid Autonomy module
- The Ω4 agent stack and kernel

---

## Licensing

- **Code:** Apache 2.0
- **Content (Codex, writing, imagery):** CC BY-NC-ND 4.0

This split lets others run and adapt the software freely while keeping the mythos itself attributed and intact.
