# app/routes/coordinador.py
# ============================================================
# RUTAS DEL PANEL DE COORDINADOR — SIPE
# ============================================================

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.extensions import get_supabase
from app.auth_utils import coordinador_required

coordinador_bp = Blueprint('coordinador', __name__)


# ── DASHBOARD PRINCIPAL ───────────────────────────────────────
@coordinador_bp.route('/dashboard')
@coordinador_required
def dashboard():
    """Panel principal del coordinador con estadísticas generales."""
    try:
        sb = get_supabase()

        # Total vacantes activas
        vacantes_activas = sb.table('vacantes').select('id', count='exact').eq('activa', True).execute()
        total_vacantes = vacantes_activas.count or 0

        # Total estudiantes registrados
        estudiantes_resp = sb.table('usuarios').select('id', count='exact').eq('rol', 'estudiante').execute()
        total_estudiantes = estudiantes_resp.count or 0

        # Total postulaciones
        postulaciones_resp = sb.table('postulaciones').select('id', count='exact').execute()
        total_postulaciones = postulaciones_resp.count or 0

        # Vacantes por fuente (para la barra de progreso)
        todas_vacantes_resp = sb.table('vacantes').select('fuente').eq('activa', True).execute()
        fuentes = {}
        for v in (todas_vacantes_resp.data or []):
            f = v.get('fuente', 'desconocida') or 'desconocida'
            fuentes[f] = fuentes.get(f, 0) + 1

        # Objeto stats que espera el template
        stats = {
            'total_vacantes': total_vacantes,
            'total_estudiantes': total_estudiantes,
            'total_postulaciones': total_postulaciones,
            'fuentes': fuentes,
        }

        # Vacantes recientes (últimas 5)
        recientes_resp = (
            sb.table('vacantes')
            .select('id, titulo, empresa, fuente, modalidad, activa, creado_en')
            .order('creado_en', desc=True)
            .limit(5)
            .execute()
        )
        vacantes_recientes = recientes_resp.data or []

        # Postulaciones recientes (últimas 5)
        postulaciones_recientes_resp = (
            sb.table('postulaciones')
            .select('id, estado, creado_en, vacantes(titulo, empresa), usuarios(nombre, apellido)')
            .order('creado_en', desc=True)
            .limit(5)
            .execute()
        )
        postulaciones_recientes = postulaciones_recientes_resp.data or []

        return render_template(
            'coordinador/dashboard.html',
            stats=stats,
            vacantes_recientes=vacantes_recientes,
            postulaciones_recientes=postulaciones_recientes,
        )

    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'danger')
        return render_template(
            'coordinador/dashboard.html',
            stats={'total_vacantes': 0, 'total_estudiantes': 0, 'total_postulaciones': 0, 'fuentes': {}},
            vacantes_recientes=[],
            postulaciones_recientes=[],
        )


# ── VER POSTULACIONES ─────────────────────────────────────────
@coordinador_bp.route('/postulaciones')
@coordinador_required
def postulaciones():
    """Lista todas las postulaciones para revisión del coordinador."""
    try:
        sb = get_supabase()
        resp = (
            sb.table('postulaciones')
            .select('id, estado, creado_en, vacantes(titulo, empresa), usuarios(nombre, apellido, email)')
            .order('creado_en', desc=True)
            .execute()
        )
        return render_template(
            'coordinador/postulaciones.html',
            postulaciones=resp.data or []
        )
    except Exception as e:
        flash(f'Error al cargar postulaciones: {str(e)}', 'danger')
        return render_template('coordinador/postulaciones.html', postulaciones=[])


# ── EJECUTAR SCRAPER ──────────────────────────────────────────
@coordinador_bp.route('/ejecutar-scraper', methods=['GET', 'POST'])
@coordinador_required
def ejecutar_scraper():
    """Ejecuta el scraper de vacantes."""
    if request.method == 'POST':
        try:
            from app.scrapers.computrabajo import ComputrabajoScraper

            sb = get_supabase()
            scraper = ComputrabajoScraper(
                supabase_client=sb,
                delay_min=3,
                delay_max=5
            )
            resumen = scraper.ejecutar(
                terminos_busqueda=['ingeniero sistemas', 'desarrollador python', 'soporte tecnico'],
                max_paginas=2
            )
            flash(
                f"✅ Scraper completado: {resumen['vacantes_guardadas']} vacantes nuevas guardadas.",
                'success'
            )
        except Exception as e:
            flash(f'❌ Error en el scraper: {str(e)}', 'danger')

        return redirect(url_for('coordinador.dashboard'))

    return render_template('coordinador/scraper.html')


# ── GESTIÓN DE VACANTES ───────────────────────────────────────
@coordinador_bp.route('/vacantes')
@coordinador_required
def gestionar_vacantes():
    """Lista todas las vacantes para el coordinador."""
    try:
        sb = get_supabase()
        mostrar = request.args.get('mostrar', 'activas')

        query = sb.table('vacantes').select('*').order('creado_en', desc=True)

        if mostrar == 'activas':
            query = query.eq('activa', True)
        elif mostrar == 'inactivas':
            query = query.eq('activa', False)

        respuesta = query.execute()
        vacantes = respuesta.data or []

        return render_template(
            'coordinador/vacantes.html',
            vacantes=vacantes,
            mostrar=mostrar
        )

    except Exception as e:
        flash(f'Error al cargar vacantes: {str(e)}', 'danger')
        return render_template('coordinador/vacantes.html', vacantes=[], mostrar='activas')


# ── TOGGLE ACTIVA/INACTIVA ────────────────────────────────────
@coordinador_bp.route('/vacantes/<uuid:vacante_id>/toggle', methods=['POST'])
@coordinador_required
def toggle_vacante(vacante_id):
    """Activa o desactiva una vacante."""
    try:
        sb = get_supabase()

        resp = sb.table('vacantes').select('activa').eq('id', str(vacante_id)).single().execute()
        if not resp.data:
            flash('Vacante no encontrada.', 'warning')
            return redirect(url_for('coordinador.gestionar_vacantes'))

        nuevo_estado = not resp.data['activa']
        sb.table('vacantes').update({'activa': nuevo_estado}).eq('id', str(vacante_id)).execute()

        estado_texto = 'activada' if nuevo_estado else 'desactivada'
        flash(f'Vacante {estado_texto} correctamente.', 'success')

    except Exception as e:
        flash(f'Error al cambiar estado: {str(e)}', 'danger')

    return redirect(url_for('coordinador.gestionar_vacantes'))


# ── NUEVA VACANTE (formulario) ────────────────────────────────
@coordinador_bp.route('/vacantes/nueva', methods=['GET', 'POST'])
@coordinador_required
def nueva_vacante():
    """Crea una nueva vacante manualmente."""
    if request.method == 'POST':
        try:
            sb = get_supabase()

            data = {
                'titulo':      request.form.get('titulo', '').strip(),
                'empresa':     request.form.get('empresa', '').strip(),
                'ubicacion':   request.form.get('ubicacion', '').strip(),
                'modalidad':   request.form.get('modalidad', 'presencial'),
                'fuente':      'manual',
                'descripcion': request.form.get('descripcion', '').strip(),
                'requisitos':  request.form.get('requisitos', '').strip(),
                'url_oferta':  request.form.get('url_oferta', '').strip(),
                'activa':      True,
            }

            if not data['titulo'] or not data['empresa']:
                flash('El título y la empresa son obligatorios.', 'warning')
                return render_template('coordinador/nueva_vacante.html', data=data)

            sb.table('vacantes').insert(data).execute()
            flash('✅ Vacante creada exitosamente.', 'success')
            return redirect(url_for('coordinador.gestionar_vacantes'))

        except Exception as e:
            flash(f'Error al crear vacante: {str(e)}', 'danger')

    return render_template('coordinador/nueva_vacante.html', data={})
