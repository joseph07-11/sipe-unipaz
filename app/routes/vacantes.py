# app/routes/vacantes.py
# ============================================================
# RUTAS DE VACANTES — Cartelera principal de SIPE
# ============================================================

from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, session
from app.extensions import get_supabase
from app.auth_utils import login_required
from app.config import CARRERAS_KEYWORDS

vacantes_bp = Blueprint('vacantes', __name__)
# app/routes/vacantes.py
# ============================================================
# Agrega esto AL INICIO del archivo, después de los imports
# ============================================================

# ── Carreras de Unipaz con sus palabras clave ─────────────────
# Cada carrera tiene keywords que identifican vacantes relevantes
# El scraper trae de todo; esto filtra lo pertinente por programa
CARRERAS_KEYWORDS = {

    'Administración de Negocios Internacionales': [
        'administración', 'administrativo', 'gerencia', 'gestión',
        'ventas', 'comercial', 'marketing', 'recursos humanos',
        'contratación', 'presupuesto', 'planificación', 'director',
        'coordinador', 'supervisor', 'asesor comercial', 'comercio exterior',
        'importaciones', 'exportaciones', 'aduanas', 'logística'
    ],
    'Ingeniería Informática': [
        'sistemas', 'software', 'programador', 'desarrollador',
        'python', 'java', 'javascript', 'web', 'base de datos',
        'sql', 'redes', 'soporte', 'tecnología', 'it ', 'ti ',
        'ciberseguridad', 'cloud', 'devops', 'frontend', 'backend',
        'fullstack', 'análisis de datos', 'machine learning'
    ],
    'Ingeniería Ambiental y de Saneamiento': [
        'ambiental', 'saneamiento', 'hseq', 'residuos', 'impacto ambiental',
        'tratamiento de aguas', 'ecología', 'biodiversidad', 'suelos',
        'recursos naturales', 'consultoría ambiental', 'gestión ambiental'
    ],
    'Ingeniería Agroindustrial': [
        'agroindustrial', 'alimentos', 'procesos', 'poscosecha',
        'control de calidad', 'transformación', 'empaques', 'conservación',
        'plantas de producción', 'lácteos', 'cárnicos', 'agroindustria'
    ],
    'Ingeniería Agropecuaria': [
        'agropecuario', 'finca', 'cultivos', 'siembra', 'cosecha',
        'asistente técnico', 'agronomía', 'campo', 'producción animal',
        'insumos agrícolas', 'riego', 'sector agro'
    ],
    'Ingeniería Electromecánica': [
        'electromecánico', 'mantenimiento', 'mecánica', 'electricidad',
        'instrumentación', 'montajes', 'equipos industriales', 'motores',
        'soldadura', 'planos', 'automatización', 'electrotecnia'
    ],
    'Licenciatura en Artes': [
        'artes', 'cultural', 'diseño', 'música', 'danza', 'teatro',
        'pintura', 'docente', 'pedagogía', 'creatividad', 'curaduría',
        'gestor cultural', 'exposición', 'artística'
    ],
    'Medicina Veterinaria y Zootecnia': [
        'veterinaria', 'veterinario', 'zootecnista', 'clínica animal',
        'pequeños animales', 'grandes animales', 'cirugía veterinaria',
        'bienestar animal', 'sanidad', 'nutrición animal', 'salud animal'
    ],
    'Profesional en Turismo': [
        'turismo', 'hotelería', 'recepción', 'guía', 'viajes',
        'agencia', 'turístico', 'eventos', 'hospitalidad', 'cruceros',
        'servicios turísticos', 'guianza'
    ]
}




# ── CARTELERA PRINCIPAL ───────────────────────────────────────
@vacantes_bp.route('/')
@login_required
def index():
    try:
        sb = get_supabase()

        modalidad = request.args.get('modalidad', '')
        fuente    = request.args.get('fuente', '')
        carrera   = request.args.get('carrera', '')
        # Sanitizar búsqueda: strip() elimina espacios, or '' evita None
        busqueda  = (request.args.get('q') or '').strip()

        query = sb.table('vacantes').select('*').eq('activa', True)

        if modalidad:
            query = query.eq('modalidad', modalidad)
        if fuente:
            query = query.eq('fuente', fuente)

        query = query.order('creado_en', desc=True)
        respuesta = query.execute()
        vacantes  = respuesta.data

        # ── Filtro de búsqueda por texto ──────────────────────
        if busqueda:
            busqueda_lower = busqueda.lower()
            vacantes_filtradas = []

            for v in vacantes:
                # CORRECCIÓN CRÍTICA: usar 'or """ para evitar None
                # antes de aplicar .lower()
                titulo      = (v.get('titulo')      or '').lower()
                empresa     = (v.get('empresa')     or '').lower()
                ubicacion   = (v.get('ubicacion')   or '').lower()
                descripcion = (v.get('descripcion') or '').lower()
                requisitos  = (v.get('requisitos')  or '').lower()

                if (busqueda_lower in titulo      or
                    busqueda_lower in empresa     or
                    busqueda_lower in ubicacion   or
                    busqueda_lower in descripcion or
                    busqueda_lower in requisitos):
                    vacantes_filtradas.append(v)

            vacantes = vacantes_filtradas

        # ── Filtro por carrera Unipaz ─────────────────────────
        if carrera and carrera in CARRERAS_KEYWORDS:
            keywords = CARRERAS_KEYWORDS[carrera]
            vacantes_filtradas = []

            for v in vacantes:
                titulo      = (v.get('titulo')      or '').lower()
                descripcion = (v.get('descripcion') or '').lower()
                requisitos  = (v.get('requisitos')  or '').lower()
                texto       = f"{titulo} {descripcion} {requisitos}"

                if any(kw in texto for kw in keywords):
                    vacantes_filtradas.append(v)

            vacantes = vacantes_filtradas

        # Mensaje amigable si no hay resultados
        if not vacantes and busqueda:
            sin_resultados_msg = (
                f'No se encontraron vacantes para "{busqueda}". '
                f'Intenta con otros términos.'
            )
        else:
            sin_resultados_msg = None

        return render_template(
            'vacantes/index.html',
            vacantes=vacantes,
            total=len(vacantes),
            filtro_modalidad=modalidad,
            filtro_fuente=fuente,
            filtro_busqueda=busqueda,
            filtro_carrera=carrera,
            sin_resultados_msg=sin_resultados_msg,
            carreras=list(CARRERAS_KEYWORDS.keys())
        )

    except Exception as e:
        flash(f'Error al cargar vacantes: {str(e)}', 'danger')
        return render_template('vacantes/index.html',
                               vacantes=[], total=0,
                               carreras=list(CARRERAS_KEYWORDS.keys()))


# ── DETALLE DE UNA VACANTE ────────────────────────────────────
@vacantes_bp.route('/<uuid:vacante_id>')
@login_required
def detalle(vacante_id):
    """Muestra el detalle completo de una vacante."""
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
            flash('Vacante no encontrada.', 'warning')
            return redirect(url_for('vacantes.index'))

        # Verificar si el usuario ya se postuló
        ya_postulado = False
        if session.get('usuario_id'):
            post = (
                sb.table('postulaciones')
                .select('id')
                .eq('usuario_id', session['usuario_id'])
                .eq('vacante_id', str(vacante_id))
                .execute()
            )
            ya_postulado = len(post.data) > 0

        return render_template(
            'vacantes/detalle.html',
            vacante=respuesta.data,
            ya_postulado=ya_postulado
        )

    except Exception as e:
        flash(f'Error al cargar la vacante: {str(e)}', 'danger')
        return redirect(url_for('vacantes.index'))


# ── POSTULARSE A UNA VACANTE ──────────────────────────────────
@vacantes_bp.route('/<uuid:vacante_id>/postular', methods=['POST'])
@login_required
def postular(vacante_id):
    """Registra la postulación de un estudiante a una vacante."""
    try:
        sb = get_supabase()

        nueva_postulacion = {
            'usuario_id': session['usuario_id'],
            'vacante_id': str(vacante_id),
            'estado':     'postulado'
        }

        sb.table('postulaciones').insert(nueva_postulacion).execute()
        flash('¡Te postulaste exitosamente! El coordinador revisará tu solicitud.', 'success')

    except Exception as e:
        if 'unique' in str(e).lower():
            flash('Ya te habías postulado a esta vacante anteriormente.', 'warning')
        else:
            flash(f'Error al postularse: {str(e)}', 'danger')

    return redirect(url_for('vacantes.detalle', vacante_id=vacante_id))


# ── MIS POSTULACIONES ─────────────────────────────────────────
@vacantes_bp.route('/mis-postulaciones')
@login_required
def mis_postulaciones():
    """Muestra las postulaciones del estudiante logueado."""
    try:
        sb = get_supabase()

        respuesta = (
            sb.table('postulaciones')
            .select('*, vacantes(*)')
            .eq('usuario_id', session['usuario_id'])
            .order('creado_en', desc=True)
            .execute()
        )

        return render_template(
            'vacantes/mis_postulaciones.html',
            postulaciones=respuesta.data
        )

    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('vacantes/mis_postulaciones.html', postulaciones=[])


# ── RUTA DE DIAGNÓSTICO (mantener del paso anterior) ──────────
@vacantes_bp.route('/test-conexion')
def test_conexion():
    try:
        sb = get_supabase()
        respuesta = sb.table('vacantes').select('id, titulo, empresa').limit(1).execute()
        return jsonify({
            'status': 'ok',
            'mensaje': '✅ Conexión con Supabase funcionando perfectamente',
            'muestra': respuesta.data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500

        # Agregar al final de vacantes.py

from app.auth_utils import coordinador_required

@vacantes_bp.route('/ejecutar-scraper', methods=['POST'])
@coordinador_required
def ejecutar_scraper():
    """
    Ruta para ejecutar el scraper desde el panel del coordinador.
    Solo accesible para usuarios con rol 'coordinador'.
    """
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

    return redirect(url_for('vacantes.index'))