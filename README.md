# Live Context Buffer

A production-tested memory and context system for AI agents on WhatsApp.

## What this solves

AI agents on WhatsApp lose context between sessions. They can't see images properly, forget quoted messages, and break when the API rate-limits hit. This system fixes that.

## Components

### 1. Vision Pipeline Fix
- Swaps OpenCode Zen proxy (20 req/day cap) for direct Gemini API
- Dedicated API key per consumer (no shared quota starvation)
- Config: `config.yaml` → `auxiliary.vision`

### 2. Quoted Message Context
- Bridge extracts full quoted message text from WhatsApp contextInfo
- Gateway populates `reply_to_message_id` and `reply_to_text` in MessageEvent
- Agent can now see what someone replied to, not just that they replied
- Files: `scripts/whatsapp-bridge/bridge.js`, `gateway/platforms/whatsapp.py`

### 3. Group Chat Routing
- Tags control OUTPUT only, not INPUT — all messages observed regardless
- Silent observation enables later reference ("describe the image above")
- Router delivery counts as address even without explicit tag
- Config: `observe_unmentioned_group_messages: true`

### 4. Memory Architecture (T0/T1/T2/T3)

| Tier | System | Purpose |
|------|--------|---------|
| T0 | Prompt memory (MEMORY.md + USER.md) | Operational rules, always-loaded pointer layer |
| T1 | Obsidian + Registries | Authoritative canonical facts |
| T2 | Hindsight | Advisory semantic recall, conversational memory |
| T3 | GBrain | Embedded corpus for long-form retrieval |

**Key principles:**
- T0 is a cache, not source of truth
- Registries (`people.yml`, `policies.yml`, `systems.yml`) are the operational foundation
- T2 (Hindsight) never overwrites T1 (Obsidian)
- Daily LLM offload captures stable facts before context compaction

## Quick Start

```bash
# Vision: swap to direct Gemini API
# In config.yaml, replace auxiliary.vision section:
auxiliary:
  vision:
    api_key: <your-gemini-api-key>
    base_url: https://generativelanguage.googleapis.com/v1beta
    model: gemini-2.5-flash
    provider: gemini
    timeout: 120

# Bridge: quoted message text extraction
# Already included in bridge.js — just restart gateway:
hermes gateway restart

# Group chat observation
# In config.yaml:
whatsapp:
  extra:
    require_mention: true
    observe_unmentioned_group_messages: true
```

## Architecture

```
WhatsApp Bridge (Node.js)
  ↓ extracts: mentionedIds, quotedMessageId, quotedText, mediaUrls
  ↓ downloads images to ~/.hermes/image_cache/
Gateway (Python)
  ↓ builds MessageEvent with reply_to_message_id, reply_to_text
  ↓ pre-analyzes images with vision_analyze (Gemini)
  ↓ routes: tag gate → observe or dispatch
Agent
  ↓ receives full context: text + quoted text + image descriptions
  ↓ can reference prior observed messages
```

## Files Modified

- `gateway/platforms/whatsapp.py` — reply_to fields in MessageEvent
- `scripts/whatsapp-bridge/bridge.js` — quotedText extraction from contextInfo
- `config.yaml` — vision provider swap (OpenCode Zen → direct Gemini)

## License

MIT
