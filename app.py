"""
AstraOps AI — AI-Powered Pilgrimage Assistance Platform
Flask application entry point.


This module creates the Flask app, registers all Blueprints,
and initializes the database on first run.
"""

import os
from flask import Flask
from config import Config
from models.db import init_db


def create_app():
    """
    Application factory: creates and configures the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure the database directory exists
    db_dir = os.path.dirname(app.config['DATABASE'])
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Initialize the database (creates tables if they don't exist)
    init_db(app.config['DATABASE'])

    # ---- Register Blueprints ----
    # Auth Blueprint — login, register, logout
    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)

    # Home Blueprint — landing page dashboard
    from routes.home_routes import home_bp
    app.register_blueprint(home_bp)

    # Additional Blueprints will be registered here as they are built.

    # Map Blueprint — interactive route map
    from routes.map_routes import map_bp
    app.register_blueprint(map_bp)

    # Facility Blueprint — nearby facilities
    from routes.facility_routes import facility_bp
    app.register_blueprint(facility_bp)

    # Chat Blueprint — AI assistant
    from routes.chat_routes import chat_bp
    app.register_blueprint(chat_bp)

    # Weather Blueprint — weather conditions
    from routes.weather_routes import weather_bp
    app.register_blueprint(weather_bp)

    # SOS Blueprint — emergency SOS
    from routes.sos_routes import sos_bp
    app.register_blueprint(sos_bp)

    # Profile Blueprint — user profile
    from routes.profile_routes import profile_bp
    app.register_blueprint(profile_bp)

    # Admin Blueprint — command & control center
    from routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    # Volunteer Blueprint — location tracking & safety (Phase 34)
    from routes.volunteer_routes import volunteer_bp
    app.register_blueprint(volunteer_bp)



    # ---- Multilingual Support ----
    from services.translation_service import (
        load_translations, get_translation, get_current_language,
        set_current_language, get_all_translations_json, SUPPORTED_LANGUAGES
    )
    from flask import request, redirect, url_for

    load_translations(app.root_path)

    @app.before_request
    def check_lang_param():
        # Check query param ?lang=xx
        lang = request.args.get('lang')
        if lang and lang in SUPPORTED_LANGUAGES:
            set_current_language(lang)

    from services.location_service import get_location_name

    @app.context_processor
    def inject_translation_helpers():
        current_lang = get_current_language()
        return {
            't': get_translation,
            'get_location_name': get_location_name,
            'current_lang': current_lang,
            'supported_languages': SUPPORTED_LANGUAGES,
            'translations_json': get_all_translations_json(current_lang)
        }

    @app.route('/set_language/<lang_code>')
    def set_language(lang_code):
        set_current_language(lang_code)
        referrer = request.referrer
        if referrer and referrer.startswith(request.host_url):
            return redirect(referrer)
        return redirect(url_for('home.home'))

    return app


# Create the app instance
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
