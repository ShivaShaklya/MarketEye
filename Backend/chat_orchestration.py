"""
Chat Orchestration - Flask Web Adapter
Only TWO public functions: start_chat(), process_message()
"""

import json
from chat_store import create_chat, save_chat, add_turn, load_chat
from query_processing import preprocess_query, idea_confirmation, apply_user_edits, get_constraints_from_query
from constraint_handling import STAGE_GUIDANCE, NUMERIC_CLARIFIABLE, needs_numeric_clarification, is_quantifiable_feature, has_numeric_value
from report import create_persona, create_market_overview
from rag_pipeline import run_rag, format_rag_summary

# =============================================================================
# CONSTANTS
# =============================================================================
CONFIRM_WORDS = {"yes", "y", "correct", "looks good", "ok", "okay", "confirm"}
DECLINE_WORDS = {"no", "n", "skip", "later", "not now"}
SKIP_JUSTIFICATION = {"justification"}

# =============================================================================
# HELPERS
# =============================================================================

def _resp(chat, text):
    """Standard response."""
    return {"chat_id": chat["chat_id"], "response": text, "status": chat["status"]}


def _fmt(data, skip=None):
    """Format dict as markdown."""
    return "\n".join(
        f"**{k.replace('_', ' ').title()}**: {', '.join(map(str, v)) if isinstance(v, list) else v}"
        for k, v in data.items() if k not in (skip or set())
    )


def _load(uid, cid):
    """Load chat safely."""
    try:
        return load_chat(f"{uid}_{cid}")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save(chat, status, key=None):
    """Set state and save."""
    chat["status"] = status
    if key:
        chat["_current_key"] = key
    else:
        chat.pop("_current_key", None)
    save_chat(chat)


def _log_understanding(chat, understanding):
    """Log understanding to chat and return formatted text for display."""
    chat["idea_understanding"] = understanding
    add_turn(chat, "assistant", json.dumps(understanding, indent=2))
    return _fmt(understanding, SKIP_JUSTIFICATION)


def _idea_prompt(formatted, is_update=False):
    """Build idea confirmation prompt."""
    prefix = "Updated:" if is_update else "I understood your idea as:"
    suffix = "Is this correct?" if is_update else "Is this correct? Confirm or write changes."
    return f"{prefix}\n\n{formatted}\n\n{suffix}"


# =============================================================================
# PUBLIC API
# =============================================================================

def start_chat(user_id, query):
    """Initialize chat session."""
    chat, chat_id = create_chat(user_id=user_id)
    chat["idea_raw"] = query
    add_turn(chat, "user", query)

    processed, confidence = preprocess_query(query)
    understanding = idea_confirmation(chat, processed, confidence)

    formatted = _log_understanding(chat, understanding)
    _save(chat, "WAITING_IDEA_CONFIRMATION")

    return {"chat_id": chat_id, "user_id": user_id, "response": _idea_prompt(formatted), "status": chat["status"]}


def process_message(user_id, chat_id, msg):
    """Route message by state."""
    chat = _load(user_id, chat_id)
    if not chat:
        return {"error": "Session not found", "response": "Session expired."}

    add_turn(chat, "user", msg)

    handlers = {
        "WAITING_IDEA_CONFIRMATION": _on_idea,
        "WAITING_CONSTRAINTS": _on_constraint,
        "WAITING_NUMERIC_CLARIFICATION": _on_numeric,
        "WAITING_FEATURE_CLARIFICATION": _on_feature,
        "WAITING_RAG_CONFIRMATION": _on_rag_confirmation,
        "MARKET_RESEARCH_READY": lambda c, m: _resp(c, "Report complete! Start new chat."),
    }

    handler = handlers.get(chat.get("status", ""))
    return handler(chat, msg) if handler else _resp(chat, "Error. Start new conversation.")


# =============================================================================
# STATE HANDLERS
# =============================================================================

def _on_idea(chat, msg):
    """Handle idea confirmation/edit."""
    if msg.lower().strip() in CONFIRM_WORDS:
        add_turn(chat, "assistant", "Idea confirmed.")
        get_constraints_from_query(chat)
        _save(chat, "WAITING_CONSTRAINTS")
        return _next_q(chat, "Great! Idea confirmed.\n")

    understanding = apply_user_edits(chat, chat["idea_understanding"], msg)
    formatted = _log_understanding(chat, understanding)
    save_chat(chat)
    return _resp(chat, _idea_prompt(formatted, is_update=True))


def _on_constraint(chat, msg):
    """Store constraint."""
    key = chat.get("_current_key")
    if key and msg.strip():
        chat.setdefault("constraints", {})[key] = msg.strip()
        add_turn(chat, "assistant", f"Noted: {msg.strip()}")
    _save(chat, "WAITING_CONSTRAINTS")
    return _next_q(chat)


def _on_numeric(chat, msg):
    """Handle numeric clarification."""
    key = chat.get("_current_key")
    if key and msg.strip():
        chat["constraints"][key] = msg.strip()
        add_turn(chat, "assistant", f"Updated: {msg.strip()}")
    _save(chat, "WAITING_CONSTRAINTS")
    return _next_q(chat)


def _on_feature(chat, msg):
    """Handle feature clarification."""
    features, clarified, idx = chat.get("_features", []), chat.get("_clarified", []), chat.get("_fidx", 0)
    if idx < len(features):
        feature = features[idx]
        clarified.append(f"{feature} (~{msg.strip()})" if msg.strip() else feature)
        chat["_fidx"], chat["_clarified"] = idx + 1, clarified
        save_chat(chat)
    return _next_feat(chat)


def _on_rag_confirmation(chat, msg):
    """Handle competitor-analysis confirmation."""
    reply = msg.lower().strip()

    if reply in DECLINE_WORDS:
        add_turn(chat, "assistant", "Skipped competitor analysis.")
        _save(chat, "MARKET_RESEARCH_READY")
        return _resp(chat, "No problem. Your report is ready, and you can export the PDF anytime.")

    if reply not in CONFIRM_WORDS:
        return _resp(chat, "Would you like me to run competitor analysis with the RAG pipeline? Reply yes or no.")

    try:
        rag_result = run_rag(chat)
        chat["competitive_analysis"] = rag_result
        summary = format_rag_summary(rag_result)
        add_turn(chat, "assistant", summary)
        _save(chat, "MARKET_RESEARCH_READY")
        return _resp(chat, summary + "\n\nPDF export is still available for this session.")
    except Exception as exc:
        add_turn(chat, "assistant", f"RAG analysis failed: {exc}")
        _save(chat, "MARKET_RESEARCH_READY")
        return _resp(
            chat,
            "The core report is ready, but competitor analysis could not run right now. "
            f"Reason: {exc}"
        )


# =============================================================================
# QUESTION FLOW
# =============================================================================

def _next_q(chat, prefix=""):
    """Find next question."""
    stage = chat["idea_understanding"].get("ideation_stage", "exploration and problem_framing")
    questions = STAGE_GUIDANCE.get(stage, STAGE_GUIDANCE["exploration and problem_framing"])["questions"]
    constraints = chat.get("constraints", {})

    for question in questions:
        key, prompt = question["key"], question["prompt"]

        if key not in constraints:
            _save(chat, "WAITING_CONSTRAINTS", key)
            return _resp(chat, f"{prefix}\n{prompt}")

        value = constraints.get(key, "")
        if key in NUMERIC_CLARIFIABLE and isinstance(value, str) and needs_numeric_clarification(value):
            _save(chat, "WAITING_NUMERIC_CLARIFICATION", key)
            cfg = NUMERIC_CLARIFIABLE[key]
            return _resp(chat, f"{prefix}\nYou mentioned '{value}'.\n{cfg['prompt'].format(value=value)}\n{cfg['examples']}")

    features = constraints.get("special_features", [])
    if features and not chat.get("_features_done"):
        chat["_features"], chat["_clarified"], chat["_fidx"] = features, [], 0
        _save(chat, "WAITING_FEATURE_CLARIFICATION")
        return _next_feat(chat, prefix)

    return _report(chat)


def _next_feat(chat, prefix=""):
    """Next feature clarification."""
    features, clarified, idx = chat.get("_features", []), chat.get("_clarified", []), chat.get("_fidx", 0)

    while idx < len(features):
        feature = features[idx]
        if has_numeric_value(feature) or not is_quantifiable_feature(feature):
            clarified.append(feature)
            idx += 1
            continue
        chat["_fidx"], chat["_clarified"] = idx, clarified
        save_chat(chat)
        return _resp(chat, f"{prefix}\nYou mentioned '{feature}'.\nCould you be more specific?")

    chat["constraints"]["special_features"] = clarified
    chat["_features_done"] = True
    for key in ["_features", "_clarified", "_fidx"]:
        chat.pop(key, None)
    _save(chat, "WAITING_CONSTRAINTS")
    return _report(chat)


# =============================================================================
# REPORT
# =============================================================================

def _report(chat):
    """Generate report."""
    persona = create_persona(chat)
    market = create_market_overview(chat)

    chat["finalized"] = True
    add_turn(chat, "assistant", "Report generated.")
    _save(chat, "WAITING_RAG_CONFIRMATION")

    parts = [
        "## Market Research Report\n",
        "### Idea", _fmt(chat["idea_understanding"], SKIP_JUSTIFICATION),
        "\n### Constraints", _fmt(chat.get("constraints", {})),
        "\n### Customer Persona"
    ]
    for persona_item in persona.get("personas", []):
        parts.extend([
            f"\n**{persona_item.get('name', 'Customer')}** - {persona_item.get('role_or_profile', '')}",
            f"- Need: {persona_item.get('primary_need', 'N/A')}",
            f"- Motivation: {persona_item.get('buying_motivation', 'N/A')}"
        ])
    parts.extend([
        "\n### Market Overview",
        f"**Definition**: {market.get('market_definition', 'N/A')}",
        *[f"- {trend}" for trend in market.get('key_trends', [])],
        "\n---\nWould you like me to run competitor analysis using the RAG pipeline? Reply yes or no."
    ])
    return _resp(chat, "\n".join(parts))
