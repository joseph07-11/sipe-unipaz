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
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

    # ── Configuración de sesiones para producción ─────────────
    SESSION_COOKIE_SECURE   = True   # Solo HTTPS
    SESSION_COOKIE_HTTPONLY = True   # No accesible desde JS
    SESSION_COOKIE_SAMESITE = 'Lax' # Protección CSRF básica
    PERMANENT_SESSION_LIFETIME = 86400  # 24 horas en segundos

    SCRAPER_DELAY_SECONDS = 3
    SCRAPER_TIMEOUT = 15

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False  # En local no hay HTTPS

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True   # En Render sí hay HTTPS

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}