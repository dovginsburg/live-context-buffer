"""
Live Context Buffer Plugin — Phase 5 (Complete)
================================================

Injects recent observed chat context into the current turn via the
``pre_llm_call`` hook.  Generalizes Discord's ``history_backfill``
pattern to all platforms (WhatsApp, Telegram, iMessage, etc.).

Phases:
  Phase 1: Sliding window of recent messages (verbatim)
  Phase 2: Extractive summary of older messages (zero-cost)
  Phase 3: Image description injection from cached images
  Phase 4: Per-platform config overrides, edge case hardening, observability
  Phase 5: Priority scoring, adaptive window, entity tracking

Config (in config.yaml):
    live_context:
      enabled: true
      max_messages: 15
      max_tokens: 400
      time_window_minutes: 30
      min_messages: 3
      summary:
        enabled: true
        max_tokens: 80
        min_messages: 3
      images:
        max_count: 3
        max_tokens: 60
      platforms:
        whatsapp: {}
        discord:
          enabled: false
        telegram: {}
        imessage: {}
      smart:
        priority_scoring: true    # Boost important messages in window
        adaptive_window: true     # Adjust window size by density
        entity_tracking: true     # Track active participants
        entity_header: true       # Show entity line in context block
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rough token estimator
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    words = len(text.split())
    return int(words * 1.3) + len(text) // 100


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _get_config() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        config = load_config()
        return config.get("live_context") or {}
    except Exception:
        return {}


def _is_enabled(config: Dict[str, Any]) -> bool:
    enabled = config.get("enabled", True)
    if isinstance(enabled, str):
        return enabled.lower() not in {"false", "0", "no", "off"}
    return bool(enabled)


def _resolve_platform_config(config: Dict[str, Any], platform: str) -> Dict[str, Any]:
    platforms = config.get("platforms") or {}
    if not isinstance(platforms, dict):
        platforms = {}
    plat_key = (platform or "").lower().split(":")[0].strip()
    override = platforms.get(plat_key) or {}
    if not isinstance(override, dict):
        override = {}

    merged = {k: v for k, v in config.items() if k not in ("platforms", "summary", "images", "smart")}
    merged.update(override)

    for section in ("summary", "images", "smart"):
        global_section = config.get(section) or {}
        platform_section = override.get(section) or {}
        if isinstance(global_section, dict) and isinstance(platform_section, dict):
            merged[section] = {**global_section, **platform_section}
        elif isinstance(platform_section, dict):
            merged[section] = platform_section
        else:
            merged[section] = global_section

    return merged


def _get_max_messages(config: Dict[str, Any]) -> int:
    return int(config.get("max_messages", 15))


def _get_max_tokens(config: Dict[str, Any]) -> int:
    return int(config.get("max_tokens", 400))


def _get_time_window_minutes(config: Dict[str, Any]) -> int:
    return int(config.get("time_window_minutes", 30))


def _get_min_messages(config: Dict[str, Any]) -> int:
    return int(config.get("min_messages", 3))


def _get_summary_config(config: Dict[str, Any]) -> Dict[str, Any]:
    s = config.get("summary") or {}
    if not isinstance(s, dict):
        s = {}
    return {
        "enabled": s.get("enabled", True),
        "max_tokens": int(s.get("max_tokens", 80)),
        "min_messages": int(s.get("min_messages", 3)),
    }


def _get_images_config(config: Dict[str, Any]) -> Dict[str, Any]:
    img = config.get("images") or {}
    if not isinstance(img, dict):
        img = {}
    return {
        "max_count": int(img.get("max_count", 3)),
        "max_tokens": int(img.get("max_tokens", 60)),
    }


def _get_smart_config(config: Dict[str, Any]) -> Dict[str, Any]:
    s = config.get("smart") or {}
    if not isinstance(s, dict):
        s = {}
    return {
        "priority_scoring": s.get("priority_scoring", True),
        "adaptive_window": s.get("adaptive_window", True),
        "entity_tracking": s.get("entity_tracking", True),
        "entity_header": s.get("entity_header", True),
    }


# ---------------------------------------------------------------------------
# Message extraction helpers
# ---------------------------------------------------------------------------

_DECISION_MARKERS = re.compile(
    r"\b(let'?s|i'?ll|we should|we'?ll|i will|you should|"
    r"plan is|going to|decided|agreed|confirmed|schedule|"
    r"meet at|call at|send|pick up|bring|cancel|reschedule)\b",
    re.IGNORECASE,
)

_QUESTION_RE = re.compile(r"\?")

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "don", "now", "and", "but", "or", "if", "while", "that", "this",
    "these", "those", "it", "its", "i", "me", "my", "myself", "we",
    "our", "ours", "ourselves", "you", "your", "yours", "he", "him",
    "his", "she", "her", "hers", "they", "them", "their", "what", "which",
    "who", "whom", "about", "up", "also", "like", "yeah", "ok", "okay",
    "sure", "right", "well", "oh", "hey", "hi", "hello", "thanks",
    "thank", "lol", "haha", "gonna", "wanna", "gotta", "kinda",
    "https", "http", "com", "www", "图片", "image",
})

_WHATSAPP_IMAGE_RE = re.compile(
    r"\[The user sent an image[~!]\s*(?:Here.s what I can see:\s*)?",
    re.IGNORECASE,
)
_CACHED_IMAGE_RE = re.compile(
    r"(img_[a-f0-9]{8,16}\.(?:jpg|jpeg|png|webp|gif))",
    re.IGNORECASE,
)
_IMAGE_INLINE_RE = re.compile(
    r"\[image:\s*([^\]]+)\]",
    re.IGNORECASE,
)

_REACTION_RE = re.compile(
    r"^(?:[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF"
    r"\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    r"\u2600-\u26FF\u2700-\u27BF]|[\w\s]{0,3})$",
    re.UNICODE,
)
_VOICE_MEMO_RE = re.compile(
    r"^\s*(?:\ud83c\udfa4|voice message|audio message|voice memo)\s*$",
    re.IGNORECASE,
)
_SYSTEM_CONTENT_RE = re.compile(
    r"^\s*\[(?:system|notification|info|meta)\]",
    re.IGNORECASE,
)


def _is_reaction_or_trivial(content: str) -> bool:
    stripped = content.strip()
    if len(stripped) <= 3:
        return True
    if _REACTION_RE.match(stripped):
        return True
    if _VOICE_MEMO_RE.match(stripped):
        return True
    if _SYSTEM_CONTENT_RE.match(stripped):
        return True
    return False


# Patterns observed in conversation_history user content across platforms.
# Order matters — try the most specific (group-observer pipe form) first,
# then fall back to the legacy display-name-only form.
#
# group_observer.py:_attributed_text produces
#     "[display_name|user_id]\n<text>"
# so the captured sender group is "display_name|user_id". Stripping the
# "|user_id" suffix gives us the human-readable display name and lets the
# entity-tracking Counter and formatted-window lines speak in real names
# ("Levi" instead of "Levi|30533643984944@lid"). Without this, every
# priority-score lookup against entity_counts uses a unique long key,
# so the frequent-participant bonus never fires and Levi's short
# answer gets pushed out of the window into the summary.
_SENDER_PIPE_RE = re.compile(r'^\[([^\]|]+)\|[^\]]+\]\s*(.*)', re.DOTALL)
_SENDER_PLAIN_RE = re.compile(r'^\[([^\]]+)\]\s*(.*)', re.DOTALL)


def _extract_sender_from_content(content: str) -> Tuple[str, str]:
    # Try the most specific form first: "[display_name|user_id]".
    # The pipe-regex requires at least one char in the display-name slot
    # ([^\]|]+), so an empty-name form like "[|abc@lid]" falls through
    # to the plain form, which returns "|abc@lid" verbatim — acceptable
    # as a raw identifier (no real conversation produces this anyway).
    m = _SENDER_PIPE_RE.match(content)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = _SENDER_PLAIN_RE.match(content)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", content


def _raw_text(msg: Dict[str, Any]) -> str:
    content = msg.get("content", "")
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
            elif isinstance(part, str):
                parts.append(part)
        content = " ".join(parts)
    return content or ""


def _format_message(msg: Dict[str, Any]) -> Optional[str]:
    role = msg.get("role", "")
    content = msg.get("content", "")

    if role != "user":
        return None
    if not content or not content.strip():
        return None
    if len(content.strip()) < 3:
        return None
    if content.startswith("(The user sent") or content.startswith("[Recent context"):
        return None
    if _WHATSAPP_IMAGE_RE.search(content):
        return None

    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
            elif isinstance(part, str):
                text_parts.append(part)
        content = " ".join(text_parts)

    if not content or not content.strip():
        return None
    if _is_reaction_or_trivial(content):
        return None

    sender, text = _extract_sender_from_content(content)
    if _IMAGE_INLINE_RE.match(text.strip()):
        return None
    if sender and _IMAGE_INLINE_RE.match(f"[{sender}]"):
        return None

    max_msg_len = 300
    if len(text) > max_msg_len:
        text = text[:max_msg_len] + "…"

    if sender:
        return f"**{sender}:** {text}"
    else:
        return f"**User:** {text}"


# ---------------------------------------------------------------------------
# Phase 5: Priority scoring
# ---------------------------------------------------------------------------

def _score_message(msg: Dict[str, Any], entity_counts: Counter) -> float:
    """Score a message by importance. Higher = more important.
    
    Scoring signals:
      - Contains a question (+2)
      - Contains a decision/action (+2)
      - Mentions the agent ("Ezra", "@Ezra") (+3)
      - Contains an image (+1)
      - Sent by a frequent participant (+1)
      - Longer message (more substantive) (+0.5)
      - Contains a URL/link (+1)
    """
    raw = _raw_text(msg)
    if not raw:
        return 0.0

    score = 0.0

    # Questions are high-signal
    if _QUESTION_RE.search(raw):
        score += 2.0

    # Decisions/actions are high-signal
    if _DECISION_MARKERS.search(raw):
        score += 2.0

    # Agent mentions (highest priority)
    raw_lower = raw.lower()
    if "ezra" in raw_lower or "@ezra" in raw_lower:
        score += 3.0

    # Image references
    if _CACHED_IMAGE_RE.search(raw) or _IMAGE_INLINE_RE.search(raw):
        score += 1.0

    # Frequent participant bonus
    sender, _ = _extract_sender_from_content(raw)
    if sender and entity_counts.get(sender, 0) >= 3:
        score += 1.0

    # Substantive length (longer = more likely important)
    if len(raw) > 100:
        score += 0.5

    # URLs (informational)
    if "http" in raw_lower:
        score += 1.0

    return score


# ---------------------------------------------------------------------------
# Phase 5: Adaptive window
# ---------------------------------------------------------------------------

def _compute_adaptive_max_messages(
    conversation_history: List[Dict[str, Any]],
    base_max: int,
    time_window_minutes: int,
) -> int:
    """Adjust window size based on conversation density.
    
    High density (many messages/min) → shrink window (more noise)
    Low density (few messages/min) → expand window (more signal)
    
    Range: base_max * 0.5 to base_max * 1.5
    """
    if time_window_minutes <= 0:
        return base_max

    now = time.time()
    cutoff = now - (time_window_minutes * 60)

    # Count recent user messages
    recent_count = 0
    for msg in conversation_history:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        msg_ts = msg.get("timestamp")
        if msg_ts:
            try:
                if isinstance(msg_ts, (int, float)) and msg_ts >= cutoff:
                    recent_count += 1
            except (TypeError, ValueError):
                pass

    # Messages per minute
    msgs_per_min = recent_count / max(time_window_minutes, 1)

    # Adaptive scaling:
    #   < 0.5 msgs/min (quiet)  → expand to 1.5x
    #   0.5-2 msgs/min (normal) → keep base
    #   > 2 msgs/min (busy)     → shrink to 0.5x
    if msgs_per_min < 0.5:
        scale = 1.5
    elif msgs_per_min > 2.0:
        # Scale down proportionally, minimum 0.5x
        scale = max(0.5, 2.0 / msgs_per_min)
    else:
        scale = 1.0

    adaptive = int(base_max * scale)
    return max(3, adaptive)  # Never go below 3


# ---------------------------------------------------------------------------
# Phase 5: Entity tracking
# ---------------------------------------------------------------------------

def _extract_entities_from_window(window_msg_dicts: List[Dict[str, Any]]) -> Counter:
    """Extract and count participant names from window messages."""
    entities: Counter = Counter()
    for msg in window_msg_dicts:
        raw = _raw_text(msg)
        sender, _ = _extract_sender_from_content(raw)
        if sender:
            entities[sender] += 1
    return entities


def _format_entity_header(entities: Counter) -> str:
    """Format the entity tracking line."""
    if not entities:
        return ""
    top = entities.most_common(5)
    names = [f"{n}({c})" for n, c in top]
    return f"Active: {', '.join(names)}"


# ---------------------------------------------------------------------------
# Image reference extraction (Phase 3)
# ---------------------------------------------------------------------------

def _extract_image_references(content: str) -> List[Dict[str, str]]:
    refs: List[Dict[str, str]] = []

    wa_match = _WHATSAPP_IMAGE_RE.search(content)
    if wa_match:
        desc_start = wa_match.end()
        desc = content[desc_start:desc_start + 300].strip()
        desc = re.split(r'\n\n|\*\*Overview\*\*|\*\*Header', desc)[0].strip()
        if len(desc) > 150:
            desc = desc[:150] + "…"
        file_match = _CACHED_IMAGE_RE.search(content)
        refs.append({
            "type": "whatsapp",
            "path": file_match.group(1) if file_match else "",
            "description": desc,
        })
        return refs

    for m in _CACHED_IMAGE_RE.finditer(content):
        refs.append({"type": "cached", "path": m.group(1), "description": ""})

    for m in _IMAGE_INLINE_RE.finditer(content):
        refs.append({"type": "inline", "path": "", "description": m.group(1).strip()[:100]})

    return refs


def _format_image_ref(ref: Dict[str, str]) -> str:
    if ref["type"] == "whatsapp" and ref["description"]:
        desc = ref["description"]
        if len(desc) > 120:
            desc = desc[:120] + "…"
        return f"[Image] {desc}"
    elif ref["type"] == "cached" and ref["path"]:
        return f"[Image: {ref['path']}]"
    elif ref["type"] == "inline" and ref["description"]:
        return f"[Image: {ref['description']}]"
    return ""


def _collect_recent_images(
    conversation_history: List[Dict[str, Any]],
    max_count: int = 3,
    max_tokens: int = 60,
) -> List[str]:
    images: List[str] = []
    token_budget = max_tokens

    for msg in reversed(conversation_history):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue

        content = _raw_text(msg)
        if not content:
            continue

        refs = _extract_image_references(content)
        for ref in refs:
            formatted = _format_image_ref(ref)
            if not formatted:
                continue

            tokens = _estimate_tokens(formatted)
            if len(images) >= 2 and tokens > token_budget:
                break

            token_budget -= tokens
            images.append(formatted)

            if len(images) >= max_count:
                return images

    return images


# ---------------------------------------------------------------------------
# Extractive summarization (Phase 2)
# ---------------------------------------------------------------------------

def _extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    filtered = [w for w in words if w not in _STOP_WORDS and len(w) >= 3]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(max_keywords)]


def _extract_decisions(text: str) -> List[str]:
    decisions = []
    sentences = re.split(r'[.!?]+', text)
    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 10:
            continue
        if _DECISION_MARKERS.search(sent):
            if len(sent) > 80:
                sent = sent[:80] + "…"
            decisions.append(sent)
    return decisions[:3]


def _has_image_reference(text: str) -> bool:
    return bool(_CACHED_IMAGE_RE.search(text) or _IMAGE_INLINE_RE.search(text) or _WHATSAPP_IMAGE_RE.search(text))


def _summarize_messages(
    messages: List[Dict[str, Any]],
    max_tokens: int = 80,
) -> str:
    if not messages:
        return ""

    participants: Counter = Counter()
    all_keywords: Counter = Counter()
    all_decisions: List[str] = []
    image_count = 0
    msg_count = 0

    for msg in messages:
        raw = _raw_text(msg)
        if not raw:
            continue
        msg_count += 1

        sender, _ = _extract_sender_from_content(raw)
        if sender:
            participants[sender] += 1
        else:
            participants["others"] += 1

        kws = _extract_keywords(raw, max_keywords=3)
        for kw in kws:
            all_keywords[kw] += 1

        decs = _extract_decisions(raw)
        all_decisions.extend(decs)

        if _has_image_reference(raw):
            image_count += 1

    if msg_count == 0:
        return ""

    parts = []
    token_budget = max_tokens

    if participants:
        top = participants.most_common(4)
        names = [f"{n}({c})" for n, c in top]
        participant_line = f"Participants: {', '.join(names)}"
        t = _estimate_tokens(participant_line)
        if t <= token_budget:
            parts.append(participant_line)
            token_budget -= t

    top_topics = [w for w, c in all_keywords.most_common(5) if c >= 1]
    if top_topics:
        topic_line = f"Topics: {', '.join(top_topics)}"
        t = _estimate_tokens(topic_line)
        if t <= token_budget:
            parts.append(topic_line)
            token_budget -= t

    if all_decisions:
        dec_text = "; ".join(all_decisions[:2])
        dec_line = f"Decisions: {dec_text}"
        t = _estimate_tokens(dec_text)
        if t <= token_budget:
            parts.append(dec_line)
            token_budget -= t

    if image_count > 0:
        img_line = f"Media: {image_count} image(s) shared"
        t = _estimate_tokens(img_line)
        if t <= token_budget:
            parts.append(img_line)
            token_budget -= t

    if not parts:
        return f"{msg_count} earlier messages"

    return ". ".join(parts)


# ---------------------------------------------------------------------------
# Context block builder
# ---------------------------------------------------------------------------

def _build_context_block(
    window_messages: List[str],
    summary: str,
    images: List[str],
    entity_line: str,
    total_tokens: int,
    total_available: int,
    window_count: int,
    summary_count: int,
    platform: str = "",
    adaptive_max: int = 0,
) -> str:
    lines = []

    parts = []
    if summary_count > 0:
        parts.append(f"{summary_count} earlier")
    parts.append(f"last {window_count} messages")
    if images:
        parts.append(f"{len(images)} image(s)")
    header = f"## Recent Context ({', '.join(parts)}, ~{total_tokens} tokens)"
    lines.append(header)
    lines.append("")

    # Entity tracking (Phase 5)
    if entity_line:
        lines.append(f"**{entity_line}**")
        lines.append("")

    if summary:
        lines.append(f"**Earlier:** {summary}")
        lines.append("")

    if images:
        lines.append("**Recent images:**")
        for img in images:
            lines.append(f"  {img}")
        lines.append("")

    if window_messages:
        lines.append("**Now:**")
        lines.extend(window_messages)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main hook
# ---------------------------------------------------------------------------

def on_pre_llm_call(
    *,
    session_id: str = "",
    task_id: str = "",
    turn_id: str = "",
    user_message: Any = None,
    conversation_history: Any = None,
    is_first_turn: bool = False,
    model: str = "",
    platform: str = "",
    sender_id: str = "",
    **kwargs: Any,
) -> Optional[Dict[str, str]]:
    """Inject recent observed context into the current turn.

    Phase 5: Priority scoring, adaptive window, entity tracking.
    """
    if not conversation_history or not isinstance(conversation_history, list):
        return None

    raw_config = _get_config()
    if not _is_enabled(raw_config):
        return None
    config = _resolve_platform_config(raw_config, platform)

    if not _is_enabled(config):
        return None

    max_messages = _get_max_messages(config)
    max_tokens = _get_max_tokens(config)
    time_window_minutes = _get_time_window_minutes(config)
    min_messages = _get_min_messages(config)
    summary_cfg = _get_summary_config(config)
    summary_enabled = summary_cfg["enabled"]
    summary_max_tokens = summary_cfg["max_tokens"]
    summary_min_messages = summary_cfg["min_messages"]
    images_cfg = _get_images_config(config)
    images_max_count = images_cfg["max_count"]
    images_max_tokens = images_cfg["max_tokens"]
    smart_cfg = _get_smart_config(config)
    priority_scoring = smart_cfg["priority_scoring"]
    adaptive_window = smart_cfg["adaptive_window"]
    entity_tracking = smart_cfg["entity_tracking"]
    entity_header = smart_cfg["entity_header"]

    # Phase 5: Adaptive window
    if adaptive_window:
        effective_max = _compute_adaptive_max_messages(
            conversation_history, max_messages, time_window_minutes,
        )
    else:
        effective_max = max_messages

    now = time.time()
    cutoff = now - (time_window_minutes * 60) if time_window_minutes > 0 else 0

    # ── Pass 0: Pre-scan for entity counts (needed for scoring) ──
    entity_counts: Counter = Counter()
    if priority_scoring or entity_tracking:
        for msg in conversation_history:
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            raw = _raw_text(msg)
            sender, _ = _extract_sender_from_content(raw)
            if sender:
                entity_counts[sender] += 1

    # ── Pass 1: Classify messages with priority scoring ──
    candidates: List[Tuple[float, int, str, Dict[str, Any]]] = []  # (score, order, formatted, dict)
    older_msg_dicts: List[Dict[str, Any]] = []
    total_user_msgs = 0
    skipped_trivial = 0
    summary_budget = summary_max_tokens if summary_enabled else 0

    for msg in reversed(conversation_history):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue

        total_user_msgs += 1
        if total_user_msgs == 1:
            continue

        formatted = _format_message(msg)
        if not formatted:
            raw = _raw_text(msg)
            if raw and _is_reaction_or_trivial(raw):
                skipped_trivial += 1
            continue

        within_time_window = True
        msg_ts = msg.get("timestamp")
        if msg_ts and cutoff > 0:
            try:
                if isinstance(msg_ts, (int, float)):
                    within_time_window = msg_ts >= cutoff
            except (TypeError, ValueError):
                pass

        if within_time_window:
            # Score for priority
            score = _score_message(msg, entity_counts) if priority_scoring else 0.0
            # Recency boost: newer messages get higher score
            if msg_ts and isinstance(msg_ts, (int, float)):
                age_minutes = (now - msg_ts) / 60
                recency_boost = max(0, 3.0 - (age_minutes / time_window_minutes * 3.0)) if time_window_minutes > 0 else 0
                score += recency_boost
            # Dov 2026-06-16: guaranteed slot for the immediate predecessor
            # of the current turn. The thing that came RIGHT BEFORE the
            # user is almost always what the user is reacting to — Levi's
            # "Sleep" answer to "what's better than sex?" was the second
            # message in the window (total_user_msgs==2) and got dropped
            # by score competition in a 13-message conversation even
            # though it was the entire point of the question. The
            # predecessor boost adds +5 (well above any other signal)
            # so the most-recent non-current message always wins a
            # window slot. Fallback: if a predecessor is filtered out
            # (truncated/empty), the next one upstream takes the slot.
            if total_user_msgs == 2:
                score += 5.0
            candidates.append((score, total_user_msgs, formatted, msg))
        else:
            older_msg_dicts.append(msg)

    # Sort by score descending (highest priority first)
    if priority_scoring:
        candidates.sort(key=lambda x: x[0], reverse=True)

    # Select top N candidates that fit in token budget
    window_messages: List[str] = []
    window_msg_dicts: List[Dict[str, Any]] = []
    token_budget = max_tokens

    for score, order, formatted, msg in candidates:
        msg_tokens = _estimate_tokens(formatted)
        available_for_window = token_budget - summary_budget
        fits = len(window_messages) < min_messages or msg_tokens <= available_for_window

        if fits and len(window_messages) < effective_max:
            token_budget -= msg_tokens
            window_messages.append(formatted)
            window_msg_dicts.append(msg)
        else:
            older_msg_dicts.append(msg)

    # Re-sort window messages by original order (chronological)
    if priority_scoring and window_messages:
        # Rebuild with original order for chronological display
        ordered = [(o, f) for _, o, f, _ in candidates if f in window_messages]
        ordered.sort(key=lambda x: x[0])
        window_messages = [f for _, f in ordered]

    # ── Pass 2: Summary ──
    summary = ""
    if summary_enabled and len(older_msg_dicts) >= summary_min_messages:
        summary = _summarize_messages(older_msg_dicts, max_tokens=summary_max_tokens)
        summary_tokens = _estimate_tokens(summary)
    else:
        summary_tokens = 0

    if not window_messages and not summary:
        return None

    # ── Pass 3: Images ──
    images = _collect_recent_images(
        conversation_history,
        max_count=images_max_count,
        max_tokens=images_max_tokens,
    )

    # ── Pass 4: Entity tracking ──
    entity_line = ""
    if entity_tracking and entity_header:
        window_entities = _extract_entities_from_window(window_msg_dicts)
        entity_line = _format_entity_header(window_entities)

    window_messages.reverse()

    window_tokens = max_tokens - token_budget
    total_tokens = window_tokens + summary_tokens + _estimate_tokens("\n".join(images))

    logger.debug(
        "[live_context] platform=%s window=%d/%d older=%d images=%d "
        "entities=%d skipped_trivial=%d total_tokens=%d/%d",
        platform or "unknown",
        len(window_messages), effective_max,
        len(older_msg_dicts),
        len(images),
        len(entity_counts),
        skipped_trivial,
        total_tokens,
        max_tokens,
    )

    block = _build_context_block(
        window_messages=window_messages,
        summary=summary,
        images=images,
        entity_line=entity_line,
        total_tokens=total_tokens,
        total_available=total_user_msgs,
        window_count=len(window_messages),
        summary_count=len(older_msg_dicts),
        platform=platform,
        adaptive_max=effective_max,
    )

    return {"context": block}


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register(ctx: Any) -> None:
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    logger.debug("[live_context] Plugin registered — pre_llm_call hook active (Phase 5: smart)")
