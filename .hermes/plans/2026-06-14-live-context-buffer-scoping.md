# Live Context Buffer — Architecture Scoping Brief

## Problem Statement

Hermes agents (like Ezra) have a critical blind spot: they can observe messages and images arriving in real-time (via the WhatsApp observe pipeline), but when asked a question about recent context, they default to stale Hindsight memory instead of the most recent input. The agent has no efficient "what just happened" layer.

Current memory tiers:
- T0 (native prompt memory) — tiny pointer layer, ~1.3KB, always loaded. Good for rules/routing, bad for recent context.
- T1 (Obsidian) — structured notes, not real-time.
- T2 (Hindsight) — cross-session semantic recall. Good for "what happened last week", terrible for "what did Zach just send 5 minutes ago."
- T3 (GBrain) — entity/policy index. Not real-time either.

The gap: there is no "live context buffer" — a lightweight, token-efficient layer that captures the last 30-60 minutes of chat activity (messages, analyzed images, speaker identities, topics) and makes it effortlessly available at reasoning time.

## Key Constraint

**DO NOT propose reinjecting 60 minutes of raw chat history into every turn.** That would blow up token budgets. The solution must be token-efficient — something like a compressed summary, index, or on-demand lookup.

## What Already Exists

1. **WhatsApp observe pipeline** (`observe_unmentioned_group_messages: true`) — already captures ALL messages (tagged and untagged) and pre-analyzes images via vision_analyze. Stores them in the session transcript.
2. **Session search** (`session_search`) — FTS5-backed retrieval over the SQLite message store. Can scroll recent messages.
3. **Image cache** (`~/.hermes/image_cache/`) — images are downloaded and cached locally.
4. **Hindsight retain/recall** — cross-session semantic memory.

The observe pipeline does the CAPTURE. The missing piece is making that captured data EFFORTLESSLY AVAILABLE at reasoning time without the agent having to actively search for it.

## What the Solution Needs

1. **Token efficiency** — <500 tokens per turn overhead, not thousands
2. **Relevance-aware** — only inject context when the question requires it (image questions, "what did X say", location questions, etc.)
3. **Recency-biased** — most recent context first, work backwards
4. **Image-aware** — recent images with descriptions should be instantly queryable
5. **Speaker-aware** — who said what, when
6. **Works across all platforms** — WhatsApp, Telegram, DMs, groups

## Design Questions to Answer

1. What form should the "live context buffer" take? (rolling summary file? in-memory ring buffer? queryable index? something else?)
2. How should it be populated? (from the observe pipeline? from session transcripts? from a background summarizer?)
3. How should the agent access it? (always injected? on-demand tool? triggered by keywords?)
4. What's the token budget? (target: <500 tokens/turn for the context layer)
5. How does it interact with existing tiers? (T0 pointer → live buffer → Hindsight → GBrain)
6. Should images be pre-indexed with descriptions and timestamps?
7. How to handle the "most recent context first" pattern without full transcript injection?

## Deliverable

A scoped architecture proposal that:
- Defines the data model and storage format
- Specifies the population pipeline (what writes to it, when)
- Specifies the retrieval mechanism (how the agent reads from it)
- Estimates token overhead per turn
- Identifies which Hermes components need modification
- Provides a phased implementation plan (what to build first)
