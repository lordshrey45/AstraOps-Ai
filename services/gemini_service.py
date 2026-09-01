"""
Gemini Service — AI integration for the Wari Mitra assistant.

Handles communication with the Google Gemini API, builds
Wari-specific context from application data, and returns
AI responses.

IMPORTANT:
- API key is read from Config (environment variable).
- Never expose the API key to the frontend.
- Never log the API key.
"""

import google.generativeai as genai
from config import Config
from models.schedule_model import get_full_schedule
from models.facility_model import get_all_facilities
from models.schedule_model import get_all_route_points


# ============================================================
# SYSTEM PROMPT — Defines the AI assistant's personality
# ============================================================

WARI_SYSTEM_PROMPT = """You are "AstraOps AI", a helpful digital assistant for pilgrims on the Pandharpur Wari pilgrimage in Maharashtra, India.

YOUR ROLE:
- Help Warkaris (pilgrims) with route information, schedule details, facility locations, medical guidance, and general Wari questions.
- Be warm, respectful, and concise in your responses.
- You speak as a knowledgeable companion, not a medical professional or official authority.

RULES:
1. Use the APPLICATION DATA provided below to answer questions about the route, schedule, and facilities. This data is from the AstraOps AI database.

2. IMPORTANT: All data in this application is DEMO/PLACEHOLDER data. If a user asks about specific real-world locations, schedules, or facilities, clearly state that the current data is for demonstration purposes and may not reflect real conditions.
3. Never invent official Wari information. If you don't know, say so.
4. For medical emergencies, advise the user to use the SOS feature or contact emergency services (112). Do NOT diagnose conditions.
5. For facility questions, reference the facility data provided below.
6. For schedule questions, reference the schedule data provided below.
7. Keep responses concise — typically 2-5 sentences unless the user asks for detail.
8. Never reveal API keys, database details, or internal system architecture.
9. You can respond in English, Hindi, or Marathi based on the user's language.
10. Be culturally respectful of the Wari tradition and Hindu pilgrimage practices.

{context}
"""


def _build_wari_context(db_path):
    """
    Build application context string from database data.
    This gives the AI knowledge of current route, schedule, and facilities.
    """
    context_parts = []

    # Schedule data
    try:
        schedule = get_full_schedule(db_path)
        if schedule:
            schedule_text = "DAILY SCHEDULE (DEMO DATA):\n"
            for s in schedule:
                schedule_text += (
                    f"  Day {s['day_number']}: {s['halt_village']} "
                    f"({s['distance_km']}km, {s['start_time']}-{s['end_time']}) "
                    f"- {s['notes'] or 'No notes'}\n"
                )
            context_parts.append(schedule_text)
    except Exception:
        pass

    # Facilities data
    try:
        facilities = get_all_facilities(db_path)
        if facilities:
            fac_text = "NEARBY FACILITIES (DEMO DATA):\n"
            for f in facilities:
                fac_text += (
                    f"  {f['name']} [{f['type']}] - {f['description'] or 'No description'}\n"
                )
            context_parts.append(fac_text)
    except Exception:
        pass

    # Route points summary
    try:
        points = get_all_route_points(db_path)
        if points:
            unique_days = len(set(p['day_number'] for p in points))
            context_parts.append(
                f"ROUTE SUMMARY (DEMO DATA): {len(points)} waypoints across {unique_days} days, "
                f"from Dehu/Alandi to Pandharpur."
            )
    except Exception:
        pass

    if context_parts:
        return "APPLICATION DATA:\n" + "\n".join(context_parts)
    return "APPLICATION DATA: No data currently available."


def detect_message_language(user_message, default_lang='en'):
    """
    Helper to detect language of user message.
    Priority:
    A. Question language (Devanagari characters -> 'mr'/'hi', English -> 'en')
    B. Fallback to default_lang.
    """
    if not user_message:
        return default_lang or 'en'
    
    # Check for Devanagari characters
    has_devanagari = any('\u0900' <= char <= '\u097f' for char in user_message)
    if has_devanagari:
        marathi_words = ['आहे', 'आलो', 'आहोत', 'नाही', 'करा', 'गेलो', 'झाले', 'केले', 'कसे', 'काय', 'कधी', 'स्थान', 'माहीत']
        if any(w in user_message for w in marathi_words) or default_lang == 'mr':
            return 'mr'
        return 'hi'
    
    # Check for Latin characters (English)
    has_latin = any('a' <= char.lower() <= 'z' for char in user_message)
    if has_latin:
        return 'en'
        
    return default_lang or 'en'


def get_gemini_response(user_message, db_path, lang=None):
    """
    Send a user message to Gemini with Wari context and return the response.

    Args:
        user_message: The user's question/message.
        db_path: Path to the SQLite database for context building.
        lang: Selected language code ('en', 'mr', 'hi').

    Returns:
        dict: {'response': str, 'success': bool, 'error': str or None}
    """
    # Validate API key
    api_key = Config.GEMINI_API_KEY
    if not api_key or api_key == 'your-gemini-api-key-here':
        return {
            'response': (
                'The AI assistant is not configured yet. '
                'Please set a valid Gemini API credential in your environment file (.env) to enable AI responses.\n\n'
                'You can get a free key from https://aistudio.google.com/apikey'
            ),
            'success': False,
            'error': 'API key not configured'
        }

    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)

        # Build Wari-specific context
        context = _build_wari_context(db_path)
        system_instruction = WARI_SYSTEM_PROMPT.format(context=context)

        # Build language instruction based on user question priority & website language fallback
        detected_lang = detect_message_language(user_message, lang)
        lang_name_map = {'en': 'English', 'mr': 'Marathi (मराठी)', 'hi': 'Hindi (हिन्दी)'}
        target_lang_name = lang_name_map.get(detected_lang, 'English')
        fallback_lang_name = lang_name_map.get(lang, 'English')

        system_instruction += (
            f"\n\nRESPONSE LANGUAGE INSTRUCTION:\n"
            f"1. Priority 1: Match the language of the user's question.\n"
            f"   - English question -> Respond in English.\n"
            f"   - Marathi question -> Respond in Marathi (मराठी).\n"
            f"   - Hindi question -> Respond in Hindi (हिन्दी).\n"
            f"   - Mixed language question -> Respond in the dominant language.\n"
            f"2. Priority 2: If question language is ambiguous, default to active session language: {fallback_lang_name}.\n"
            f"FOR THIS QUERY: Respond in {target_lang_name}.\n"
            f"CONVERSATIONAL STYLE DIRECTIVE:\n"
            f"- MARATHI: Use natural, conversational Maharashtra Marathi that ordinary users would use in daily conversation. Avoid overly formal, literary, Sanskritized, or machine-translated Marathi. Keep sentences simple, warm, and friendly.\n"
            f"- HINDI: Use natural, conversational Indian Hindi that ordinary users would use in daily conversation. Avoid overly formal, literary, Sanskritized, or machine-translated Hindi. Keep sentences simple, warm, and friendly."
        )

        # Model candidates list for resilience against per-model free tier quota limits
        model_candidates = [
            'gemini-3.5-flash',
            'gemini-flash-lite-latest',
            'gemini-3.5-flash-lite',
            'gemini-3.1-flash-lite',
            'gemini-flash-latest'
        ]

        last_exception = None
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )
                response = model.generate_content(user_message)
                if response and response.text:
                    return {
                        'response': response.text,
                        'success': True,
                        'error': None
                    }
            except Exception as e:
                last_exception = e
                print(f"Gemini API model '{model_name}' attempt error: {e}")
                continue

        if last_exception:
            raise last_exception

        return {
            'response': 'I could not generate a response. Please try rephrasing your question.',
            'success': False,
            'error': 'Empty response from Gemini'
        }

    except Exception as e:
        error_msg = str(e)
        # Never expose raw error details to the user
        print(f"Gemini API error: {error_msg}")

        # User-friendly error message
        if 'API_KEY_INVALID' in error_msg or 'API key' in error_msg:
            user_msg = 'The AI service is not properly configured. Please check your API key.'
        elif 'quota' in error_msg.lower() or 'rate' in error_msg.lower():
            user_msg = 'The AI service is temporarily busy. Please try again in a moment.'
        elif 'safety' in error_msg.lower():
            user_msg = 'I cannot respond to that query. Please try a different question.'
        else:
            user_msg = 'The AI service encountered an error. Please try again later.'

        return {
            'response': user_msg,
            'success': False,
            'error': 'Gemini API error'
        }
