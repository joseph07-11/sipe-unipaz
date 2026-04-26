# app/routes/coordinador.py
# ============================================================
# RUTAS DEL COORDINADOR — API JSON pura
# Endpoints bajo prefijo /api/coordinador/
# Todos protegidos por rol 'coordinador'
# ============================================================

from flask import Blueprint, request, jsonify, session
from app.extensions import get_supabase, get_supabase_service
from functools import wraps

coordinador_bp = Blueprint('coordinador_api', __name__)


# ── Decorador para rutas de coordinador ──────────────────────
def coordinador_required_json(f):
    """
    Protege rutas exclusivas del coordinador.
    Retorna JSON 401 o 403 según el caso.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({'error': 'No autenticado', 'autenticado': False}), 401
        if session.get('rol') != 'coordinador':
            return jsonify({'error': 'Acceso denegado. Se requiere rol coordinador'}), 403
        return f(*args, **kwargs)
    return decorated


# ── DASHBOARD ────────────────────────────────────────────────
@coordinador_bp.route('/dashboard', methods=['GET'])
@coordinador_required_json
def dashboard():
    """
    GET /api/coordinador/dashboard
    Retorna estadísticas generales de SIPE.
    """
    try:
        sb = get_supabase()

        # Conteos principales
        r_vacantes     = sb.table('vacantes').select('id', count='exact').eq('activa', True).execute()
        r_estudiantes  = sb.table('usuarios').select('id', count='exact').eq('rol', 'estudiante').execute()
        r_postulaciones = sb.table('postulaciones').select('id', count='exact').execute()

        # Vacantes por fuente
        r_fuentes = sb.table('vacantes').select('fuente').eq('activa', True).execute()
        fuentes   = {}
        for v in (r_fuentes.data or []):
            f = v.get('fuente') or 'desconocida'
            fuentes[f] = fuentes.get(f, 0) + 1

        # Últimas 5 postulaciones
        r_post_rec = (
            sb.table('postulaciones')
            .select('id, estado, creado_en, vacantes(titulo, empresa), usuarios(nombre, apellido, email)')
            .order('creado_en', desc=True)
            .limit(5)
            .execute()
        )

        # Últimas 5 vacantes
        r_vac_rec = (
            sb.table('vacantes')
            .select('id, titulo, empresa, fuente, modalidad, activa, creado_en')
            .order('creado_en', desc=True)
            .limit(5)
            .execute()
        )

        return jsonify({
            'ok': True,
            'stats': {
                'total_vacantes':      r_vacantes.count     or 0,
                'total_estudiantes':   r_estudiantes.count  or 0,
                'total_postulaciones': r_postulaciones.count or 0,
                'fuentes':             fuentes,
            },
            'postulaciones_recientes': r_post_rec.data or [],
            'vacantes_recientes':      r_vac_rec.data  or [],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── CHART DATA ────────────────────────────────────────────────
@coordinador_bp.route('/chart-data', methods=['GET'])
@coordinador_required_json
def chart_data():
    """
    GET /api/coordinador/chart-data
    Serie temporal de vacantes por mes (últimos 6 meses).
    """
    try:
        sb = get_supabase()
        from collections import defaultdict

        r = sb.table('vacantes').select('creado_en, fuente').eq('activa', True).execute()

        por_mes = defaultdict(int)
        for v in (r.data or []):
            fecha = (v.get('creado_en') or '')[:7]  # YYYY-MM
            if fecha:
                por_mes[fecha] += 1

        # Ordenar y tomar últimos 6 meses
        series = [
            {'mes': mes, 'total': total}
            for mes, total in sorted(por_mes.items())
        ][-6:]

        return jsonify({
            'ok':    True,
            'series': series,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── TODAS LAS POSTULACIONES ───────────────────────────────────
@coordinador_bp.route('/postulaciones', methods=['GET'])
@coordinador_required_json
def postulaciones():
    """
    GET /api/coordinador/postulaciones
    Params opcionales: ?estado=postulado|en_proceso|aceptado|rechazado
    """
    try:
        sb     = get_supabase()
        estado = request.args.get('estado', '')

        query = (
            sb.table('postulaciones')
            .select('*, usuarios(nombre, apellido, email, programa), vacantes(titulo, empresa)')
            .order('creado_en', desc=True)
        )

        if estado:
            query = query.eq('estado', estado)

        r = query.execute()

        return jsonify({
            'ok':            True,
            'postulaciones': r.data or [],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── CAMBIAR ESTADO DE POSTULACIÓN ─────────────────────────────
@coordinador_bp.route('/postulaciones/<postulacion_id>/estado', methods=['POST', 'OPTIONS'])
@coordinador_required_json
def cambiar_estado(postulacion_id):
    """POST /api/coordinador/postulaciones/<id>/estado"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data         = request.get_json(silent=True) or {}
    nuevo_estado = data.get('estado')
    nota         = data.get('nota', '')

    estados_validos = ['postulado', 'en_proceso', 'aceptado', 'rechazado']
    if nuevo_estado not in estados_validos:
        return jsonify({'error': f'Estado inválido. Opciones: {estados_validos}'}), 400

    try:
        sb = get_supabase()

        update_data = {'estado': nuevo_estado}
        if nota:
            update_data['nota'] = nota

        sb.table('postulaciones').update(update_data).eq('id', postulacion_id).execute()

        return jsonify({
            'ok':      True,
            'mensaje': f'Estado actualizado a "{nuevo_estado}"',
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── LISTAR VACANTES (vista coordinador) ───────────────────────
@coordinador_bp.route('/vacantes', methods=['GET'])
@coordinador_required_json
def listar_vacantes():
    """
    GET /api/coordinador/vacantes
    Params opcionales: ?mostrar=activas|inactivas|todas
    """
    try:
        sb      = get_supabase()
        mostrar = request.args.get('mostrar', 'activas')

        query = sb.table('vacantes').select('*').order('creado_en', desc=True)

        if mostrar == 'activas':
            query = query.eq('activa', True)
        elif mostrar == 'inactivas':
            query = query.eq('activa', False)
        # 'todas' no aplica filtro

        r = query.execute()

        return jsonify({
            'ok':      True,
            'vacantes': r.data or [],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── CREAR VACANTE MANUAL ──────────────────────────────────────
@coordinador_bp.route('/vacantes', methods=['POST', 'OPTIONS'])
@coordinador_required_json
def crear_vacante():
    """POST /api/coordinador/vacantes"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json(silent=True) or {}

    titulo  = (data.get('titulo')  or '').strip()
    empresa = (data.get('empresa') or '').strip()

    if not titulo or not empresa:
        return jsonify({'error': 'Título y empresa son obligatorios'}), 400

    try:
        # Usar service key para bypasear RLS
        sb = get_supabase_service() or get_supabase()

        nueva = {
            'titulo':          titulo,
            'empresa':         empresa,
            'salario':         data.get('salario')         or None,
            'ubicacion':       data.get('ubicacion')       or None,
            'modalidad':       data.get('modalidad', 'presencial'),
            'descripcion':     data.get('descripcion')     or None,
            'requisitos':      data.get('requisitos')      or None,
            'link_aplicacion': data.get('link_aplicacion') or None,
            'fecha_limite':    data.get('fecha_limite')    or None,
            'fuente':          'manual',
            'activa':          True,
        }

        resultado = sb.table('vacantes').insert(nueva).execute()

        return jsonify({
            'ok':      True,
            'vacante': resultado.data[0] if resultado.data else None,
            'mensaje': f'Vacante "{titulo}" creada exitosamente',
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── TOGGLE ACTIVA/INACTIVA ────────────────────────────────────
@coordinador_bp.route('/vacantes/<vacante_id>/toggle', methods=['POST', 'OPTIONS'])
@coordinador_required_json
def toggle_vacante(vacante_id):
    """POST /api/coordinador/vacantes/<id>/toggle"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        sb = get_supabase()

        r = sb.table('vacantes').select('activa, titulo').eq('id', vacante_id).single().execute()

        if not r.data:
            return jsonify({'error': 'Vacante no encontrada'}), 404

        nuevo_estado = not r.data['activa']
        sb.table('vacantes').update({'activa': nuevo_estado}).eq('id', vacante_id).execute()

        accion = 'activada' if nuevo_estado else 'desactivada'

        return jsonify({
            'ok':      True,
            'activa':  nuevo_estado,
            'mensaje': f'Vacante "{r.data["titulo"]}" {accion}',
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── EJECUTAR SCRAPER ──────────────────────────────────────────
@coordinador_bp.route('/ejecutar-scraper', methods=['POST', 'OPTIONS'])
@coordinador_required_json
def ejecutar_scraper():
    """
    POST /api/coordinador/ejecutar-scraper
    Dispara el scraper de Computrabajo manualmente.
    ⚠️ Puede tardar 2-5 minutos.
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        from app.scrapers.computrabajo import ComputrabajoScraper

        sb_service = get_supabase_service()
        if sb_service is None:
            return jsonify({'error': 'SUPABASE_SERVICE_KEY no configurada'}), 500

        terminos = [
            'pasantia ingenieria',
            'practicante sistemas',
            'aprendiz sena',
            'practicante administrativo',
            'trainee colombia',
            'practicante ambiental',
            'auxiliar juridico sin experiencia',
            'desarrollador junior sin experiencia',
        ]

        scraper = ComputrabajoScraper(
            supabase_client=sb_service,
            delay_min=4,
            delay_max=8
        )

        resumen = scraper.ejecutar(
            terminos_busqueda=terminos,
            max_paginas=2
        )

        return jsonify({
            'ok':      True,
            'resumen': {
                'encontradas':  resumen['vacantes_encontradas'],
                'guardadas':    resumen['vacantes_guardadas'],
                'rechazadas':   resumen['vacantes_rechazadas'],
                'errores':      resumen['errores'],
                'duracion_seg': resumen['duracion_segundos'],
            },
            'mensaje': (
                f"Scraper completado: {resumen['vacantes_guardadas']} vacantes nuevas "
                f"de {resumen['vacantes_encontradas']} encontradas."
            ),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500