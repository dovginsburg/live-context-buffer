# Live Context Buffer — Scoping Brief for Default Profile

## Problem
Hermes agents observe all messages/images in real-time (via WhatsApp observe pipeline), but when asked a question about recent context, they default to stale Hindsight memory instead of the most recent input. The agent has no efficient "what just happened" layer.

## Current Architecture
- T0 (native memory) — pointer layer, ~1.3KB, always loaded. Good for rules/routing.
- T1 (Obsidian) — structured notes, not real-time.
- T2 (Hindsight) — cross-session semantic recall. Good for "last week", terrible for "5 minutes ago".
- T3 (GBrain) — entity/policy index. Not real-time.

## What Already Exists
1. WhatsApp observe pipeline (observe_unmentioned_group_messages: true) — captures ALL messages and pre-analyzes images. Stores in session transcript.
2. Session search (session_search) — FTS5-backed retrieval over SQLite message store.
3. Image cache (~/.hermes/image_cache/) — images downloaded and cached locally.
4. Hindsight retain/recall — cross-session semantic memory.

The observe pipeline does CAPTURE. Missing piece: making captured data EFFORTLESSLY AVAILABLE at reasoning time.

## Key Constraint
DO NOT propose reinjecting 60 minutes of raw chat history into every turn. Solution must be token-efficient (<500 tokens/turn overhead).

## What the Solution Needs
1. Token efficiency — <500 tokens/turn
2. Relevance-aware — only inject when question requires it
3. Recency-biased — most recent context first, work backwards
4. Image-aware — recent images with descriptions instantly queryable
5. Speaker-aware — who said what, when
6. Cross-platform — WhatsApp, Telegram, DMs, groups

## Design Questions to Answer
1. What form should the "live context buffer" take?
2. How should it be populated?
3. How should the agent access it?
4. What's the token budget?
5. How does it interact with existing tiers?
6. Should images be pre-indexed?
7. How to handle "most recent first" without full transcript injection?

## Deliverable
A scoped architecture proposal with:
- Data model and storage format
- Population pipeline
- Retrieval mechanism
- Token overhead estimate
- Hermes component modifications needed
- Phased implementation plan
