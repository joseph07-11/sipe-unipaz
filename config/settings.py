# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Encuentra la raíz del proyecto (donde está run.py)
# y carga el .env desde ahí con ruta absoluta
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-temporal'
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SCRAPER_DELAY_SECONDS = 3
    SCRAPER_TIMEOUT = 15

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}