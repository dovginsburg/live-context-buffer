# Live Context Buffer — Phase 1 Implementation

## Status: ✅ Complete (pending gateway restart)

## What Was Built

A user plugin at `~/.hermes/profiles/ezra_chat/plugins/live_context/` that implements
a rolling context buffer via the `pre_llm_call` hook.

### Files
- `plugin.yaml` — Plugin manifest (name, version, hooks)
- `__init__.py` — Plugin code (~200 lines)

### How It Works
1. On each LLM call, the `pre_llm_call` hook fires
2. It reads `conversation_history` (the session's message list)
3. Extracts the last N user messages (excluding the current trigger)
4. Applies time window filtering (default: last 30 minutes)
5. Formats as a `## Recent Context` block
6. Returns `{"context": block}` → agent core appends to user message

### Config (in config.yaml)
```yaml
live_context:
  enabled: true
  max_messages: 15       # Max recent messages to include
  max_tokens: 400        # Hard token budget for the context block
  time_window_minutes: 30  # Only include messages from last N minutes
  min_messages: 3        # Always inject at least this many (if available)
```

### Token Budget
- Header: ~20 tokens
- Messages (15 max): ~250-350 tokens
- Total: ~350-500 tokens (within budget)

### What's NOT in Phase 1
- Summary layer for older messages (Phase 2)
- Image description injection (Phase 3)
- Multi-platform config overrides (Phase 4)
- Priority scoring / topic detection (Phase 5)

## Verification
The plugin was tested with:
- Basic message formatting (sender extraction, truncation)
- Token budget enforcement
- Time window filtering (old messages excluded)
- Longer conversations (20+ messages)

## To Activate
Restart the gateway: `hermes gateway restart`
The plugin will be loaded automatically from the user plugins directory.

## Architecture Notes
- Uses Hermes `pre_llm_call` hook (not channel_context like Discord)
- Reads from `conversation_history` parameter (session's message list)
- Non-invasive: no core modifications, plugin-based
- Fails open: returns None on error, agent runs without context
- Configurable: window size, token budget, time window, min messages
