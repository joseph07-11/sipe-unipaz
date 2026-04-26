# debug_guardado.py — Identificar error exacto al guardar
import os, sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / '.env')
sys.path.insert(0, str(BASE_DIR))

from supabase import create_client

sb = create_client(
    os.environ.get('SUPABASE_URL'),
    os.environ.get('SUPABASE_SERVICE_KEY')
)

# Intentar insertar una vacante de prueba mínima
vacante_prueba = {
    'titulo':          'TEST Practicante Sistemas',
    'empresa':         'Empresa Test',
    'salario':         None,
    'ubicacion':       None,
    'modalidad':       'presencial',
    'descripcion':     None,
    'requisitos':      None,
    'link_aplicacion': None,
    'fuente':          'computrabajo',
    'activa':          True,
}

print("🧪 Intentando insertar vacante de prueba...")
try:
    resultado = sb.table('vacantes').insert(vacante_prueba).execute()
    print(f"✅ ÉXITO: {resultado.data}")
except Exception as e:
    print(f"❌ ERROR EXACTO: {str(e)}")
    print(f"❌ TIPO: {type(e).__name__}")