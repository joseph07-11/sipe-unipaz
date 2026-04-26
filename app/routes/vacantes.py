# app/routes/vacantes.py
# ============================================================
# RUTAS DE VACANTES — API JSON pura
# Endpoints bajo prefijo /api/vacantes/
# ============================================================

from flask import Blueprint, request, jsonify, session
from app.extensions import get_supabase
from functools import wraps

vacantes_bp = Blueprint('vacantes_api', __name__)

# ── Keywords por carrera Unipaz ───────────────────────────────
# Importar desde computrabajo si existe, sino definir aquí
try:
    from app.scrapers.computrabajo import CARRERAS_UNIPAZ as CARRERAS_KEYWORDS
except ImportError:
    CARRERAS_KEYWORDS = {}


# ── Decorador de autenticación JSON ──────────────────────────
def login_required_json(f):
    """Retorna 401 JSON si el usuario no está autenticado."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({'error': 'No autenticado', 'autenticado': False}), 401
        return f(*args, **kwargs)
    return decorated


# ── LISTAR VACANTES ───────────────────────────────────────────
@vacantes_bp.route('/', methods=['GET'])
@login_required_json
def index():
    """
    GET /api/vacantes/
    Params opcionales: ?q=texto&modalidad=...&fuente=...&carrera=...
    """
    try:
        sb = get_supabase()

        modalidad = request.args.get('modalidad', '')
        fuente    = request.args.get('fuente', '')
        carrera   = request.args.get('carrera', '')
        busqueda  = (request.args.get('q') or '').strip()

        # Construir query base
        query = sb.table('vacantes').select('*').eq('activa', True)

        if modalidad:
            query = query.eq('modalidad', modalidad)
        if fuente:
            query = query.eq('fuente', fuente)

        query    = query.order('creado_en', desc=True)
        response = query.execute()
        vacantes = response.data or []

        # ── Filtro por texto (en Python) ──────────────────────
        if busqueda:
            bl = busqueda.lower()
            vacantes = [
                v for v in vacantes
                if bl in (v.get('titulo')      or '').lower()
                or bl in (v.get('empresa')     or '').lower()
                or bl in (v.get('ubicacion')   or '').lower()
                or bl in (v.get('descripcion') or '').lower()
                or bl in (v.get('requisitos')  or '').lower()
            ]

        # ── Filtro por carrera Unipaz ─────────────────────────
        if carrera and carrera in CARRERAS_KEYWORDS:
            kws = CARRERAS_KEYWORDS[carrera]
            vacantes = [
                v for v in vacantes
                if any(
                    kw in (
                        (v.get('titulo')      or '') + ' ' +
                        (v.get('descripcion') or '') + ' ' +
                        (v.get('requisitos')  or '')
                    ).lower()
                    for kw in kws
                )
            ]

        return jsonify({
            'ok':       True,
            'total':    len(vacantes),
            'vacantes': vacantes,
            'carreras': list(CARRERAS_KEYWORDS.keys()),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── DETALLE DE UNA VACANTE ────────────────────────────────────
@vacantes_bp.route('/<vacante_id>', methods=['GET'])
@login_required_json
def detalle(vacante_id):
    """GET /api/vacantes/<vacante_id>"""
    try:
        sb = get_supabase()

        respuesta = (
            sb.table('vacantes')
            .select('*')
            .eq('id', vacante_id)
            .single()
            .execute()
        )

        if not respuesta.data:
            return jsonify({'error': 'Vacante no encontrada'}), 404

        # Verificar si ya se postuló
        ya_postulado = False
        if session.get('usuario_id'):
            post = (
                sb.table('postulaciones')
                .select('id')
                .eq('usuario_id', session['usuario_id'])
                .eq('vacante_id', vacante_id)
                .execute()
            )
            ya_postulado = len(post.data) > 0

        return jsonify({
            'ok':           True,
            'vacante':      respuesta.data,
            'ya_postulado': ya_postulado,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── POSTULARSE ────────────────────────────────────────────────
@vacantes_bp.route('/<vacante_id>/postular', methods=['POST', 'OPTIONS'])
@login_required_json
def postular(vacante_id):
    """POST /api/vacantes/<vacante_id>/postular"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        sb = get_supabase()

        sb.table('postulaciones').insert({
            'usuario_id': session['usuario_id'],
            'vacante_id': vacante_id,
            'estado':     'postulado',
        }).execute()

        return jsonify({
            'ok':      True,
            'mensaje': '¡Te postulaste exitosamente! El coordinador revisará tu solicitud.',
        }), 201

    except Exception as e:
        if 'unique' in str(e).lower():
            return jsonify({'error': 'Ya te postulaste a esta vacante anteriormente'}), 409
        return jsonify({'error': str(e)}), 500


# ── MIS POSTULACIONES ─────────────────────────────────────────
@vacantes_bp.route('/mis-postulaciones', methods=['GET'])
@login_required_json
def mis_postulaciones():
    """GET /api/vacantes/mis-postulaciones"""
    try:
        sb = get_supabase()

        respuesta = (
            sb.table('postulaciones')
            .select('*, vacantes(*)')
            .eq('usuario_id', session['usuario_id'])
            .order('creado_en', desc=True)
            .execute()
        )

        return jsonify({
            'ok':            True,
            'postulaciones': respuesta.data or [],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── TEST CONEXIÓN ─────────────────────────────────────────────
@vacantes_bp.route('/test-conexion', methods=['GET'])
def test_conexion():
    """GET /api/vacantes/test-conexion — Endpoint público de diagnóstico"""
    try:
        sb = get_supabase()
        r  = sb.table('vacantes').select('id').limit(1).execute()
        return jsonify({
            'ok':      True,
            'mensaje': 'Conexión con Supabase funcionando correctamente',
        }), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500