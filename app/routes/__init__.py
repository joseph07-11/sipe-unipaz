# app/__init__.py

from flask import Flask
from supabase import create_client
from config.settings import config
import app.extensions as extensions

def create_app(config_name='default'):

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ── Inicializar Supabase ─────────────────────────────────
    supabase_url = app.config.get('SUPABASE_URL')
    supabase_key = app.config.get('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        raise ValueError(
            "❌ ERROR: SUPABASE_URL o SUPABASE_KEY no están en el .env"
        )

    # Guardamos el cliente en extensions.py (no aquí)
    extensions.supabase_client = create_client(supabase_url, supabase_key)
    print("✅ Conexión con Supabase establecida correctamente.")

    # ── Registrar Blueprints ─────────────────────────────────
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.vacantes import vacantes_bp
    app.register_blueprint(vacantes_bp, url_prefix='/vacantes')

    return app# app/__init__.py

from flask import Flask
from supabase import create_client
from config.settings import config
import app.extensions as extensions

def create_app(config_name='default'):

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ── Inicializar Supabase ─────────────────────────────────
    supabase_url = app.config.get('SUPABASE_URL')
    supabase_key = app.config.get('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        raise ValueError(
            "❌ ERROR: SUPABASE_URL o SUPABASE_KEY no están en el .env"
        )

    # Guardamos el cliente en extensions.py (no aquí)
    extensions.supabase_client = create_client(supabase_url, supabase_key)
    print("✅ Conexión con Supabase establecida correctamente.")

    # ── Registrar Blueprints ─────────────────────────────────
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.vacantes import vacantes_bp
    app.register_blueprint(vacantes_bp, url_prefix='/vacantes')

    return app