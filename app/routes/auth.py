# app/routes/auth.py
# ============================================================
# RUTAS DE AUTENTICACIÓN — API JSON pura
# Endpoints: /api/auth/login, /api/auth/registro,
#            /api/auth/logout, /api/auth/me
# ============================================================

from flask import Blueprint, request, jsonify, session
from app.extensions import get_supabase
from app.auth_utils import hash_password, verify_password

auth_bp = Blueprint('auth_api', __name__)


# ── LOGIN ─────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    # Preflight CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json(silent=True) or {}
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Correo y contraseña requeridos'}), 400

    try:
        sb = get_supabase()

        resultado = (
            sb.table('usuarios')
            .select('*')
            .eq('email', email)
            .eq('activo', True)
            .execute()
        )

        if not resultado.data:
            return jsonify({'error': 'Credenciales incorrectas'}), 401

        usuario = resultado.data[0]

        if not verify_password(password, usuario.get('password_hash', '')):
            return jsonify({'error': 'Credenciales incorrectas'}), 401

        # ── Guardar en sesión ─────────────────────────────────
        session.permanent = True
        session['usuario_id'] = usuario['id']
        session['nombre']     = usuario['nombre']
        session['apellido']   = usuario['apellido']
        session['email']      = usuario['email']
        session['rol']        = usuario['rol']
        session['programa']   = usuario.get('programa', '')

        return jsonify({
            'ok': True,
            'usuario': {
                'id':       usuario['id'],
                'nombre':   usuario['nombre'],
                'apellido': usuario['apellido'],
                'email':    usuario['email'],
                'rol':      usuario['rol'],
                'programa': usuario.get('programa'),
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── REGISTRO ──────────────────────────────────────────────────
@auth_bp.route('/registro', methods=['POST', 'OPTIONS'])
def registro():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data     = request.get_json(silent=True) or {}
    nombre   = (data.get('nombre')   or '').strip()
    apellido = (data.get('apellido') or '').strip()
    email    = (data.get('email')    or '').strip().lower()
    password = data.get('password')  or ''
    codigo   = data.get('codigo')    or None
    programa = data.get('programa')  or None

    if not all([nombre, apellido, email, password]):
        return jsonify({'error': 'Nombre, apellido, correo y contraseña son requeridos'}), 400

    if len(password) < 6:
        return jsonify({'error': 'La contraseña debe tener mínimo 6 caracteres'}), 400

    if '@' not in email:
        return jsonify({'error': 'Correo electrónico inválido'}), 400

    try:
        sb = get_supabase()

        # Verificar si ya existe
        existe = sb.table('usuarios').select('id').eq('email', email).execute()
        if existe.data:
            return jsonify({'error': 'Ya existe una cuenta con ese correo'}), 409

        nuevo_usuario = {
            'nombre':        nombre,
            'apellido':      apellido,
            'email':         email,
            'codigo':        codigo,
            'programa':      programa,
            'password_hash': hash_password(password),
            'rol':           'estudiante',
            'activo':        True,
        }

        resultado = sb.table('usuarios').insert(nuevo_usuario).execute()

        if not resultado.data:
            return jsonify({'error': 'Error al crear la cuenta'}), 500

        return jsonify({
            'ok':      True,
            'mensaje': 'Cuenta creada exitosamente. Ya puedes iniciar sesión.'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── LOGOUT ────────────────────────────────────────────────────
@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
def logout():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    session.clear()
    return jsonify({'ok': True, 'mensaje': 'Sesión cerrada correctamente'}), 200


# ── ME — Usuario actual ───────────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
def me():
    """Retorna los datos del usuario autenticado en la sesión."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado', 'autenticado': False}), 401

    return jsonify({
        'ok':           True,
        'autenticado':  True,
        'usuario': {
            'id':       session.get('usuario_id'),
            'nombre':   session.get('nombre'),
            'apellido': session.get('apellido'),
            'email':    session.get('email'),
            'rol':      session.get('rol'),
            'programa': session.get('programa'),
        }
    }), 200