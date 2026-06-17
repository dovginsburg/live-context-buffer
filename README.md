# Live Context Buffer

A Hermes Agent plugin that injects recent chat context into the current LLM
turn. Generalizes the `history_backfill` pattern used by the built-in Discord
adapter so WhatsApp, iMessage, Telegram, and other platforms get the same
"what just happened" buffer.

## What this is

A single `pre_llm_call` hook plugin (~880 lines, no external dependencies)
that:

1. Reads the last N messages from the active session transcript
2. Filters out reactions, voice memo stubs, and other non-substantive
   content
3. Picks the most relevant 3-15 messages within a 400-token budget
4. Optionally summarizes older messages within a separate 80-token budget
5. Optionally attaches recent image descriptions (60 tokens)
6. Optionally applies priority scoring, adaptive window sizing, and
   entity tracking
7. Returns a `{"context": "..."}` dict that Hermes injects into the user
   message (never the system prompt, so the prompt cache stays stable)

The hook fires on **every** LLM call (CLI, WhatsApp, iMessage, Telegram,
Discord) but its effect is platform-specific — see the `platforms:` config
block below.

## Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Sliding window of recent messages (verbatim) | implemented |
| 2 | Extractive summary of older messages (zero-cost) | implemented |
| 3 | Image description injection from cached images | implemented |
| 4 | Per-platform config overrides, edge case hardening | implemented |
| 5 | Priority scoring, adaptive window, entity tracking | implemented |
| 6 | Q&A preservation in summary (Phase 6 — `Levi: Sleep…` survives compression) | implemented |
| 7 | **Every message is present in context** (no silent drops) | implemented |

Phases 1-5 ship in the base code; phases 6-7 are progressive refinements.
Phase 7 is the most important behavior guarantee: **no message is silently
dropped from the output**. A low-priority message can be compressed to a
per-sender one-liner in the summary, but it always has a slot. The
previous failure mode was `Topics: lcb, gary, levi` (keyword dump that
loses the actual content); Phase 7 emits
`[Levi]: Zach drives a Tesla Model Y, plate LBE2036` instead, so the
agent can answer "what did Levi say about Zach's car?" even minutes later.

## Install

This plugin lives at `~/.hermes/plugins/live_context/` in a standard
Hermes install. To install it elsewhere:

```bash
# Clone this repo
git clone https://github.com/dovginsburg/live-context-buffer.git
cd live-context-buffer

# Copy the plugin into your Hermes install
mkdir -p ~/.hermes/plugins/live_context
cp plugins/live_context/__init__.py ~/.hermes/plugins/live_context/
cp plugins/live_context/plugin.yaml ~/.hermes/plugins/live_context/

# Enable the plugin
hermes plugins enable live_context
```

## Config

Add a `live_context:` block to the profile's `config.yaml`. Per-profile
scoping is intentional — typically you only want this on the chat
profile (`ezra_chat`), not on the CLI profile (`default`):

```yaml
# In ~/.hermes/profiles/<name>/config.yaml
live_context:
  enabled: true
  max_messages: 15           # upper bound on the sliding window
  max_tokens: 400            # token budget for the window
  time_window_minutes: 30    # ignore messages older than this
  min_messages: 3            # always include at least this many if available
  summary:
    enabled: true
    max_tokens: 80           # budget for the older-message summary
    min_messages: 3          # only summarize if ≥ this many older messages
  images:
    max_count: 3
    max_tokens: 60
  platforms:
    whatsapp: {}
    discord:
      enabled: false         # Discord already has history_backfill built in
    telegram:
      max_messages: 20
      max_tokens: 500
    imessage:
      max_messages: 10
    slack: {}
    signal: {}
  smart:
    priority_scoring: true   # boost important messages in window
    adaptive_window: true    # adjust window size by message density
    entity_tracking: true    # track active participants
    entity_header: true      # show entity line in context block
```

## What it does NOT do

- **Does not fix the iMessage-not-responding problem.** If iMessage
  messages reach the Mac but don't trigger an agent run, that's a
  routing/adapter issue (`hermes-gateway-bluebubbles-debug`), not a
  context buffer issue. This plugin only helps when messages *do* reach
  the agent — it gives the agent better memory of what was said
  before.
- **Does not add new storage.** Reads from the existing session
  transcript in `state.db`. The sliding window is recomputed on every
  LLM call.
- **Does not modify the system prompt.** Injected context always goes
  into the user message, preserving the prompt cache prefix.
- **Does not persist injected context.** Each turn's context is
  ephemeral; the session DB only contains the actual user/assistant
  exchanges, not the backfill block.

## Architecture

```
                ┌──────────────────────────────────────────┐
                │  Hermes Agent (per-profile)              │
                │                                          │
inbound msg ──▶ │  gateway adapter                         │
                │    │                                     │
                │    ▼                                     │
                │  agent loop ──▶ pre_llm_call hook        │
                │                  │                       │
                │                  ▼                       │
                │          live_context plugin            │
                │            │              │              │
                │            ▼              ▼              │
                │      session db    image cache          │
                │      (state.db)    (~/.hermes/)         │
                │            │              │              │
                │            └──────┬───────┘              │
                │                   ▼                      │
                │          formatted context block         │
                │                   │                      │
                │                   ▼                      │
                │          injected into user message      │
                │                   │                      │
                │                   ▼                      │
                │              LLM call                    │
                └──────────────────────────────────────────┘
```

## Token budget

- Window: 400 tokens (configurable, 0.39% of a 128K context)
- Summary: 80 tokens (configurable)
- Images: 60 tokens (configurable)
- Total: ~540 tokens/turn at default settings

## Files

- `plugins/live_context/__init__.py` — the plugin (register + on_pre_llm_call)
- `plugins/live_context/plugin.yaml` — plugin manifest (name, hooks)

## Why "Phase 5 (Complete)" is in the docstring

The plugin shipped all five phases on 2026-06-14 in a single drop. The
docstring calls out the phases so future readers can disable or tune
each independently.

## License

MIT
