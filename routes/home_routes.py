"""
Home Routes — Flask Blueprint for the Home/Landing page.

Serves the main dashboard with hero section, feature cards,
today's overview, and quick navigation to all modules.

Routes:
    GET /  — Home/Landing page
"""

from flask import Blueprint, render_template, session, current_app
from models.schedule_model import get_full_schedule


# Create the Blueprint
home_bp = Blueprint('home', __name__)


@home_bp.route('/')
def home():
    """
    Home page — the main landing dashboard.

    Displays:
        - Hero section with branding and CTA
        - Feature cards linking to all modules
        - Today's overview (placeholder data)
        - Recent announcements (placeholder data)

    No database queries or API calls — uses placeholder data only.
    """
    # Placeholder data for today's overview
    todays_overview = {
        'halt_village': 'Wakhari',
        'day_number': 5,
        'distance_remaining': '18.5 km',
        'weather_temp': '28',
        'weather_condition': 'Partly Cloudy',
        'next_halt': 'Taradgaon',
    }

    # Placeholder announcements
    announcements = [
        {
            'type': 'info',
            'icon': 'bi-info-circle-fill',
            'message': 'Medical camp available near Wakhari halt. Open 24 hours.'
        },
        {
            'type': 'warning',
            'icon': 'bi-exclamation-triangle-fill',
            'message': 'Heavy rain expected tomorrow. Please carry rain gear and stay on marked paths.'
        },
        {
            'type': 'success',
            'icon': 'bi-check-circle-fill',
            'message': 'Anna Chhatra (free food service) is active at today\'s halt location.'
        },
    ]

    return render_template('home.html',
                           overview=todays_overview,
                           announcements=announcements)


@home_bp.route('/schedule')
def schedule_page():
    """
    Daily Schedule page — displays the Wari itinerary.
    Uses existing schedule data from the database.
    """
    db_path = current_app.config['DATABASE']
    schedule = get_full_schedule(db_path)

    schedule_list = []
    for entry in schedule:
        schedule_list.append({
            'day_number': entry['day_number'],
            'date': entry['date'],
            'halt_village': entry['halt_village'],
            'distance_km': entry['distance_km'],
            'start_time': entry['start_time'],
            'end_time': entry['end_time'],
            'notes': entry['notes']
        })

    return render_template('schedule.html', schedule=schedule_list)


@home_bp.route('/about')
def about_page():
    """About page — project information."""
    return render_template('about.html')
