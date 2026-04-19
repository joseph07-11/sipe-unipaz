# run.py - VERSIÓN DIAGNÓSTICO
import os
from pathlib import Path
from dotenv import load_dotenv

# Carga explícita con ruta absoluta
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / '.env'

print(f"📁 Buscando .env en: {env_path}")
print(f"📁 ¿El archivo existe?: {env_path.exists()}")

load_dotenv(dotenv_path=env_path)

print(f"🔑 SUPABASE_URL: {os.environ.get('SUPABASE_URL')}")
print(f"🔑 SUPABASE_KEY: {str(os.environ.get('SUPABASE_KEY'))[:20] if os.environ.get('SUPABASE_KEY') else 'NO ENCONTRADA'}")

from app import create_app
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)