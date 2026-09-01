"""
Chat Routes — Flask Blueprint for the AI Assistant.

Serves the chat page and provides the AI conversation API.

Page Routes:
    GET /chat — AI Assistant chat page

API Routes:
    POST /api/chat — Send a message and get AI response
"""

from flask import Blueprint, render_template, request, jsonify, session, current_app, send_file
from services.gemini_service import get_gemini_response
from services.tts_service import generate_speech_audio
from models.chat_model import save_chat_message, get_chat_history_by_user


# Create the Blueprint
chat_bp = Blueprint('chat', __name__)

# Maximum allowed message length (characters)
MAX_MESSAGE_LENGTH = 2000


# ============================================================
# Page Route
# ============================================================

@chat_bp.route('/chat')
def chat_page():
    """
    AI Assistant chat page.
    Renders the chat UI. If user is logged in, loads their chat history.
    """
    history = []

    # Load chat history for authenticated users
    if 'user_id' in session:
        db_path = current_app.config['DATABASE']
        raw_history = get_chat_history_by_user(db_path, session['user_id'], limit=30)
        # Convert to list of dicts and reverse so oldest is first
        for entry in reversed(raw_history):
            history.append({
                'message': entry['message'],
                'response': entry['response'],
                'created_at': entry['created_at']
            })

    return render_template('chat.html', history=history)


# ============================================================
# API Route — Chat
# ============================================================

@chat_bp.route('/api/chat', methods=['POST'])
def api_chat():
    """
    POST /api/chat — Send a message to the AI assistant.

    Request JSON:
        { "message": "user question" }

    Response JSON:
        { "response": "AI response", "success": true/false }

    Validation:
        - Message must not be empty
        - Message must not exceed MAX_MESSAGE_LENGTH characters
    """
    data = request.get_json()

    if not data or not data.get('message'):
        return jsonify({
            'response': 'Please enter a message.',
            'success': False
        }), 400

    user_message = data['message'].strip()

    # Validate empty after strip
    if not user_message:
        return jsonify({
            'response': 'Please enter a message.',
            'success': False
        }), 400

    # Validate length
    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            'response': f'Message is too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.',
            'success': False
        }), 400

    # Get AI response from Gemini service
    db_path = current_app.config['DATABASE']
    lang = session.get('lang', 'en')
    result = get_gemini_response(user_message, db_path, lang=lang)

    # Save to chat history if user is authenticated
    if 'user_id' in session:
        save_chat_message(
            db_path=db_path,
            message=user_message,
            response=result['response'],
            user_id=session['user_id']
        )

    return jsonify({
        'response': result['response'],
        'success': result['success']
    })


# ============================================================
# API Route — Text to Speech
# ============================================================

@chat_bp.route('/api/tts', methods=['POST'])
def api_tts():
    """
    POST /api/tts — Generate native multilingual audio (MP3) for text.

    Request JSON:
        { "text": "text to speak", "lang": "mr" | "hi" | "en" }

    Response:
        audio/mpeg binary stream
    """
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    lang = data.get('lang', 'en').strip()

    if not text:
        return jsonify({'error': 'No text provided', 'success': False}), 400

    audio_fp = generate_speech_audio(text=text, lang=lang)
    if not audio_fp:
        return jsonify({'error': 'Audio generation failed', 'success': False}), 500

    res = send_file(
        audio_fp,
        mimetype='audio/mpeg',
        as_attachment=False,
        download_name='speech.mp3'
    )
    res.headers['Cache-Control'] = 'public, max-age=86400'
    return res
