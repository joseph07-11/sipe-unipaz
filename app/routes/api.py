# app/routes/api.py
# ============================================================
# API REST — Endpoints JSON para el Frontend React
# ============================================================

from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Blueprint, jsonify, request, session
from app.extensions import get_supabase, get_supabase_service
from app.auth_utils import hash_password, verify_password
from app.config import CARRERAS_KEYWORDS
from app.scrapers.indeed import IndeedScraper
from app.scrapers.elempleo import ElempleoScraper

api_bp = Blueprint('api', __name__)


# ════════════════════════════════════════════════════════════════
# AUTENTICACIÓN
# ════════════════════════════════════════════════════════════════

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """Login del usuario — devuelve datos del usuario en JSON."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON con email y password'}), 400

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Email y contraseña son requeridos'}), 400

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
            return jsonify({'error': 'Correo o contraseña incorrectos'}), 401

        usuario = resultado.data[0]

        if not verify_password(password, usuario.get('password_hash', '')):
            return jsonify({'error': 'Correo o contraseña incorrectos'}), 401

        # Guardar en sesión
        session.permanent = True
        session['usuario_id'] = usuario['id']
        session['nombre']     = usuario['nombre']
        session['apellido']   = usuario.get('apellido', '')
        session['email']      = usuario['email']
        session['rol']        = usuario['rol']
        session['programa']   = usuario.get('programa', '')

        return jsonify({
            'ok': True,
            'usuario': {
                'id':       usuario['id'],
                'nombre':   usuario['nombre'],
                'apellido': usuario.get('apellido', ''),
                'email':    usuario['email'],
                'rol':      usuario['rol'],
                'programa': usuario.get('programa', ''),
            }
        })

    except Exception as e:
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500


@api_bp.route('/auth/registro', methods=['POST'])
def api_registro():
    """Registro de nuevo usuario."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    nombre    = (data.get('nombre') or '').strip()
    apellido  = (data.get('apellido') or '').strip()
    email     = (data.get('email') or '').strip().lower()
    codigo    = (data.get('codigo') or '').strip()
    programa  = (data.get('programa') or '').strip()
    password  = data.get('password') or ''
    password2 = data.get('password2') or ''

    # Validaciones
    errores = []
    if not all([nombre, apellido, email, password]):
        errores.append('Todos los campos obligatorios deben estar completos.')
    if password != password2:
        errores.append('Las contraseñas no coinciden.')
    if len(password) < 6:
        errores.append('La contraseña debe tener al menos 6 caracteres.')
    if '@' not in email:
        errores.append('El correo electrónico no es válido.')

    if errores:
        return jsonify({'error': errores[0], 'errores': errores}), 400

    try:
        sb = get_supabase()

        # Verificar si email ya existe
        existe = sb.table('usuarios').select('id').eq('email', email).execute()
        if existe.data:
            return jsonify({'error': 'Ya existe una cuenta con ese correo electrónico.'}), 409

        nuevo_usuario = {
            'nombre':        nombre,
            'apellido':      apellido,
            'email':         email,
            'codigo':        codigo or None,
            'programa':      programa or None,
            'password_hash': hash_password(password),
            'rol':           'estudiante'
        }

        resultado = sb.table('usuarios').insert(nuevo_usuario).execute()

        if resultado.data:
            return jsonify({
                'ok': True,
                'mensaje': 'Cuenta creada exitosamente. Ya puedes iniciar sesión.'
            }), 201
        else:
            return jsonify({'error': 'Error al crear la cuenta.'}), 500

    except Exception as e:
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500


@api_bp.route('/auth/logout', methods=['POST'])
def api_logout():
    """Cierra la sesión del usuario."""
    session.clear()
    return jsonify({'ok': True, 'mensaje': 'Sesión cerrada correctamente.'})


@api_bp.route('/auth/me', methods=['GET'])
def api_me():
    """Retorna datos del usuario logueado, o 401 si no hay sesión."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    return jsonify({
        'ok': True,
        'usuario': {
            'id':       session.get('usuario_id'),
            'nombre':   session.get('nombre'),
            'apellido': session.get('apellido', ''),
            'email':    session.get('email'),
            'rol':      session.get('rol'),
            'programa': session.get('programa', ''),
        }
    })


# ════════════════════════════════════════════════════════════════
# VACANTES
# ════════════════════════════════════════════════════════════════

@api_bp.route('/vacantes', methods=['GET'])
def api_vacantes():
    """Lista vacantes con filtros opcionales: modalidad, fuente, carrera, q (búsqueda)."""
    # Verificar autenticación
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        sb = get_supabase()

        modalidad = request.args.get('modalidad', '')
        fuente    = request.args.get('fuente', '')
        carrera   = request.args.get('carrera', '')
        busqueda  = (request.args.get('q') or '').strip()

        query = sb.table('vacantes').select('*').eq('activa', True)

        if modalidad:
            query = query.eq('modalidad', modalidad)
        if fuente:
            query = query.eq('fuente', fuente)

        query = query.order('creado_en', desc=True)
        respuesta = query.execute()
        vacantes  = respuesta.data or []

        # Filtro de búsqueda por texto
        if busqueda:
            busqueda_lower = busqueda.lower()
            vacantes = [
                v for v in vacantes
                if busqueda_lower in (v.get('titulo') or '').lower()
                or busqueda_lower in (v.get('empresa') or '').lower()
                or busqueda_lower in (v.get('ubicacion') or '').lower()
                or busqueda_lower in (v.get('descripcion') or '').lower()
                or busqueda_lower in (v.get('requisitos') or '').lower()
            ]

        # Filtro por carrera Unipaz
        if carrera and carrera in CARRERAS_KEYWORDS:
            keywords = CARRERAS_KEYWORDS[carrera]
            vacantes = [
                v for v in vacantes
                if any(
                    kw in f"{(v.get('titulo') or '').lower()} {(v.get('descripcion') or '').lower()} {(v.get('requisitos') or '').lower()}"
                    for kw in keywords
                )
            ]

        return jsonify({
            'ok': True,
            'vacantes': vacantes,
            'total': len(vacantes),
            'carreras': list(CARRERAS_KEYWORDS.keys()),
        })

    except Exception as e:
        return jsonify({'error': f'Error al cargar vacantes: {str(e)}'}), 500


@api_bp.route('/vacantes/<vacante_id>', methods=['GET'])
def api_vacante_detalle(vacante_id):
    """Detalle de una vacante específica."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        sb = get_supabase()

        respuesta = (
            sb.table('vacantes')
            .select('*')
            .eq('id', str(vacante_id))
            .single()
            .execute()
        )

        if not respuesta.data:
            return jsonify({'error': 'Vacante no encontrada.'}), 404

        # Verificar si el usuario ya se postuló
        ya_postulado = False
        post = (
            sb.table('postulaciones')
            .select('id')
            .eq('usuario_id', session['usuario_id'])
            .eq('vacante_id', str(vacante_id))
            .execute()
        )
        ya_postulado = len(post.data) > 0

        return jsonify({
            'ok': True,
            'vacante': respuesta.data,
            'ya_postulado': ya_postulado,
        })

    except Exception as e:
        return jsonify({'error': f'Error al cargar la vacante: {str(e)}'}), 500


@api_bp.route('/vacantes/<vacante_id>/postular', methods=['POST'])
def api_postular(vacante_id):
    """Registra la postulación de un estudiante a una vacante."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        sb = get_supabase()

        nueva_postulacion = {
            'usuario_id': session['usuario_id'],
            'vacante_id': str(vacante_id),
            'estado':     'postulado'
        }

        sb.table('postulaciones').insert(nueva_postulacion).execute()

        return jsonify({
            'ok': True,
            'mensaje': 'Te postulaste exitosamente. El coordinador revisará tu solicitud.',
        })

    except Exception as e:
        if 'unique' in str(e).lower():
            return jsonify({'error': 'Ya te habías postulado a esta vacante anteriormente.'}), 409
        return jsonify({'error': f'Error al postularse: {str(e)}'}), 500


@api_bp.route('/mis-postulaciones', methods=['GET'])
def api_mis_postulaciones():
    """Muestra las postulaciones del estudiante logueado."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

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
            'ok': True,
            'postulaciones': respuesta.data or [],
        })

    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


# ════════════════════════════════════════════════════════════════
# COORDINADOR
# ════════════════════════════════════════════════════════════════

def _check_coordinador():
    """Helper que verifica si el usuario es coordinador. Retorna None si OK, o un Response de error."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    if session.get('rol') != 'coordinador':
        return jsonify({'error': 'No tienes permisos para acceder a esta sección.'}), 403
    return None


@api_bp.route('/coordinador/dashboard', methods=['GET'])
def api_coordinador_dashboard():
    """Estadísticas generales del coordinador."""
    check = _check_coordinador()
    if check:
        return check

    try:
        sb = get_supabase()

        # Total vacantes activas
        vacantes_activas = sb.table('vacantes').select('id', count='exact').eq('activa', True).execute()
        total_vacantes = vacantes_activas.count or 0

        # Total estudiantes
        estudiantes_resp = sb.table('usuarios').select('id', count='exact').eq('rol', 'estudiante').execute()
        total_estudiantes = estudiantes_resp.count or 0

        # Total postulaciones
        postulaciones_resp = sb.table('postulaciones').select('id', count='exact').execute()
        total_postulaciones = postulaciones_resp.count or 0

        # Vacantes por fuente
        todas_vacantes_resp = sb.table('vacantes').select('fuente').eq('activa', True).execute()
        fuentes = {}
        for v in (todas_vacantes_resp.data or []):
            f = v.get('fuente', 'desconocida') or 'desconocida'
            fuentes[f] = fuentes.get(f, 0) + 1

        # Vacantes recientes
        recientes_resp = (
            sb.table('vacantes')
            .select('id, titulo, empresa, fuente, modalidad, activa, creado_en')
            .order('creado_en', desc=True)
            .limit(5)
            .execute()
        )

        # Postulaciones recientes
        postulaciones_recientes_resp = (
            sb.table('postulaciones')
            .select('id, estado, creado_en, vacantes(titulo, empresa), usuarios(nombre, apellido)')
            .order('creado_en', desc=True)
            .limit(5)
            .execute()
        )

        return jsonify({
            'ok': True,
            'stats': {
                'total_vacantes': total_vacantes,
                'total_estudiantes': total_estudiantes,
                'total_postulaciones': total_postulaciones,
                'fuentes': fuentes,
            },
            'vacantes_recientes': recientes_resp.data or [],
            'postulaciones_recientes': postulaciones_recientes_resp.data or [],
        })

    except Exception as e:
        return jsonify({'error': f'Error al cargar el dashboard: {str(e)}'}), 500


@api_bp.route('/coordinador/chart-data', methods=['GET'])
def api_coordinador_chart_data():
    """Devuelve los datos de series de tiempo para el gráfico del dashboard."""
    check = _check_coordinador()
    if check:
        return check

    try:
        sb = get_supabase()

        # Extraer fechas de estudiantes (rol=estudiante)
        estudiantes_resp = sb.table('usuarios').select('creado_en').eq('rol', 'estudiante').execute()
        estudiantes_data = estudiantes_resp.data or []

        # Extraer fechas de vacantes activas
        vacantes_resp = sb.table('vacantes').select('creado_en').eq('activa', True).execute()
        vacantes_data = vacantes_resp.data or []

        from collections import defaultdict
        from datetime import datetime, timedelta

        datos_por_fecha = defaultdict(lambda: {'estudiantes': 0, 'vacantes': 0})

        for e in estudiantes_data:
            if e.get('creado_en'):
                fecha = e['creado_en'][:10]
                datos_por_fecha[fecha]['estudiantes'] += 1

        for v in vacantes_data:
            if v.get('creado_en'):
                fecha = v['creado_en'][:10]
                datos_por_fecha[fecha]['vacantes'] += 1

        hoy = datetime.utcnow().date()
        chart_data = []

        # Aseguramos de enviar los últimos 90 días
        for i in range(89, -1, -1):
            fecha_actual = hoy - timedelta(days=i)
            fecha_str = fecha_actual.isoformat()

            chart_data.append({
                'date': fecha_str,
                'estudiantes': datos_por_fecha.get(fecha_str, {}).get('estudiantes', 0),
                'vacantes': datos_por_fecha.get(fecha_str, {}).get('vacantes', 0)
            })

        return jsonify({
            'ok': True,
            'data': chart_data
        })

    except Exception as e:
        return jsonify({'error': f'Error al obtener chart data: {str(e)}'}), 500



@api_bp.route('/coordinador/postulaciones', methods=['GET'])
def api_coordinador_postulaciones():
    """Lista todas las postulaciones para revisión del coordinador."""
    check = _check_coordinador()
    if check:
        return check

    try:
        sb = get_supabase()
        resp = (
            sb.table('postulaciones')
            .select('id, estado, creado_en, vacantes(titulo, empresa), usuarios(nombre, apellido, email)')
            .order('creado_en', desc=True)
            .execute()
        )
        return jsonify({
            'ok': True,
            'postulaciones': resp.data or [],
        })

    except Exception as e:
        return jsonify({'error': f'Error al cargar postulaciones: {str(e)}'}), 500


@api_bp.route('/coordinador/vacantes', methods=['GET'])
def api_coordinador_vacantes():
    """Lista todas las vacantes para gestión del coordinador."""
    check = _check_coordinador()
    if check:
        return check

    try:
        sb = get_supabase()
        mostrar = request.args.get('mostrar', 'activas')

        query = sb.table('vacantes').select('*').order('creado_en', desc=True)

        if mostrar == 'activas':
            query = query.eq('activa', True)
        elif mostrar == 'inactivas':
            query = query.eq('activa', False)

        respuesta = query.execute()

        return jsonify({
            'ok': True,
            'vacantes': respuesta.data or [],
            'mostrar': mostrar,
        })

    except Exception as e:
        return jsonify({'error': f'Error al cargar vacantes: {str(e)}'}), 500


@api_bp.route('/coordinador/vacantes', methods=['POST'])
def api_coordinador_crear_vacante():
    """Crea una nueva vacante manualmente."""
    check = _check_coordinador()
    if check:
        return check

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    try:
        sb = get_supabase()

        vacante_data = {
            'titulo':           (data.get('titulo') or '').strip(),
            'empresa':          (data.get('empresa') or '').strip(),
            'ubicacion':        (data.get('ubicacion') or '').strip(),
            'modalidad':        data.get('modalidad', 'presencial'),
            'fuente':           'manual',
            'descripcion':      (data.get('descripcion') or '').strip(),
            'requisitos':       (data.get('requisitos') or '').strip(),
            'link_aplicacion':  (data.get('url_oferta') or data.get('link_aplicacion') or '').strip(),
            'activa':           True,
        }

        if not vacante_data['titulo'] or not vacante_data['empresa']:
            return jsonify({'error': 'El título y la empresa son obligatorios.'}), 400

        resultado = sb.table('vacantes').insert(vacante_data).execute()

        return jsonify({
            'ok': True,
            'mensaje': 'Vacante creada exitosamente.',
            'vacante': resultado.data[0] if resultado.data else None,
        }), 201

    except Exception as e:
        return jsonify({'error': f'Error al crear vacante: {str(e)}'}), 500


@api_bp.route('/coordinador/vacantes/<vacante_id>/toggle', methods=['POST'])
def api_coordinador_toggle_vacante(vacante_id):
    """Activa o desactiva una vacante."""
    check = _check_coordinador()
    if check:
        return check

    try:
        sb = get_supabase()

        resp = sb.table('vacantes').select('activa').eq('id', str(vacante_id)).single().execute()
        if not resp.data:
            return jsonify({'error': 'Vacante no encontrada.'}), 404

        nuevo_estado = not resp.data['activa']
        sb.table('vacantes').update({'activa': nuevo_estado}).eq('id', str(vacante_id)).execute()

        estado_texto = 'activada' if nuevo_estado else 'desactivada'
        return jsonify({
            'ok': True,
            'mensaje': f'Vacante {estado_texto} correctamente.',
            'activa': nuevo_estado,
        })

    except Exception as e:
        return jsonify({'error': f'Error al cambiar estado: {str(e)}'}), 500


@api_bp.route('/coordinador/ejecutar-scraper', methods=['POST'])
def api_coordinador_ejecutar_scraper():
    """
    Ejecuta el scraper de Computrabajo con REGLA DE ORO: Experiencia Cero.
    Busca únicamente vacantes para pasantías, practicantes y trainee.
    """
    check = _check_coordinador()
    if check:
        return check

    try:
        from app.scrapers.computrabajo import ComputrabajoScraper, TERMINOS_BUSQUEDA

        # Usar el cliente service role para bypasear RLS de Supabase
        sb = get_supabase_service()
        scraper = ComputrabajoScraper(
            supabase_client=sb,
            delay_min=3,
            delay_max=6
        )

        # Los términos viven en el módulo del scraper — un único punto de verdad
        resumen = scraper.ejecutar(
            terminos_busqueda=TERMINOS_BUSQUEDA,
            max_paginas=2
        )

        return jsonify({
            'ok': True,
            'mensaje': (
                f"Scraper completado: {resumen['vacantes_guardadas']} vacantes nuevas "
                f"guardadas | {resumen['vacantes_rechazadas']} rechazadas por filtro."
            ),
            'resumen': resumen,
        })

    except Exception as e:
        return jsonify({'error': f'Error en el scraper: {str(e)}'}), 500


# ── HELPER PRIVADO ────────────────────────────────────────────

def _ejecutar_scraper_generico(scraper_cls, terminos, max_paginas=2):
    """
    Instancia un scraper, lo ejecuta y retorna el resumen.
    Usa el cliente service_role (bypass RLS) igual que el scraper de Computrabajo.
    """
    try:
        sb = get_supabase_service()
        scraper = scraper_cls(supabase_client=sb)
        resumen = scraper.ejecutar(
            terminos_busqueda=terminos,
            max_paginas=max_paginas,
        )
        return {**resumen, 'ok': True}
    except Exception as e:
        return {
            'ok': False,
            'fuente': scraper_cls.__name__,
            'error': str(e),
        }


# ┌─────────────────────────────────────────────────────────────┐
# │  POST /api/coordinador/ejecutar-scraper-indeed              │
# └─────────────────────────────────────────────────────────────┘
@api_bp.route('/coordinador/ejecutar-scraper-indeed', methods=['POST'])
def ejecutar_scraper_indeed():
    """Lanza el scraper de Indeed Colombia."""
    check = _check_coordinador()
    if check:
        return check

    from app.scrapers.computrabajo import TERMINOS_BUSQUEDA

    resultado = _ejecutar_scraper_generico(IndeedScraper, TERMINOS_BUSQUEDA)
    status = 200 if resultado.get('ok') else 500
    return jsonify(resultado), status


# ┌─────────────────────────────────────────────────────────────┐
# │  POST /api/coordinador/ejecutar-scraper-elempleo            │
# └─────────────────────────────────────────────────────────────┘
@api_bp.route('/coordinador/ejecutar-scraper-elempleo', methods=['POST'])
def ejecutar_scraper_elempleo():
    """Lanza el scraper de elempleo.com."""
    check = _check_coordinador()
    if check:
        return check

    from app.scrapers.computrabajo import TERMINOS_BUSQUEDA

    resultado = _ejecutar_scraper_generico(ElempleoScraper, TERMINOS_BUSQUEDA)
    status = 200 if resultado.get('ok') else 500
    return jsonify(resultado), status


# ┌─────────────────────────────────────────────────────────────┐
# │  POST /api/coordinador/ejecutar-todos-scrapers              │
# │  Corre Computrabajo + Indeed + Elempleo en paralelo.        │
# └─────────────────────────────────────────────────────────────┘
@api_bp.route('/coordinador/ejecutar-todos-scrapers', methods=['POST'])
def ejecutar_todos_scrapers():
    """Lanza los 3 scrapers en paralelo y devuelve resumen consolidado."""
    check = _check_coordinador()
    if check:
        return check

    from app.scrapers.computrabajo import ComputrabajoScraper, TERMINOS_BUSQUEDA

    scrapers = [ComputrabajoScraper, IndeedScraper, ElempleoScraper]

    resultados = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futuros = {
            pool.submit(_ejecutar_scraper_generico, cls, TERMINOS_BUSQUEDA): cls
            for cls in scrapers
        }
        for fut in as_completed(futuros):
            resultados.append(fut.result())

    total_guardadas = sum(
        r.get('vacantes_guardadas', 0) for r in resultados if r.get('ok')
    )
    todos_ok = all(r.get('ok') for r in resultados)

    return jsonify({
        'ok': todos_ok,
        'total_vacantes_guardadas': total_guardadas,
        'resultados_por_fuente': resultados,
    }), 200 if todos_ok else 207  # 207 Multi-Status si alguno falló


# ════════════════════════════════════════════════════════════════
# DIAGNÓSTICO
# ════════════════════════════════════════════════════════════════

@api_bp.route('/test-conexion', methods=['GET'])
def api_test_conexion():
    """Endpoint público para verificar conectividad."""
    try:
        sb = get_supabase()
        respuesta = sb.table('vacantes').select('id, titulo, empresa').limit(1).execute()
        return jsonify({
            'status': 'ok',
            'mensaje': '✅ Conexión con Supabase funcionando correctamente',
            'muestra': respuesta.data,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500
