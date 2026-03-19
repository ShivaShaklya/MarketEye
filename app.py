"""
MarketEye - Flask Application
Routes only - all business logic delegated to chat_orchestration
"""

import sys
import os

# Add Backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend'))

from flask import Flask, render_template, request, jsonify
from Backend.chat_orchestration import start_chat, process_message
import uuid

# app = Flask(__name__)
app = Flask(
    __name__,
    template_folder='Frontend/templates',
    static_folder='Frontend/static'
)



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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
