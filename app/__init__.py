# app/__init__.py
# ============================================================
# FÁBRICA DE LA APLICACIÓN — Solo registra api.py como API JSON
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from supabase import create_client
import app.extensions as extensions

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')


def create_app(config_name='default'):

    app = Flask(__name__)

    # ── Configuración ─────────────────────────────────────────
    from config.settings import config
    app.config.from_object(config[config_name])

    # ── CORS ──────────────────────────────────────────────────
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
    CORS(app,
         origins=[
             'http://localhost:5173',
             'http://localhost:3000',
             'http://127.0.0.1:5173',
             frontend_url,
         ],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Accept', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    )

    # ── Supabase cliente anon (lectura) ───────────────────────
    supabase_url = app.config.get('SUPABASE_URL')
    supabase_key = app.config.get('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL o SUPABASE_KEY no están en el .env")

    extensions.supabase_client = create_client(supabase_url, supabase_key)
    print("✅ Supabase (anon) conectado.")

    # ── Supabase service role (escritura, bypasea RLS) ────────
    service_key = os.environ.get('SUPABASE_SERVICE_KEY')
    if service_key:
        extensions.supabase_service_client = create_client(supabase_url, service_key)
        print("✅ Supabase (service) conectado.")
    else:
        extensions.supabase_service_client = extensions.supabase_client
        print("⚠️  Sin SUPABASE_SERVICE_KEY — usando cliente anon.")

    # ── Registrar SOLO api.py ─────────────────────────────────
    # api.py contiene TODOS los endpoints del frontend React
    # bajo el prefijo /api/
    from app.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    print("✅ Blueprint API registrado en /api/")

    # ── Health check ──────────────────────────────────────────
    @app.route('/api/health')
    def health():
        return jsonify({'ok': True, 'status': 'SIPE running'}), 200

    # ── Ruta raíz ─────────────────────────────────────────────
    @app.route('/')
    def home():
        return jsonify({
            'ok':      True,
            'app':     'SIPE API',
            'version': '2.0',
            'docs':    '/api/test-conexion'
        }), 200

    print("✅ App lista.")
    return app