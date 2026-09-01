import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database', 'wari_mitra.db')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
