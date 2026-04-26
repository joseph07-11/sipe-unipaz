# app/__init__.py
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from supabase import create_client
import app.extensions as extensions

# Carga el .env directamente aquí también, con ruta absoluta
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

def create_app(config_name='default'):

    app = Flask(__name__)

    # Leer directamente desde os.environ (no desde app.config)
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')

    print(f"  → URL dentro de create_app: {supabase_url}")
    print(f"  → KEY dentro de create_app: {str(supabase_key)[:20] if supabase_key else 'NONE'}")

    # Configuración de Flask
    app.secret_key = os.environ.get('SECRET_KEY', 'clave-temporal')
    app.config['DEBUG'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    # Habilitar CORS para el frontend React
    CORS(app, supports_credentials=True, origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ])

    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL o SUPABASE_KEY no encontradas")
    # Cliente normal (anon) — para lectura en el frontend
    extensions.supabase_client = create_client(supabase_url, supabase_key)

    # Cliente de servicio — para escritura del scraper
    supabase_service_key = os.environ.get('SUPABASE_SERVICE_KEY')
    if supabase_service_key:
        extensions.supabase_service_client = create_client(supabase_url, supabase_service_key)
    else:
        extensions.supabase_service_client = extensions.supabase_client

    print("✅ Conexión con Supabase establecida correctamente.")

    # Registrar Blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.vacantes import vacantes_bp
    app.register_blueprint(vacantes_bp, url_prefix='/vacantes')

    from app.routes.coordinador import coordinador_bp
    app.register_blueprint(coordinador_bp, url_prefix='/coordinador')

    # API REST para el frontend React
    from app.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Agregar esto ANTES del return app en create_app()

    # ── Ruta raíz ────────────────────────────────────────────────
    from flask import redirect, url_for, session
    
    @app.route('/')
    def home():
        """Redirige al login o a vacantes según si hay sesión."""
        if 'usuario_id' in session:
            return redirect(url_for('vacantes.index'))
        return redirect(url_for('auth.login'))

    return app