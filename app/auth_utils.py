# app/auth_utils.py
# ============================================================
# UTILIDADES DE AUTENTICACIÓN
# Funciones reutilizables para manejo de contraseñas y sesiones
# ============================================================

from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from functools import wraps
from flask import redirect, url_for, flash

def hash_password(password: str) -> str:
    """
    Encripta una contraseña usando pbkdf2:sha256.
    Ejemplo: 'mi123' → '$pbkdf2-sha256$...' (irreversible)
    """
    return generate_password_hash(password, method='pbkdf2:sha256')

def verify_password(password: str, password_hash: str) -> bool:
    """
    Compara una contraseña en texto plano con su hash guardado.
    Retorna True si coinciden, False si no.
    """
    return check_password_hash(password_hash, password)

def login_required(f):
    """
    Decorador que protege rutas que requieren login.
    Uso:
        @vacantes_bp.route('/mis-postulaciones')
        @login_required
        def mis_postulaciones():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def coordinador_required(f):
    """
    Decorador que protege rutas exclusivas para coordinadores.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('rol') != 'coordinador':
            flash('No tienes permisos para acceder a esta sección.', 'danger')
            return redirect(url_for('vacantes.index'))
        return f(*args, **kwargs)
    return decorated_function

def get_usuario_actual():
    """
    Retorna los datos del usuario logueado desde la sesión.
    Retorna None si no hay sesión activa.
    """
    if 'usuario_id' in session:
        return {
            'id': session.get('usuario_id'),
            'nombre': session.get('nombre'),
            'email': session.get('email'),
            'rol': session.get('rol'),
            'programa': session.get('programa')
        }
    return None