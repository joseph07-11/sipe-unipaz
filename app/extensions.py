# app/extensions.py
# ============================================================
# EXTENSIONES Y CLIENTES GLOBALES
# Separado de __init__.py para evitar importaciones circulares
# ============================================================

from supabase import Client

# El cliente se guarda aquí y se inicializa desde create_app()
supabase_client: Client = None

def get_supabase() -> Client:
    """Retorna el cliente Supabase inicializado."""
    return supabase_client