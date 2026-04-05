"""
MarketEye - Flask Application
Routes only - all business logic delegated to chat_orchestration
"""

import sys
import os
from pathlib import Path

# Add Backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend'))

from flask import Flask, render_template, request, jsonify, send_file
from Backend.chat_orchestration import start_chat, process_message
from Backend.chat_store import load_chat, list_chats
import uuid

# app = Flask(__name__)
app = Flask(
    __name__,
    template_folder='Frontend/templates',
    static_folder='Frontend/static'
)

REPORT_OUTPUT_DIR = Path("outputs") / "web_exports"


def _safe_filename(value: str | None) -> str:
    if not value:
        return ""
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value).strip())
    cleaned = cleaned.strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned

@app.route('/')
def index():
    """Serve the main chat interface."""
    return render_template('index.html')


@app.route('/api/chat/start', methods=['POST'])
def api_start_chat():
    """
    Start a new chat session with an initial idea.
    Expects JSON: {"message": "user's idea"}
    Returns: {"response": "...", "user_id": "...", "chat_id": "..."}
    """
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    # Generate a new user ID for this session
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    
    try:
        result = start_chat(user_id, message)
        # Include session identifiers in response for client to store
        result['user_id'] = user_id
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat/message', methods=['POST'])
def api_send_message():
    """
    Send a message to an existing chat session.
    Expects JSON: {"message": "...", "user_id": "...", "chat_id": "..."}
    """
    data = request.get_json()
    message = data.get('message', '').strip()
    user_id = data.get('user_id')
    chat_id = data.get('chat_id')
    
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    if not user_id or not chat_id:
        return jsonify({"error": "No active chat session. Please start a new conversation."}), 400
    
    try:
        result = process_message(user_id, chat_id, message)
        # Include session identifiers in response
        result['user_id'] = user_id
        result['chat_id'] = chat_id
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat/reset', methods=['POST'])
def api_reset_chat():
    """Reset the current chat session."""
    return jsonify({"success": True, "message": "Chat session reset."})


@app.route('/api/chats', methods=['GET'])
def api_list_chats():
    """List saved chats for sidebar history."""
    try:
        return jsonify({"chats": list_chats()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route('/api/chat/<user_id>/<chat_id>', methods=['GET'])
def api_get_chat(user_id, chat_id):
    """Return a full saved chat session."""
    try:
        chat = load_chat(f"{user_id}_{chat_id}")
        return jsonify(chat)
    except FileNotFoundError:
        return jsonify({"error": "Chat session not found."}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route('/api/chat/export/<user_id>/<chat_id>', methods=['GET'])
def api_export_chat_pdf(user_id, chat_id):
    """Generate and download a PDF for an existing chat session."""
    try:
        chat = load_chat(f"{user_id}_{chat_id}")
    except FileNotFoundError:
        return jsonify({"error": "Chat session not found."}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    if not chat.get("finalized"):
        return jsonify({"error": "Report is not ready yet. Complete the chat flow first."}), 400

    try:
        from reporting import ReportGenerator, transform_chat_to_report_payload
    except Exception as exc:
        return jsonify({"error": f"Report dependencies are unavailable: {exc}"}), 500

    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename_root = _safe_filename(user_id) or "marketeye_report"
    output_pdf = REPORT_OUTPUT_DIR / f"{filename_root}.pdf"
    asset_dir = Path("generated_assets") / f"{user_id}_{chat_id}"

    try:
        payload = transform_chat_to_report_payload(chat, asset_dir)
        generator = ReportGenerator()
        generator.generate(payload, output_pdf)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return send_file(
        output_pdf,
        as_attachment=True,
        download_name=output_pdf.name,
        mimetype='application/pdf'
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
