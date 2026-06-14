# Live Context Buffer: Architecture Proposal

**Author:** Ezra (cron agent)
**Date:** 2026-06-14
**Status:** Scoping / Planning
**Scope:** Make recently-observed WhatsApp/group-chat context effortlessly available at reasoning time without exceeding 500 tokens/turn overhead.

---

## 1. Problem Statement

Hermes agents observe all messages/images in real-time via the WhatsApp observe pipeline (`observe_unmentioned_group_messages: true`), but when asked a question about recent context, they default to stale Hindsight memory instead of the most recent input. The agent has no efficient "what just happened" layer.

**Current state:**
- T0 (native memory) — pointer layer, ~1.3KB, always loaded. Good for rules/routing.
- T1 (Obsidian) — structured notes, not real-time.
- T2 (Hindsight) — cross-session semantic recall. Good for "last week", terrible for "5 minutes ago".
- T3 (GBrain) — entity/policy index. Not real-time.

**The gap:** The observe pipeline CAPTURES data. Missing piece: making captured data EFFORTLESSLY AVAILABLE at reasoning time.

**Constraint:** Do NOT reinject 60 minutes of raw chat history into every turn. Solution must be token-efficient (<500 tokens/turn overhead).

---

## 2. Research: Existing Solutions

### 2.1 Agent Framework Patterns

| Pattern | Framework | How It Works | Token Efficiency | Relevance |
|---------|-----------|--------------|-----------------|-----------|
| **BufferWindowMemory** | LangChain | Fixed sliding window of N most recent messages. Discards everything older. | Very high (fixed) | High — simple but loses all historical context |
| **ConversationSummaryBufferMemory** | LangChain | Recent messages kept verbatim until token threshold; older messages summarized. | High (adaptive) | **Very high** — closest existing pattern to our need |
| **CombinedMemory** | LangChain | Multiple memory backends in parallel (e.g., buffer + entity). | Medium | Medium — useful for multi-source fusion |
| **Sliding Window + Summary** | Production pattern | Last 5-10 messages in full + running summary of older context. | High | **Very high** — industry standard production pattern |
| **Active Context Compression** | Focus architecture (arXiv:2601.07190) | Agent decides when to consolidate. Frequent small compressions every 10-15 calls. | High | Medium — agent-driven, adds complexity |
| **AgentRM** | OS-inspired (arXiv:2603.13110) | MLFQ scheduling + three-tier context management. Treats context as a schedulable resource. | High | Low — overkill for our use case |
| **TokenMizer** | Graph-structured (arXiv:2606.06337) | 14-node typed session graph. Structured recall of decisions, statuses, file changes. | Medium | Medium — good for coding agents, heavy for chat context |

### 2.2 Hermes-Specific Findings

| Feature | Status | Relevance |
|---------|--------|-----------|
| **Context Compression** (`compression.enabled`, `protect_last_n: 20`) | Built-in, configurable | Operates on ACTIVE conversation turns, not on observed context from other chats |
| **Event Hooks** (`pre_llm_call`) | Built-in, pluggable | **Ideal integration point** — can inject context into user message before LLM call |
| **Context Engine Plugins** | Built-in, pluggable | Can replace built-in compression with custom strategy |
| **Discord History Backfill** (`history_backfill: true`, `history_backfill_limit: 50`) | Built-in for Discord only | **Exactly the pattern we need** — but only implemented for Discord, not WhatsApp |
| **WhatsApp Observe Pipeline** | Built-in | Captures all messages + pre-analyzes images. Stores in session transcript. |
| **Session Search** (FTS5-backed) | Built-in tool | Can query SQLite message store, but requires active tool call |
| **Honcho Memory** | Optional plugin | Cross-session user modeling — not real-time |
| **hermes-lcm** (Lossless Context Management) | Third-party plugin | Builds knowledge DAG instead of lossy summarization — interesting but different scope |

### 2.3 Key Insight

**Hermes already has the Discord `history_backfill` pattern** — it prepends recent channel scrollback to the user message when the bot is mentioned. This is exactly the "live context buffer" pattern we need, but it's only implemented for Discord, not WhatsApp/observe contexts.

The solution is to **generalize the Discord backfill pattern** into a reusable "live context buffer" that works across all observe-capable platforms.

---

## 3. Recommendation: Hybrid Approach (Custom, Built on Existing Hermes Infrastructure)

**Do NOT** use an existing framework (LangChain etc.) — Hermes already has the right primitives.

**Do NOT** build a new Context Engine plugin — that's for replacing compression strategy, not for adding observed-context injection.

**DO** build a **pre_llm_call plugin** that implements a rolling context buffer, generalized from the Discord `history_backfill` pattern.

### Why This Approach?

1. **Leverages existing infrastructure**: `pre_llm_call` hook, session transcript, image cache
2. **Token-efficient**: Sliding window + summary keeps overhead under 500 tokens
3. **Non-invasive**: Plugin-based, no core modifications needed
4. **Consistent with Hermes architecture**: Follows the same pattern as Discord backfill
5. **Configurable**: Users can tune window size, summary aggressiveness, etc.

---

## 4. Architecture

### 4.1 Data Model

```yaml
# Stored in-memory per-session (not persisted — regenerates from session transcript)
live_context_buffer:
  session_id: "whatsapp:group:12345"
  window:
    messages: []          # Last N observed messages (sliding window)
    max_messages: 15      # Configurable
    max_tokens: 400       # Token budget for the window
  summary:
    text: ""              # Compressed summary of messages outside the window
    last_updated: null    # Timestamp of last summary generation
    token_count: 0        # Current summary token count
  images:
    recent: []            # Last M image references (path + alt text)
    max_images: 3         # Configurable
```

### 4.2 Storage Format

The buffer is **in-memory per session**, rebuilt from the session transcript on each turn. It does NOT persist separately — it's a computed view over the existing session data.

```python
# Pseudocode for the buffer contents injected into user message
"""
## Recent Context (from WhatsApp group "Family Chat")
(last 5 minutes, 12 messages)

**Dov:** Just landed at JFK, customs was insane
**Sarah:** Safe travels! We'll pick you up
**Dov:** ETA 45 min, need to grab luggage first
**Mom:** I'm making pasta tonight 🍝
**[Image: photo of airport terminal — crowded, many people in line]

**Summary of earlier today:** Family coordinated airport pickup. Dov's flight arrived at 3pm. Sarah driving, Mom cooking dinner.
"""
```

### 4.3 Population Pipeline

**What writes to the buffer, when:**

1. **On each LLM turn** (via `pre_llm_call` hook):
   - Query session transcript for messages since last LLM response
   - Add new messages to the sliding window
   - If window exceeds token budget, evict oldest messages into summary
   - If summary exceeds budget, compress summary further (or drop oldest)

2. **Image handling:**
   - Reference images from `~/.hermes/image_cache/` by path
   - Include alt text / pre-analysis from observe pipeline
   - Max 3 recent images to control token usage

3. **Summary generation:**
   - When messages are evicted from the window, append a compressed summary
   - Use a fast/cheap model (same as context compression) for summarization
   - OR use simple extractive summarization (key facts, names, topics) for zero-cost

### 4.4 Retrieval Mechanism

**How the agent reads from it:**

The buffer is injected into the user message via the `pre_llm_call` hook:

```python
def pre_llm_call(ctx):
    # Get the live context buffer for the current session
    buffer = get_live_context_buffer(ctx.session_id)
    
    if not buffer.has_content():
        return None  # No recent context to inject
    
    # Format the buffer as a context block
    context_block = format_buffer(buffer)
    
    # Return as context injection (Hermes prepends to user message)
    return {"context": context_block}
```

**Formatting rules:**
- Header: `## Recent Context (from {platform} "{chat_name}")`
- Time window: `(last {N} minutes, {M} messages)`
- Messages: `**{sender}:** {message}` (name + content, no timestamps for brevity)
- Images: `[Image: {alt_text}]` or `[Image: {description}]`
- Summary: `**Summary of earlier:** {compressed_summary}`
- Total block capped at ~400 tokens

### 4.5 Token Overhead Estimate

| Component | Tokens | Notes |
|-----------|--------|-------|
| Header + metadata | ~20 | Platform name, chat name, time window |
| Recent messages (10-15) | ~250-350 | Average 20-25 tokens/message |
| Image references (2-3) | ~30-50 | Alt text + path reference |
| Summary of older context | ~50-100 | Compressed to key facts |
| **Total** | **~350-500** | **Within 500 token budget** |

### 4.6 Hermes Components Affected

| Component | Change Type | Description |
|-----------|-------------|-------------|
| `plugins/live_context/` | **New plugin** | `pre_llm_call` hook implementing the buffer |
| `config.yaml` | **New config section** | `live_context:` settings (window size, summary model, etc.) |
| Session transcript | **Read-only** | Buffer reads from existing session data — no changes needed |
| Image cache | **Read-only** | Buffer references existing cached images — no changes needed |
| `context_compressor.py` | **No changes** | Buffer operates independently of compression |

---

## 5. Configuration

```yaml
# ~/.hermes/config.yaml
live_context:
  enabled: true
  window:
    max_messages: 15        # Max messages in the sliding window
    max_tokens: 400         # Token budget for the entire buffer
    time_window_minutes: 30 # Only include messages from last N minutes
  summary:
    enabled: true
    model: null             # null = use extractive (free), or specify a cheap model
    max_tokens: 100         # Max tokens for the summary portion
  images:
    max_count: 3            # Max recent images to include
    include_descriptions: true  # Include pre-analysis from observe pipeline
  platforms:
    whatsapp: true          # Enable for WhatsApp observe contexts
    discord: true           # Enable for Discord (supplements existing backfill)
    telegram: true          # Enable for Telegram observe contexts
    imessage: true          # Enable for iMessage group contexts
```

---

## 6. Phased Implementation Plan

### Phase 1: Foundation (1-2 days)
**Goal:** Basic sliding window buffer via `pre_llm_call` plugin

1. Create `plugins/live_context/__init__.py` with the plugin skeleton
2. Implement `pre_llm_call` hook that:
   - Reads session transcript for recent messages
   - Applies time window filter (last N minutes)
   - Formats as context block
   - Returns via `{"context": block}`
3. Add `live_context:` config section with defaults
4. Test with WhatsApp group chat

**Deliverable:** Working plugin that injects last 15 messages (~300 tokens) into user message.

### Phase 2: Summary Layer (2-3 days)
**Goal:** Add running summary for messages outside the window

1. Implement extractive summarization (zero-cost):
   - Extract key entities (names, places, topics)
   - Extract action items and decisions
   - Extract sentiment/urgency signals
2. Implement sliding window eviction:
   - When messages exceed `max_tokens`, evict oldest into summary
   - Summary accumulates: `Earlier: {summary}. Now: {window}`
3. Add summary compression when summary exceeds budget
4. Test with longer conversations (30+ minutes of observed context)

**Deliverable:** Buffer with summary layer, maintaining <500 token overhead over 30+ minute windows.

### Phase 3: Image Integration (1 day)
**Goal:** Include recent images with pre-analysis

1. Reference images from `~/.hermes/image_cache/`
2. Include pre-analysis text from observe pipeline
3. Cap at `max_count` images
4. Test with image-heavy conversations

**Deliverable:** Buffer includes recent image descriptions.

### Phase 4: Multi-Platform & Polish (1-2 days)
**Goal:** Works across all observe-capable platforms

1. Generalize from WhatsApp to all platforms
2. Add per-platform config overrides
3. Handle edge cases:
   - Empty sessions
   - Very long messages (truncate)
   - Non-text content (reactions, voice memos)
4. Add observability (token count logging)
5. Write documentation

**Deliverable:** Production-ready plugin with docs.

### Phase 5: Advanced Features (optional, future)
**Goal:** Smart context management

1. **Priority scoring**: Weight messages by relevance (mentions, questions, decisions)
2. **Topic detection**: Group messages by topic, summarize per-topic
3. **Entity tracking**: Maintain running entity list across the buffer
4. **Adaptive window**: Adjust window size based on conversation density
5. **Cross-session bridges**: Link related conversations across sessions

---

## 7. Comparison with Existing Discord Backfill

| Aspect | Discord Backfill | Live Context Buffer (Proposed) |
|--------|------------------|-------------------------------|
| Trigger | On mention only | Every LLM turn |
| Source | Discord API scrollback | Session transcript (all platforms) |
| Window | Configurable limit (default 50) | Configurable + token-aware |
| Summary | None (raw messages only) | Running summary of older context |
| Images | Not included | Included with pre-analysis |
| Platforms | Discord only | All observe-capable platforms |
| Token budget | None (can be large) | Hard cap at 500 tokens |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Token budget overrun** | Context window pressure | Hard cap at 500 tokens; evict oldest first |
| **Summary quality** | Misleading context | Use extractive (not generative) summary; low risk |
| **Plugin failure** | Agent runs without context | Fail-open design; hook returns None on error |
| **Duplicate context** | Same info in window + summary | Deduplication on eviction; message IDs |
| **Stale context** | Old info injected | Time window filter; configurable TTL |
| **Performance** | Slow pre_llm_call | Session transcript is in-memory SQLite; fast |

---

## 9. Success Criteria

1. **Token overhead < 500 tokens/turn** — measured via `/usage` during session
2. **"What just happened" works** — ask about recent context, agent answers from buffer
3. **No degradation** — existing features (compression, memory, tools) unaffected
4. **Cross-platform** — works on WhatsApp, Discord, Telegram, iMessage
5. **Configurable** — users can tune window size, summary, images per platform

---

## 10. References

- **LangChain ConversationSummaryBufferMemory**: Hybrid buffer + summary pattern
- **Active Context Compression (arXiv:2601.07190)**: Agent-controlled compression architecture
- **AgentRM (arXiv:2603.13110)**: OS-inspired context scheduling
- **TokenMizer (arXiv:2606.06337)**: Graph-structured session memory
- **Hermes Discord History Backfill**: Existing pattern to generalize
- **Hermes pre_llm_call Hook**: Integration point for context injection
- **Hermes Context Engine Plugin**: Alternative integration point (not recommended for this use case)

---

## Appendix A: Token Budget Math

Assuming a 128K context window:
- System prompt: ~3K tokens
- Skills + memory: ~2K tokens
- Conversation history: ~10K tokens (typical)
- **Live context buffer: ~500 tokens** (this proposal)
- Tool schemas: ~2K tokens
- Available for response: ~110K tokens

The 500-token buffer represents **0.39%** of a 128K context window — negligible impact on response capacity.

## Appendix B: Implementation Sketch

```python
# plugins/live_context/__init__.py

from hermes.plugins import Plugin
from hermes.tools import session_search

class LiveContextPlugin(Plugin):
    name = "live_context"
    
    def __init__(self):
        self.buffers = {}  # session_id -> buffer state
    
    def pre_llm_call(self, ctx):
        """Inject recent observed context into the user message."""
        session_id = ctx.session_id
        config = ctx.config.get("live_context", {})
        
        if not config.get("enabled", True):
            return None
        
        # Get or create buffer for this session
        buffer = self._get_or_create_buffer(session_id, config)
        
        # Refresh buffer from session transcript
        self._refresh_buffer(buffer, ctx, config)
        
        if not buffer.has_content():
            return None
        
        # Format and return
        return {"context": buffer.format()}
    
    def _refresh_buffer(self, buffer, ctx, config):
        """Update buffer with new messages from session transcript."""
        # Query recent messages from session transcript
        # Add to sliding window
        # Evict old messages to summary if needed
        # Update image references
        pass
```
